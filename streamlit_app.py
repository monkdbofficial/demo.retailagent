# streamlit_app.py
from gen_insights_force import main as run_insights
import plotly.express as px
import plotly.graph_objects as go
import json
from functools import lru_cache
from pathlib import Path
import sys
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from mcp_monkdb.mcp_server import run_select_query

# === Imports for Agentic Reasoning Integration ===
from agents.agent_dynamic_insights import dynamic_insights_from_schema
from langchain_ollama import ChatOllama

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
load_dotenv()
SCHEMA_TABLE = "trent.products"
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

# -------------------------------------------------
# HELPERS
# -------------------------------------------------


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    res = run_select_query(sql)
    if isinstance(res, dict) and res.get("status") == "error":
        raise RuntimeError(res["message"])
    return pd.DataFrame(res or [])


def sql_quote(val: str) -> str:
    return "'" + val.replace("'", "''") + "'"


# -------------------------------------------------
# LAYOUT CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Trent Agentic AI Demo", layout="wide")
st.image("logo.png", width=250)
st.title("Product Trends Agentic AI: Data → Deployment")

# -------------------------------------------------
# FILTERS
# -------------------------------------------------
brands_df = q(f"SELECT DISTINCT brand FROM {SCHEMA_TABLE} ORDER BY 1")
brands = brands_df["brand"].dropna().tolist() if not brands_df.empty else []

c1, c2, c3 = st.columns([1, 2, 2])
min_disc, max_disc = c1.slider("Discount % Range", 0, 90, (0, 90))
min_rating, max_rating = c2.slider("Rating Range", 0.0, 5.0, (0.0, 5.0), 0.1)
selected_brands = c3.multiselect("Brands", brands, default=brands)

where_clauses = ["1=1"]
if selected_brands:
    brand_csv = ",".join(sql_quote(b) for b in selected_brands)
    where_clauses.append(f"brand IN ({brand_csv})")
where_clauses.append(
    f"discount_percent BETWEEN {int(min_disc)} AND {int(max_disc)}")
where_clauses.append(f"rating BETWEEN {min_rating} AND {max_rating}")
where_clause = " AND ".join(where_clauses)

# -------------------------------------------------
# KPIs
# -------------------------------------------------
kpis_df = q(f"""
    SELECT
      COUNT(*) AS products,
      ROUND(AVG(price),2) AS avg_price,
      ROUND(AVG(mrp),2) AS avg_mrp,
      ROUND(AVG(discount_percent),2) AS avg_discount_pct,
      SUM(CASE WHEN price = mrp THEN 1 ELSE 0 END) AS no_discount_items
    FROM {SCHEMA_TABLE}
    WHERE {where_clause}
""")

kpis = kpis_df.iloc[0] if not kpis_df.empty else pd.Series(
    {"products": 0, "avg_price": 0, "avg_mrp": 0,
        "avg_discount_pct": 0, "no_discount_items": 0}
)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Products", int(kpis["products"]))
with k2:
    st.metric("Avg Price", kpis["avg_price"])
with k3:
    st.metric("Avg MRP", kpis["avg_mrp"])
with k4:
    st.metric("Avg Discount %", kpis["avg_discount_pct"])
with k5:
    st.metric("No-discount Items", int(kpis["no_discount_items"]))

# -------------------------------------------------
# CORE CHARTS
# -------------------------------------------------
st.subheader("Top Brands (5)")
t_brands = q(f"""
    SELECT brand, COUNT(*) AS product_count, AVG(mrp) AS mrp
    FROM {SCHEMA_TABLE}
    WHERE {where_clause}
    GROUP BY brand
    ORDER BY product_count DESC
    LIMIT 5;
""")

