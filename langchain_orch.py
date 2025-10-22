import argparse
import os
from pathlib import Path
import logging
import pandas as pd

from utils import abspath, run_command
from langchain_ollama import ChatOllama
from langchain.agents import initialize_agent, AgentType

from agents.agent_upload import upload
from agents.agent_insights import generate_insights
from agents.agent_deploy import deploy_dashboard
from agents.agent_dynamic_insights import dynamic_insights_from_schema  # NEW

# -------------------------------------------------------------------
# Setup logging
# -------------------------------------------------------------------
logger = logging.getLogger("orch")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

# -------------------------------------------------------------------
# Constants: model, table, DDL, reference queries
# -------------------------------------------------------------------
model_name = os.getenv("OLLAMA_MODEL", "mistral")
TABLE_NAME = "trent.products"

# Exact DDL you provided
TABLE_DDL = """
CREATE TABLE trent.products (
    product_id        LONG PRIMARY KEY,          -- unique product identifier
    style_id          INTEGER,                   -- style ID
    title             TEXT,                      -- product title
    brand             TEXT,                      -- brand name
    price             DOUBLE,                    -- selling price
    mrp               DOUBLE,                    -- maximum retail price
    discount_percent  DOUBLE,                    -- discount percentage
    rating            FLOAT,                     -- average rating (0.0 - 5.0)
    rating_total      INTEGER,                   -- number of ratings
    img_primary       TEXT,                      -- primary image URL
    img_count         INTEGER                    -- number of images
)
CLUSTERED BY (product_id);
""".strip()

# Reference query "moulds" (from your gen_insights_force.py)
REFERENCE_SQLS = [
    # core kpis
    "SELECT ROUND(AVG(price),2) AS avg_price, ROUND(AVG(mrp),2) AS avg_mrp, ROUND(AVG(discount_percent),2) AS avg_discount_pct, SUM(CASE WHEN price = mrp THEN 1 ELSE 0 END) AS no_discount_items FROM {table}",
    # discount bands
    "SELECT band, COUNT(*) AS items FROM (SELECT CASE WHEN discount_percent = 0 THEN '0%' WHEN discount_percent < 20 THEN '0-20%' WHEN discount_percent < 40 THEN '20-40%' WHEN discount_percent < 60 THEN '40-60%' ELSE '60%+' END AS band FROM {table}) b GROUP BY band ORDER BY items DESC",
    # brand concentration
    "SELECT t.brand, t.c AS items, ROUND(100.0 * t.c / total.s, 2) AS share_pct FROM (SELECT brand, COUNT(*) AS c FROM {table} GROUP BY brand) t CROSS JOIN (SELECT COUNT(*) AS s FROM {table}) total ORDER BY t.c DESC LIMIT 20",
    # ratings coverage
    "SELECT SUM(CASE WHEN rating_total > 0 THEN 1 ELSE 0 END) AS rated_items, SUM(CASE WHEN rating_total = 0 THEN 1 ELSE 0 END) AS unrated_items, ROUND(AVG(NULLIF(rating, 0)), 2) AS avg_rating_nonzero FROM {table}",
    # rating distribution
    "SELECT CASE WHEN rating = 0 THEN '0 (unrated)' WHEN rating < 2 THEN '1.0-1.9' WHEN rating < 3 THEN '2.0-2.9' WHEN rating < 4 THEN '3.0-3.9' WHEN rating < 4.5 THEN '4.0-4.49' ELSE '4.5-5.0' END AS rating_band, COUNT(*) AS items FROM {table} GROUP BY rating_band ORDER BY items DESC",
    # top rated by volume
    "SELECT product_id, title, brand, rating, rating_total, price, mrp, discount_percent FROM {table} WHERE rating_total >= 100 AND rating >= 4 ORDER BY rating DESC, rating_total DESC LIMIT 50",
    # highest discounts among rated
    "SELECT product_id, title, brand, price, mrp, discount_percent, rating, rating_total FROM {table} WHERE rating_total > 0 ORDER BY discount_percent DESC, price ASC LIMIT 50",
    # rating by discount band
    "SELECT band, ROUND(AVG(NULLIF(rating,0)), 2) AS avg_rating_nonzero, SUM(rating_total) AS total_ratings, COUNT(*) AS items FROM (SELECT CASE WHEN discount_percent = 0 THEN '0%' WHEN discount_percent < 20 THEN '0-20%' WHEN discount_percent < 40 THEN '20-40%' WHEN discount_percent < 60 THEN '40-60%' ELSE '60%+' END AS band, rating, rating_total FROM {table}) bands GROUP BY band ORDER BY band",
    # price buckets
    "SELECT CASE WHEN price < 500 THEN '<500' WHEN price < 1000 THEN '500-999' WHEN price < 2000 THEN '1000-1999' WHEN price < 5000 THEN '2000-4999' ELSE '5000+' END AS price_bucket, COUNT(*) AS items, ROUND(AVG(discount_percent),2) AS avg_discount_pct FROM {table} GROUP BY price_bucket ORDER BY items DESC",
    # image count vs rating
    "SELECT CASE WHEN img_count IS NULL OR img_count = 0 THEN '0' WHEN img_count <= 2 THEN '1-2' WHEN img_count <= 4 THEN '3-4' ELSE '5+' END AS img_bucket, COUNT(*) AS items, ROUND(AVG(NULLIF(rating,0)), 2) AS avg_rating_nonzero FROM {table} GROUP BY img_bucket ORDER BY items DESC",
    # total markdown value
    "SELECT ROUND(SUM(GREATEST(mrp - price, 0)), 2) AS total_markdown_value FROM {table}",
    # duplicate titles (catalog hygiene)
    "SELECT title, COUNT(*) AS dupes FROM {table} GROUP BY title HAVING COUNT(*) > 1 ORDER BY dupes DESC LIMIT 50",
    # data quality nulls
    "SELECT SUM(CASE WHEN brand IS NULL OR brand = '' THEN 1 ELSE 0 END) AS null_brands, SUM(CASE WHEN title IS NULL OR title = '' THEN 1 ELSE 0 END) AS null_titles, SUM(CASE WHEN price IS NULL OR price <= 0 THEN 1 ELSE 0 END) AS bad_price FROM {table}",
]

