import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

# MCP import (SELECT-only)
from mcp_monkdb.mcp_server import run_select_query

SCHEMA_TABLE = "trent.products"  # adjust if needed

# ---------- Query helper (SELECT via MCP) ----------


@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    res = run_select_query(sql)
    if isinstance(res, dict) and res.get("status") == "error":
        raise RuntimeError(res["message"])
    return pd.DataFrame(res or [])


# ---------- App ----------
st.set_page_config(page_title="Trent Agentic AI Demo", layout="wide")
st.title("Trends Agentic AI: Data → Deployment")

# ---------- Filters ----------


def sql_quote(val: str) -> str:
    # wrap in single quotes and escape internal single quotes by doubling
    return "'" + val.replace("'", "''") + "'"


brands_df = q(f"SELECT DISTINCT brand FROM {SCHEMA_TABLE} ORDER BY 1")
brands = brands_df["brand"].dropna().tolist() if not brands_df.empty else []
c1, c2, c3 = st.columns(3)
brand_sel = c1.multiselect(
    "Brand(s)", brands, default=brands[:3] if len(brands) >= 3 else brands)
min_disc = c2.slider("Min discount %", 0, 90, 0)
min_rating = c3.slider("Min rating", 0.0, 5.0, 0.0, 0.1)

where_clauses = ["1=1"]
if brand_sel:
    brand_csv = ",".join(sql_quote(b) for b in brand_sel)
    where_clauses.append(f"brand IN ({brand_csv})")
if min_disc > 0:
    where_clauses.append(f"discount_percent >= {int(min_disc)}")
if min_rating > 0:
    where_clauses.append(f"rating >= {min_rating}")

where_sql = " AND ".join(where_clauses)

# ---------- KPIs ----------
kpis_df = q(f"""
    SELECT
      COUNT(*) AS products,
      ROUND(AVG(price),2) AS avg_price,
      ROUND(AVG(mrp),2) AS avg_mrp,
      ROUND(AVG(discount_percent),2) AS avg_discount_pct,
      SUM(CASE WHEN price = mrp THEN 1 ELSE 0 END) AS no_discount_items
    FROM {SCHEMA_TABLE}
    WHERE {where_sql}
""")
kpis = kpis_df.iloc[0] if not kpis_df.empty else pd.Series(
    {"products": 0, "avg_price": 0, "avg_mrp": 0,
        "avg_discount_pct": 0, "no_discount_items": 0}
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Products", int(kpis["products"]))
k2.metric("Avg Price", kpis["avg_price"])
k3.metric("Avg MRP", kpis["avg_mrp"])
k4.metric("Avg Discount %", kpis["avg_discount_pct"])
k5.metric("No-discount Items", int(kpis["no_discount_items"]))

# ---------- Discount bands (SELECT-wrapped, no WITH) ----------
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
      WHERE {where_sql}
    ) b
    GROUP BY band
    ORDER BY items DESC
""")
st.subheader("Discount bands")
if not bands.empty:
    st.bar_chart(bands.set_index("band")["items"])
else:
    st.info("No data for discount bands with the current filters.")

# ---------- Price bucket distribution ----------
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
    WHERE {where_sql}
    GROUP BY price_bucket
    ORDER BY items DESC
""")
c4, c5 = st.columns(2)
with c4:
    st.subheader("Price buckets")
    if not price_buckets.empty:
        st.bar_chart(price_buckets.set_index("price_bucket")["items"])
    else:
        st.info("No data for price buckets with the current filters.")
with c5:
    st.subheader("Avg discount by price bucket")
    if not price_buckets.empty:
        st.bar_chart(price_buckets.set_index(
            "price_bucket")["avg_discount_pct"])
    else:
        st.info("No data for avg discount by bucket with the current filters.")

# ---------- Top discounted & Top rated (SELECT-only) ----------
top_discounted = q(f"""
    SELECT product_id, title, brand, price, mrp, discount_percent, rating, rating_total
    FROM {SCHEMA_TABLE}
    WHERE {where_sql}
    ORDER BY discount_percent DESC, price ASC
    LIMIT 50
""")
top_rated = q(f"""
    SELECT product_id, title, brand, rating, rating_total, price, mrp, discount_percent
    FROM {SCHEMA_TABLE}
    WHERE {where_sql} AND rating_total >= 100 AND rating >= 4
    ORDER BY rating DESC, rating_total DESC
    LIMIT 50
""")

st.subheader("Top discounted (50)")
st.dataframe(top_discounted, use_container_width=True, hide_index=True)
st.subheader("Top rated by volume (50)")
st.dataframe(top_rated, use_container_width=True, hide_index=True)

st.caption(
    "Powered by MCP (SELECT-only). No writes, no schema changes from the app.")

# =====================================================================
# Multi-pack insights viewer (reads files generated by gen_insights.py)
# =====================================================================
PACKS_DIR = Path("analytics_out/packs")
PACKS_DIR.mkdir(parents=True, exist_ok=True)

st.divider()
st.subheader("Insights Packs")


@lru_cache(maxsize=256)
def load_pack(path_str: str) -> dict:
    try:
        return json.loads(Path(path_str).read_text(encoding="utf-8"))
    except Exception:
        return {}


pack_files = sorted(PACKS_DIR.glob("*.json"))
if not pack_files:
    st.info(
        "No packs found. Generate some with gen_insights.py into analytics_out/packs/")
else:
    labels = [f.stem for f in pack_files]
    chosen = st.multiselect("Select packs to view/compare",
                            options=labels, default=labels[:1])
    files_to_show = [pack_files[labels.index(lbl)] for lbl in chosen]

    cols = st.columns(max(1, min(3, len(files_to_show))))
    for i, f in enumerate(files_to_show):
        with cols[i % len(cols)]:
            st.markdown(f"**{f.stem}**")
            pack = load_pack(str(f))
            if not pack:
                st.warning("Could not read this pack.")
                continue

            bullets = pack.get("bullets") or []
            if bullets:
                for b in bullets:
                    st.write(f"• {b}")

            kpis_insight = pack.get("kpis") or {}
            if kpis_insight:
                with st.expander("Insight KPIs (JSON)"):
                    st.json(kpis_insight)

            tables = pack.get("tables") or {}
            for name, rows in tables.items():
                st.markdown(f"**{name.replace('_', ' ').title()}**")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