if not t_brands.empty:
    fig = go.Figure(data=[
        go.Bar(name='Product Count',
               x=t_brands['brand'], y=t_brands['product_count'], marker_color='#2ca02c'),
        go.Bar(name='Avg. MRP', x=t_brands['brand'],
               y=t_brands['mrp'], marker_color='#d62728')
    ])
    fig.update_layout(barmode='group', xaxis_title='Brand',
                      yaxis_title='Value', legend_title='Metric', height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for top brands with current filters.")

# -------------------------------------------------
# BRAND METRICS
# -------------------------------------------------
st.subheader("Brand: Avg Price vs Avg Discount")
brand_metrics_df = q(f"""
    SELECT brand, AVG(price) AS avg_price, AVG(discount_percent) AS avg_discount_percent
    FROM {SCHEMA_TABLE}
    WHERE brand IS NOT NULL AND price IS NOT NULL AND discount_percent IS NOT NULL AND {where_clause}
    GROUP BY brand
""")
if not brand_metrics_df.empty:
    fig = px.bar(brand_metrics_df, x="brand", y=["avg_price", "avg_discount_percent"],
                 barmode="group", title="Average Price vs Discount % by Brand",
                 labels={"value": "Value", "brand": "Brand",
                         "variable": "Metric"},
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(xaxis_tickangle=-45, height=500, legend_title="Metric")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No brand metrics available.")

# -------------------------------------------------
# DISCOUNT BANDS
# -------------------------------------------------
bands = q(f"""
    SELECT band, COUNT(*) AS items
    FROM (
      SELECT CASE
        WHEN discount_percent = 0 THEN '0%'
        WHEN discount_percent < 20 THEN '0-20%'
        WHEN discount_percent < 40 THEN '20-40%'
        WHEN discount_percent < 60 THEN '40-60%'
        ELSE '60%+'
      END AS band
      FROM {SCHEMA_TABLE}
      WHERE {where_clause}
    ) b
    GROUP BY band
    ORDER BY items DESC
""")
st.subheader("Discount bands")
if not bands.empty:
    fig = px.bar(bands, x="items", y="band", orientation="h", title="Items per Discount Band",
                 color="band", color_discrete_sequence=px.colors.qualitative.Set2)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for discount bands.")

# -------------------------------------------------
# PRICE BUCKETS
# -------------------------------------------------
price_buckets = q(f"""
    SELECT CASE
      WHEN price < 500 THEN '<500'
      WHEN price < 1000 THEN '500-999'
      WHEN price < 2000 THEN '1000-1999'
      WHEN price < 5000 THEN '2000-4999'
      ELSE '5000+'
    END AS price_bucket,
    COUNT(*) AS items,
    ROUND(AVG(discount_percent),2) AS avg_discount_pct
    FROM {SCHEMA_TABLE}
    WHERE {where_clause}
    GROUP BY price_bucket
    ORDER BY items DESC
""")
c4, c5 = st.columns(2)
with c4:
    st.subheader("Price buckets")
    if not price_buckets.empty:
        st.plotly_chart(px.bar(price_buckets, x="price_bucket", y="items",
                               color="price_bucket", color_discrete_sequence=px.colors.qualitative.Pastel),
                        use_container_width=True)
with c5:
    st.subheader("Avg discount by price bucket")
    if not price_buckets.empty:
        st.plotly_chart(px.bar(price_buckets, x="price_bucket", y="avg_discount_pct",
                               color="price_bucket", color_discrete_sequence=px.colors.qualitative.Bold),
                        use_container_width=True)

# =====================================================================
# 🤖 Autonomous AI-Generated Insights (Reasoning Output)
# =====================================================================
st.divider()
st.subheader("Autonomous AI-Generated Insights")

sample_df = q(f"SELECT * FROM {SCHEMA_TABLE} LIMIT 10")
schema_info = {
    "columns": list(sample_df.columns),
    "preview_markdown": sample_df.head(5).to_markdown(index=False),
    "summary_markdown": "Streamlit live call — generating autonomous KPIs based on schema."
}
llm = ChatOllama(model="mistral")

if st.button("Generate Live AI Insights"):
    with st.spinner("Reasoning over data and generating SQLs..."):
        results = dynamic_insights_from_schema(
            table_name=SCHEMA_TABLE,
            table_ddl=TABLE_DDL,
            schema_info=schema_info,
            reference_sqls=[q.format(table=SCHEMA_TABLE)
                            for q in REFERENCE_SQLS],
        )

    if not results:
        st.warning("No AI insights returned.")
    else:
        st.success(f"Generated {len(results)} insights dynamically!")
        for name, df in results.items():
            st.markdown(f"### {name.replace('_', ' ').title()}")
            st.dataframe(df, use_container_width=True, hide_index=True)

# =====================================================================
# Insights Pack Section (manual insights)
# =====================================================================
st.divider()
st.subheader("Insights Packs (Manual Generator)")

PACKS_DIR = Path("analytics_out/packs")
PACKS_DIR.mkdir(parents=True, exist_ok=True)

with st.form("filters_form"):
    st.subheader("Filter products")
    all_brands = brands_df["brand"].dropna().unique(
    ).tolist() if not brands_df.empty else []
    col1, col2 = st.columns(2)
    with col1:
        brands_inc = st.multiselect("Include Brands", options=all_brands)
        exclude_brands = st.multiselect("Exclude Brands", options=all_brands)
        title_ilike = st.text_input("Title contains (ILIKE)", "")
        top_limit = st.number_input("Top Rated Limit", 1, 100, 10)
    with col2:
        min_discount = st.slider("Min Discount %", 0, 100, 0)
        max_discount = st.slider("Max Discount %", 0, 100, 100)
        price_range = st.slider("Price Between", 0.0, 5000.0, (0.0, 5000.0))
        mrp_range = st.slider("MRP Between", 0.0, 5000.0, (0.0, 5000.0))
    submitted = st.form_submit_button("Run Insights")

if submitted:
    filters = {
        "brands": brands_inc,
        "exclude_brands": exclude_brands,
        "title_ilike": title_ilike.strip() or None,
        "min_discount": min_discount,
        "max_discount": max_discount,
        "price_between": list(price_range),
        "mrp_between": list(mrp_range),
        "top_limit": top_limit
    }
    filters = {k: v for k, v in filters.items() if v not in [None, [], ""]}
    try:
        sys.argv = ["gen_insights_force.py",
                    "--filters-json", json.dumps(filters)]
        pack = run_insights()
    except Exception as e:
        st.error(f"Failed to generate insights: {e}")
        st.stop()
    st.success("Pack generated successfully!")
    st.markdown("### Summary Bullets")
    for b in pack.get("bullets", []):
        st.write(f"• {b}")
    st.markdown("### Tables")
    tables = pack.get("tables", {})
    cols = st.columns(max(1, min(3, len(tables))))
    for i, (name, rows) in enumerate(tables.items()):
        with cols[i % len(cols)]:
            st.markdown(f"**{name.replace('_', ' ').title()}**")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