# -------------------------------------------------------------------
# Instantiate LLM
# -------------------------------------------------------------------
logger.info("Using Ollama model: %s", model_name)
llm = ChatOllama(model=model_name)

# -------------------------------------------------------------------
# Tools & Agents
# -------------------------------------------------------------------
uploader = initialize_agent(
    tools=[upload],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

insighter = initialize_agent(
    tools=[generate_insights],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

deployer = initialize_agent(
    tools=[deploy_dashboard],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

# -------------------------------------------------------------------
# Helper: Agent Invocation
# -------------------------------------------------------------------


def invoke_agent(agent, instruction: str, timeout: int = 120):
    logger.info("Invoking agent with instruction: %s", instruction)
    try:
        res = agent.run(instruction)
        logger.info("Agent completed successfully.")
        logger.debug("Agent raw output: %s", res)
        return {"success": True, "output": res}
    except Exception as e:
        logger.exception("Agent invocation failed: %s", e)
        return {"success": False, "error": str(e)}

# -------------------------------------------------------------------
# STEP 0: Schema & Content Awareness (returns dict used later)
# -------------------------------------------------------------------


def analyze_schema(csv_file_path, llm):
    """Read a sample of the CSV and let the LLM describe structure & KPIs."""
    try:
        df = pd.read_csv(csv_file_path, nrows=10)
        cols = df.columns.tolist()
        sample_preview = df.head(5).to_markdown(index=False)

        prompt = f"""
        You are a data analyst. Here is a preview of a dataset:

        Columns: {cols}

        Sample:
        {sample_preview}

        1) Briefly describe what this dataset appears to represent.
        2) Propose likely data types of each column (int/float/text).
        3) Suggest 3–5 potential KPIs we could compute given these columns.
        Please return a concise markdown summary.
        """

        response = llm.invoke(prompt)
        summary = (response.content or "").strip()
        logger.info(
            "\n=== DATA UNDERSTANDING (LLM) ===\n%s\n===============================\n", summary)
        return {
            "columns": cols,
            "preview_markdown": sample_preview,
            "summary_markdown": summary
        }
    except Exception as e:
        logger.warning(f"Schema analysis failed: {e}")
        return {
            "columns": [],
            "preview_markdown": "",
            "summary_markdown": f"(schema analysis failed: {e})"
        }

# -------------------------------------------------------------------
# Multi-Agent Workflow
# -------------------------------------------------------------------


def multi_agent_workflow(csv_file_path: str):
    csv_file_path = str(Path(csv_file_path).resolve())
    logger.info("🚀 Starting multi-agent pipeline for %s", csv_file_path)

    # STEP 0: Schema Awareness (we WILL use this below)
    schema_info = analyze_schema(csv_file_path, llm)

    # STEP 1: Upload to MonkDB
    res1 = invoke_agent(uploader, {csv_file_path})
    if not res1["success"]:
        return res1
    logger.info("Uploader Output:\n%s", res1["output"])

    # STEP 2: Autonomous Insight Planning via LLM (uses schema_info, DDL, references)
    logger.info("🧠 Running Autonomous Insight Planning...")
    auto_results = dynamic_insights_from_schema(
        table_name=TABLE_NAME,
        table_ddl=TABLE_DDL,
        schema_info=schema_info,
        reference_sqls=[q.format(table=TABLE_NAME) for q in REFERENCE_SQLS],
    )
    if auto_results:
        logger.info("Generated dynamic insights for %d metrics",
                    len(auto_results))
    else:
        logger.warning("No dynamic insights generated.")

    # STEP 3: Deploy Dashboard
    res3 = invoke_agent(deployer, {csv_file_path})
    if not res3["success"]:
        return res3
    logger.info("Deployer Output:\n%s", res3["output"])

    logger.info("✅ Multi-agent workflow finished successfully.")
    return {"success": True, "deployer": res3["output"]}


# -------------------------------------------------------------------
# CLI Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="CSV file path")
    args = parser.parse_args()
    result = multi_agent_workflow(args.file_path)
    print("\n=== FINAL RESULT ===")
    print(result)
