import streamlit as st
import plotly.express as px
import pandas as pd
from dotenv import load_dotenv
from mcp_monkdb.mcp_server import run_select_query
from agents.agent_dynamic_insights import dynamic_insights_from_schema

load_dotenv()
SCHEMA_TABLE = "trent.products"

# ---------- Query helper ----------


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    res = run_select_query(sql)
    return pd.DataFrame(res or [])


# ---------- Auto visualization ----------
def auto_viz(name: str, df: pd.DataFrame):
    """Heuristic chart selector based on structure."""
    if df.empty:
        st.info(f"No data for {name}")
        return

    numeric = df.select_dtypes(include="number").columns.tolist()
    categoric = [c for c in df.columns if c not in numeric]

    if len(df) == 1 and len(numeric) == 1:
        st.metric(label=name.replace("_", " ").title(), value=df.iloc[0, 0])
    elif len(numeric) == 1 and len(categoric) == 1:
        st.plotly_chart(
            px.bar(df, x=categoric[0], y=numeric[0],
                   color=categoric[0],
                   title=name.replace("_", " ").title()),
            use_container_width=True,
        )
    elif len(numeric) > 1 and len(categoric) == 1:
        st.plotly_chart(
            px.bar(df, x=categoric[0], y=numeric, barmode="group",
                   title=name.replace("_", " ").title()),
            use_container_width=True,
        )
    elif any("date" in c.lower() or "time" in c.lower() for c in df.columns):
        x_col = next((c for c in df.columns if "date" in c.lower()
                     or "time" in c.lower()), df.columns[0])
        y_col = numeric[0] if numeric else df.columns[1]
        st.plotly_chart(
            px.line(df, x=x_col, y=y_col,
                    title=name.replace("_", " ").title()),
            use_container_width=True,
        )
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# ---------- Streamlit App ----------
st.set_page_config(page_title="Trent Agentic AI Demo", layout="wide")
st.image("logo.png", width=250)
st.title("🧠 Product Trends Agentic AI: Data → Reasoning → Reflection")

goal = st.text_input(
    "🎯 What’s your analysis goal?",
    value="Optimize discounts and understand brand performance",
)

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
]

sample_df = q(f"SELECT * FROM {SCHEMA_TABLE} LIMIT 10")
schema_info = {
    "columns": list(sample_df.columns),
    "preview_markdown": sample_df.head(5).to_markdown(index=False),
    "summary_markdown": "Streamlit live session - generating goal-aligned insights."
}

if st.button("🚀 Generate AI Insights"):
    with st.spinner("Reasoning, querying, and reflecting..."):
        results, summary = dynamic_insights_from_schema(
            table_name=SCHEMA_TABLE,
            table_ddl=TABLE_DDL,
            schema_info=schema_info,
            reference_sqls=[r.format(table=SCHEMA_TABLE)
                            for r in REFERENCE_SQLS],
            goal=goal,
        )

    if not results:
        st.warning("No AI insights generated.")
    else:
        st.success(f"✅ Generated {len(results)} insights for goal: *{goal}*")
        for name, df in results.items():
            st.markdown(f"### {name.replace('_', ' ').title()}")
            auto_viz(name, df)

        st.divider()
        st.subheader("🧩 Reflective Summary (LLM Reasoning)")
        st.markdown(summary)
