import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import sys
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from mcp_monkdb.mcp_server import run_select_query
from agents.agent_dynamic_insights import dynamic_insights_from_schema
from langchain_ollama import ChatOllama
from gen_insights_force import main as run_insights

load_dotenv()
SCHEMA_TABLE = "trent.products"

# ---------- Query helper ----------


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    res = run_select_query(sql)
    if isinstance(res, dict) and res.get("status") == "error":
        raise RuntimeError(res["message"])
    return pd.DataFrame(res or [])


# ---------- Auto visualization ----------
def auto_viz(name: str, df: pd.DataFrame):
    """Heuristic chart selector based on data structure."""
    if df.empty:
        st.info(f"No data for {name}")
        return

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    # Single KPI
    if len(df) == 1 and len(numeric_cols) == 1:
        st.metric(label=name.replace("_", " ").title(), value=df.iloc[0, 0])
        return

    # Categorical bar
    if len(numeric_cols) == 1 and len(non_numeric_cols) == 1:
        fig = px.bar(df, x=non_numeric_cols[0], y=numeric_cols[0],
                     title=name.replace("_", " ").title(),
                     color=non_numeric_cols[0])
        st.plotly_chart(fig, use_container_width=True)
        return

    # Multi-metric grouped bar
    if len(numeric_cols) > 1 and len(non_numeric_cols) == 1:
        fig = px.bar(df, x=non_numeric_cols[0], y=numeric_cols,
                     barmode="group",
                     title=name.replace("_", " ").title())
        st.plotly_chart(fig, use_container_width=True)
        return

    # Time-series line
    if any("date" in c.lower() or "time" in c.lower() for c in df.columns):
        x_col = next((c for c in df.columns if "date" in c.lower()
                     or "time" in c.lower()), df.columns[0])
        y_col = numeric_cols[0] if numeric_cols else df.columns[1]
        fig = px.line(df, x=x_col, y=y_col,
                      title=name.replace("_", " ").title())
        st.plotly_chart(fig, use_container_width=True)
        return

    # Fallback table
    st.dataframe(df, use_container_width=True, hide_index=True)


# ---------- Streamlit app ----------
st.set_page_config(page_title="Trent Agentic AI Demo", layout="wide")
st.image("logo.png", width=250)
st.title("Product Trends Agentic AI: Data → Reasoning → Visualization")

# ---------- Filters ----------
brands_df = q(f"SELECT DISTINCT brand FROM {SCHEMA_TABLE} ORDER BY 1")
brands = brands_df["brand"].dropna().tolist() if not brands_df.empty else []
c1, c2, c3 = st.columns([1, 2, 2])

min_disc, max_disc = c1.slider("Discount % Range", 0, 90, (0, 90))
min_rating, max_rating = c2.slider("Rating Range", 0.0, 5.0, (0.0, 5.0), 0.1)
selected_brands = c3.multiselect("Brands", brands, default=brands)

where_clauses = ["1=1"]
if selected_brands:
    brand_csv = ",".join(f"'{b}'" for b in selected_brands)
    where_clauses.append(f"brand IN ({brand_csv})")
where_clauses.append(
    f"discount_percent BETWEEN {int(min_disc)} AND {int(max_disc)}")
where_clauses.append(f"rating BETWEEN {min_rating} AND {max_rating}")
where_clause = " AND ".join(where_clauses)

# ---------- KPI cards ----------
kpis_df = q(f"""
    SELECT COUNT(*) AS products,
           ROUND(AVG(price),2) AS avg_price,
           ROUND(AVG(mrp),2) AS avg_mrp,
           ROUND(AVG(discount_percent),2) AS avg_discount_pct,
           SUM(CASE WHEN price = mrp THEN 1 ELSE 0 END) AS no_discount_items
    FROM {SCHEMA_TABLE}
    WHERE {where_clause}
""")
kpis = kpis_df.iloc[0] if not kpis_df.empty else pd.Series({
    "products": 0, "avg_price": 0, "avg_mrp": 0,
    "avg_discount_pct": 0, "no_discount_items": 0
})
cols = st.columns(5)
labels = ["Products", "Avg Price", "Avg MRP",
          "Avg Discount %", "No-discount Items"]
for i, label in enumerate(labels):
    with cols[i].container(border=True):
        st.metric(label, kpis[i])

# ---------- AI-driven insights ----------
st.divider()
st.subheader("🤖 Autonomous AI-Generated Insights (Mistral Reasoning)")

goal = st.text_input(
    "What’s your analysis goal?",
    value="Optimize discounts and understand brand performance"
)

TABLE_NAME = SCHEMA_TABLE
TABLE_DDL = """
CREATE TABLE trent.products (
    product_id        LONG PRIMARY KEY,
    style_id          INTEGER,
    title             TEXT,
    brand             TEXT,
    price             DOUBLE,
    mrp               DOUBLE,
    discount_percent  DOUBLE,
    rating            FLOAT,
    rating_total      INTEGER,
    img_primary       TEXT,
    img_count         INTEGER
)
CLUSTERED BY (product_id);
""".strip()

REFERENCE_SQLS = [
    "SELECT ROUND(AVG(price),2) AS avg_price FROM {table}",
    "SELECT ROUND(AVG(discount_percent),2) AS avg_discount_pct FROM {table}",
    "SELECT brand, COUNT(*) AS items FROM {table} GROUP BY brand ORDER BY items DESC LIMIT 10",
    "SELECT ROUND(AVG(rating),2) AS avg_rating FROM {table} WHERE rating_total > 0",
    "SELECT product_id, title, brand, price, mrp, discount_percent, rating, rating_total FROM {table} ORDER BY rating_total DESC LIMIT 50",
]

sample_df = q(f"SELECT * FROM {TABLE_NAME} LIMIT 10")
schema_info = {
    "columns": list(sample_df.columns),
    "preview_markdown": sample_df.head(5).to_markdown(index=False),
    "summary_markdown": "Streamlit live session - generating goal-aligned insights."
}

if st.button("Generate Live AI Insights"):
    with st.spinner("Reasoning over schema and goal..."):
        results = dynamic_insights_from_schema(
            table_name=TABLE_NAME,
            table_ddl=TABLE_DDL,
            schema_info=schema_info,
            reference_sqls=[q.format(table=TABLE_NAME)
                            for q in REFERENCE_SQLS],
            goal=goal,
        )

    if not results:
        st.warning("No AI insights returned.")
    else:
        st.success(f"Generated {len(results)} insights dynamically!")
        for name, df in results.items():
            st.markdown(f"### {name.replace('_', ' ').title()}")
            auto_viz(name, df)
