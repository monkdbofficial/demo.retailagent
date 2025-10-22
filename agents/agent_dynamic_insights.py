import json
import re
import pandas as pd
from typing import Dict, List
from langchain_ollama import ChatOllama
from mcp_monkdb.mcp_server import run_select_query

# Initialize LLM
llm = ChatOllama(model="mistral")

# --- simple SQL safety checks (PoC-grade) ---


def _is_safe_select(sql: str, table_name: str) -> bool:
    s = sql.strip().rstrip(";").lower()
    if not s.startswith("select"):
        return False
    if any(bad in s for bad in ["insert ", "update ", "delete ", "drop ", "alter ", "truncate ", "create "]):
        return False
    if table_name.lower() not in s:
        return False
    return True


def dynamic_insights_from_schema(
    table_name: str,
    table_ddl: str,
    schema_info: Dict,
    reference_sqls: List[str],
    goal: str = "Generate general insights",
):
    """
    Let the LLM read (1) CSV sample summary, (2) concrete DDL, and (3) reference query moulds,
    then propose 3–5 SELECT statements to compute KPIs. Executes them via MCP.
    """
    columns = schema_info.get("columns", [])
    preview_md = schema_info.get("preview_markdown", "")
    summary_md = schema_info.get("summary_markdown", "")

    ref_block = "\n".join([f"- {s}" for s in reference_sqls])

    prompt = f"""
You are an experienced SQL data analyst working with a CrateDB/MonkDB table.

USER GOAL: {goal}

Table name: {table_name}

Table DDL (authoritative):
{table_ddl}

CSV sample (first few rows):
{preview_md}

LLM's earlier understanding:
{summary_md}

Column list (from CSV):
{columns}

REFERENCE EXAMPLES (style/mould to follow; use same table and column names):
{ref_block}

Now produce 3–5 useful SELECT queries for KPIs/insights on {table_name}
that best align with the goal: "{goal}".

RULES (strict):
- Use only this table: {table_name}
- SELECT-only. No INSERT/UPDATE/DELETE/DDL.
- Prefer simple aggregates, rankings, or trend summaries.
- Use existing columns only.
- Include LIMIT where appropriate.
- Output JSON ONLY in this format:

[
  {{ "name": "kpi_slug", "sql": "SELECT ... FROM {table_name} ..." }},
  ...
]
    """

    # --- Step 1: Query the LLM ---
    response = llm.invoke(prompt)
    text = (response.content or "").strip()

    print("\n=== AUTO-GENERATED INSIGHT PLAN (RAW) ===\n",
          text, "\n=========================================\n")

    # --- Step 2: Parse JSON safely ---
    plan = []
    try:
        plan = json.loads(text)
        if not isinstance(plan, list):
            raise ValueError("Expected a JSON list at top level")
    except Exception as e:
        print(f"⚠️ LLM response not valid JSON: {e}")
        match = re.search(r"\[.*\]", text, re.S)
        if match:
            try:
                plan = json.loads(match.group(0))
            except Exception:
                plan = []
        if not plan:
            print("⚠️ Could not recover any valid plan JSON.")
            return {}

    # --- Step 3: Validate & execute ---
    results = {}
    for item in plan:
        name = item.get("name", "unnamed")
        sql = item.get("sql", "")
        if not sql:
            continue

        # fix potential GROUP BY issue seen in CrateDB
        if "GROUP BY" in sql and "title" in sql and "SUM(" in sql and "product_id" in sql:
            sql = re.sub(r"GROUP BY\s+\w+",
                         "GROUP BY product_id, title, brand, price", sql)

        if not _is_safe_select(sql, table_name):
            print(f"⛔ Skipping unsafe or invalid SQL for {name}: {sql}")
            continue

        print(f"→ Running {name}: {sql}")
        try:
            df_res = pd.DataFrame(run_select_query(sql))
            results[name] = df_res
            try:
                print(df_res.head(5).to_string(index=False))
            except Exception:
                print(f"(rows: {len(df_res)})")
        except Exception as e:
            print(f"❌ Failed to execute {name}: {e}")

    print(f"✅ Generated dynamic insights for {len(results)} metrics.")
    return results
