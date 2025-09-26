
#!/usr/bin/env python3
"""
MonkDB / Trent Pipeline Test Runner

What it does:
- Computes KPIs from a CSV with Pandas.
- Computes the same KPIs from MonkDB via MCP `run_select_query`.
- Compares results (accuracy) and reports deltas.
- Benchmarks query latency (P50/P95/P99) for core dashboard queries.
- Optionally samples PKs from the CSV to spot-check row parity in DB.
- Exports JSON + Markdown reports.

Requirements:
- pandas, numpy, python-dotenv (optional), statistics
- Access to `mcp_monkdb.mcp_server.run_select_query` (SELECT-only MCP)
"""
import argparse
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# MCP SELECT helper
try:
    from mcp_monkdb.mcp_server import run_select_query
except Exception as e:
    run_select_query = None


# -------------------------------
# Utilities
# -------------------------------
def q(sql: str) -> pd.DataFrame:
    if run_select_query is None:
        raise RuntimeError(
            "run_select_query unavailable. Ensure MCP is installed & configured.")
    res = run_select_query(sql)
    if isinstance(res, dict) and res.get("status") == "error":
        raise RuntimeError(res["message"])
    return pd.DataFrame(res or [])


def p50(values: List[float]) -> float:
    return float(np.percentile(values, 50)) if values else 0.0


def p95(values: List[float]) -> float:
    return float(np.percentile(values, 95)) if values else 0.0


def p99(values: List[float]) -> float:
    return float(np.percentile(values, 99)) if values else 0.0


def safe_float(x) -> float:
    try:
        if x is None:
            return float("nan")
        f = float(x)
        if f != f:  # NaN
            return float("nan")
        return f
    except Exception:
        return float("nan")


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# -------------------------------
# KPI computation (Pandas & SQL)
# -------------------------------
def compute_kpis_pandas(df: pd.DataFrame) -> Dict[str, Any]:
    # Ensure numeric
    for col in ["price", "mrp", "discount_percent", "rating", "rating_total", "img_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Basic KPIs
    products = int(len(df))
    avg_price = float(round(df["price"].mean(
        skipna=True), 2)) if "price" in df.columns else 0.0
    avg_mrp = float(round(df["mrp"].mean(skipna=True), 2)
                    ) if "mrp" in df.columns else 0.0
    avg_discount_pct = float(round(df["discount_percent"].mean(
        skipna=True), 2)) if "discount_percent" in df.columns else 0.0
    no_discount_items = int(((df["price"] == df["mrp"]) if {"price", "mrp"} <= set(
        df.columns) else pd.Series([])).sum()) if {"price", "mrp"} <= set(df.columns) else 0

    # Bands
    if "discount_percent" in df.columns:
        bins = pd.cut(
            df["discount_percent"],
            bins=[-0.000001, 0, 20, 40, 60, float("inf")],
            labels=["0%", "0-20%", "20-40%", "40-60%", "60%+"],
            include_lowest=True,
        )
        discount_bands = df.assign(band=bins).groupby(
            "band", dropna=True).size().reset_index(name="items")
        discount_bands = discount_bands.sort_values("items", ascending=False)
        discount_bands = discount_bands.to_dict(orient="records")
    else:
        discount_bands = []

    # Brand concentration
    if "brand" in df.columns:
        brand_counts = df.groupby("brand", dropna=True).size().reset_index(
            name="items").sort_values("items", ascending=False)
        total = max(1, int(brand_counts["items"].sum())
                    ) if not brand_counts.empty else 1
        brand_counts["share_pct"] = (
            100.0 * brand_counts["items"] / total).round(2)
        brand_concentration = brand_counts.head(10).to_dict(orient="records")
    else:
        brand_concentration = []

    return {
        "products": products,
        "avg_price": round(avg_price, 2),
        "avg_mrp": round(avg_mrp, 2),
        "avg_discount_pct": round(avg_discount_pct, 2),
        "no_discount_items": no_discount_items,
        "discount_bands": discount_bands,
        "brand_concentration": brand_concentration,
    }


def compute_kpis_sql(table: str, where_clause: str = "1=1") -> Dict[str, Any]:
    kpis = q(f"""
        SELECT
          COUNT(*) AS products,
          ROUND(AVG(price),2) AS avg_price,
          ROUND(AVG(mrp),2) AS avg_mrp,
          ROUND(AVG(discount_percent),2) AS avg_discount_pct,
          SUM(CASE WHEN price = mrp THEN 1 ELSE 0 END) AS no_discount_items
        FROM {table}
        WHERE {where_clause}
    """)
    k = kpis.iloc[0].to_dict() if not kpis.empty else {
        "products": 0, "avg_price": 0.0, "avg_mrp": 0.0, "avg_discount_pct": 0.0, "no_discount_items": 0
    }
    # Bands
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
          FROM {table}
          WHERE {where_clause}
        ) b
        GROUP BY band
        ORDER BY items DESC
    """)
    # Brand share
    brands = q(f"""
        SELECT t.brand, t.items,
               CASE WHEN total.s > 0 THEN ROUND(100.0 * t.items / total.s, 2) ELSE 0 END AS share_pct
        FROM (
          SELECT brand, COUNT(*) AS items
          FROM {table}
          WHERE {where_clause}
          GROUP BY brand
        ) t
        CROSS JOIN (
          SELECT COUNT(*) AS s
          FROM {table}
          WHERE {where_clause}
        ) total
        ORDER BY t.items DESC
        LIMIT 10
    """)
    k["discount_bands"] = bands.to_dict(orient="records")
    k["brand_concentration"] = brands.to_dict(orient="records")
    return k


# -------------------------------
# Comparisons
# -------------------------------
def compare_numbers(name: str, csv_val: float, sql_val: float, tol: float = 1e-6) -> Dict[str, Any]:
    diff = None
    try:
        diff = float(sql_val) - float(csv_val)
    except Exception:
        pass
    passed = (abs(diff) <= tol) if diff is not None else False
    return {"metric": name, "csv": csv_val, "sql": sql_val, "delta": diff, "tolerance": tol, "pass": passed}


def compare_bands(csv_bands: List[Dict[str, Any]], sql_bands: List[Dict[str, Any]]) -> Dict[str, Any]:
    csv_map = {str(b["band"]): int(b["items"]) for b in csv_bands}
    sql_map = {str(b["band"]): int(b["items"]) for b in sql_bands}
    all_keys = sorted(set(csv_map) | set(sql_map))
    per_band = []
    all_pass = True
    for k in all_keys:
        c = csv_map.get(k, 0)
        s = sql_map.get(k, 0)
        per_band.append({"band": k, "csv": c, "sql": s,
                        "delta": s - c, "pass": c == s})
        all_pass = all_pass and (c == s)
    return {"per_band": per_band, "pass": all_pass}


def compare_brand_share(csv_rows: List[Dict[str, Any]], sql_rows: List[Dict[str, Any]], top_n: int = 10, tol_items: int = 0, tol_share: float = 0.5) -> Dict[str, Any]:
    # Compare top brands by item count and approximate share percentage
    def to_map(rows):
        return {str(r["brand"]): {"items": int(r["items"]), "share_pct": float(r.get("share_pct", 0.0))} for r in rows}
    cm = to_map(csv_rows[:top_n])
    sm = to_map(sql_rows[:top_n])
    brands = sorted(set(cm) | set(sm))
    per_brand = []
    all_pass = True
    for b in brands:
        c = cm.get(b, {"items": 0, "share_pct": 0.0})
        s = sm.get(b, {"items": 0, "share_pct": 0.0})
        item_ok = abs(s["items"] - c["items"]) <= tol_items
        share_ok = abs(s["share_pct"] - c["share_pct"]) <= tol_share
        per_brand.append({
            "brand": b,
            "csv_items": c["items"],
            "sql_items": s["items"],
            "delta_items": s["items"] - c["items"],
            "csv_share_pct": c["share_pct"],
            "sql_share_pct": s["share_pct"],
            "delta_share_pct": s["share_pct"] - c["share_pct"],
            "pass": item_ok and share_ok
        })
        all_pass = all_pass and (item_ok and share_ok)
    return {"per_brand": per_brand, "pass": all_pass}


# -------------------------------
# Performance tests
# -------------------------------
def time_query(sql: str, repeats: int = 20, sleep: float = 0.0) -> Dict[str, Any]:
    durations = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        _ = q(sql)
        durations.append((time.perf_counter() - t0) * 1000.0)  # ms
        if sleep > 0:
            time.sleep(sleep)
    return {
        "repeats": repeats,
        "p50_ms": round(p50(durations), 2),
        "p95_ms": round(p95(durations), 2),
        "p99_ms": round(p99(durations), 2),
        "max_ms": round(max(durations), 2),
        "min_ms": round(min(durations), 2)
    }


# -------------------------------
# Row parity spot-check (optional)
# -------------------------------
def row_parity_sample(csv_df: pd.DataFrame, table: str, pk_cols: List[str], sample_size: int = 1000) -> Dict[str, Any]:
    # Validate PK columns exist
    for c in pk_cols:
        if c not in csv_df.columns:
            return {"enabled": False, "reason": f"missing PK column '{c}' in CSV"}

    # Build candidate key set
    candidates = csv_df[pk_cols].dropna().drop_duplicates()

    # Nothing to sample? Bail out gracefully
    if candidates.empty:
        return {"enabled": False, "reason": "no valid PK rows after dropna/drop_duplicates"}

    # Draw up to sample_size rows (but only if > 0)
    n = min(sample_size, len(candidates))
    if n <= 0:
        return {"enabled": False, "reason": "requested sample size <= 0"}

    sample = candidates.sample(n=n, random_state=42)

    # 1- or 2-column key support
    if len(pk_cols) == 1:
        col = pk_cols[0]
        values = ",".join("'" + str(v).replace("'", "''") +
                          "'" for v in sample[col].tolist())
        sql = f"SELECT COUNT(*) AS c FROM {table} WHERE {col} IN ({values})"
    elif len(pk_cols) == 2:
        c1, c2 = pk_cols
        tuples = ",".join(
            "('" + str(r[c1]).replace("'", "''") +
            "','" + str(r[c2]).replace("'", "''") + "')"
            for _, r in sample.iterrows()
        )
        sql = f"SELECT COUNT(*) AS c FROM {table} WHERE ({c1},{c2}) IN ({tuples})"
    else:
        return {"enabled": False, "reason": "row parity sample supports up to 2 PK columns"}

    df = q(sql)
    db_count = int(df.iloc[0]["c"]) if not df.empty else 0
    csv_count = int(len(sample))
    return {
        "enabled": True,
        "sampled": csv_count,
        "db_found": db_count,
        "parity_pct": round(100.0 * db_count / max(1, csv_count), 2),
    }


# -------------------------------
# Report assembly
# -------------------------------


@dataclass
class AccuracyResult:
    kpi_deltas: List[Dict[str, Any]]
    bands: Dict[str, Any]
    brand_share: Dict[str, Any]
    row_parity_sample: Dict[str, Any]


@dataclass
class PerfResult:
    kpi_latency_ms: Dict[str, Any]
    bands_latency_ms: Dict[str, Any]
    brand_latency_ms: Dict[str, Any]


@dataclass
class TestReport:
    timestamp: str
    table: str
    where_clause: str
    csv_file: str
    env: Dict[str, Any]
    accuracy: AccuracyResult
    performance: PerfResult


def to_markdown(report: TestReport) -> str:
    r = report
    md = []
    md.append(
        f"# MonkDB / Trent — Test Report\n\n**Timestamp:** {r.timestamp}\n\n**Table:** `{r.table}`\n\n**CSV:** `{r.csv_file}`\n\n**WHERE:** `{r.where_clause}`\n")
    md.append("## 1) Accuracy\n")
    md.append(
        "| Metric | CSV | SQL | Δ | Tol | Pass |\n|---|---:|---:|---:|---:|:--:|\n")
    for row in r.accuracy.kpi_deltas:
        md.append(f"| {row['metric']} | {row['csv']} | {row['sql']} | {round(row['delta'], 6) if row['delta'] is not None else 'n/a'} | {row['tolerance']} | {'✅' if row['pass'] else '❌'} |\n")
    md.append(
        "\n**Discount bands:**\n\n| Band | CSV | SQL | Δ | Pass |\n|---|---:|---:|---:|:--:|\n")
    for b in r.accuracy.bands["per_band"]:
        md.append(
            f"| {b['band']} | {b['csv']} | {b['sql']} | {b['delta']} | {'✅' if b['pass'] else '❌'} |\n")
    md.append("\n**Brand concentration (top):**\n\n| Brand | CSV Items | SQL Items | Δ Items | CSV Share % | SQL Share % | Δ Share | Pass |\n|---|---:|---:|---:|---:|---:|---:|:--:|\n")
    for b in r.accuracy.brand_share["per_brand"]:
        md.append(f"| {b['brand']} | {b['csv_items']} | {b['sql_items']} | {b['delta_items']} | {b['csv_share_pct']} | {b['sql_share_pct']} | {round(b['delta_share_pct'], 2)} | {'✅' if b['pass'] else '❌'} |\n")
    if r.accuracy.row_parity_sample.get("enabled"):
        s = r.accuracy.row_parity_sample
        md.append(
            f"\n**Row parity sample:** {s['db_found']}/{s['sampled']} found in DB (**{s['parity_pct']}%**)\n")
    else:
        md.append(
            f"\n**Row parity sample:** skipped ({r.accuracy.row_parity_sample.get('reason', '')})\n")

    md.append("\n## 2) Performance (latency in ms)\n")
    for name, block in [("KPIs", r.performance.kpi_latency_ms), ("Discount Bands", r.performance.bands_latency_ms), ("Brand Share", r.performance.brand_latency_ms)]:
        md.append(
            f"\n### {name}\n\n| p50 | p95 | p99 | min | max | repeats |\n|---:|---:|---:|---:|---:|---:|\n")
        md.append(
            f"| {block['p50_ms']} | {block['p95_ms']} | {block['p99_ms']} | {block['min_ms']} | {block['max_ms']} | {block['repeats']} |\n")
    return "".join(md)


# -------------------------------
# Main
# -------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="MonkDB/Trent pipeline test runner")
    ap.add_argument("--csv", required=True,
                    help="Path to the CSV used for Pandas KPIs and optional parity sampling")
    ap.add_argument("--table", default="trent.products",
                    help="DB table to query")
    ap.add_argument("--where", default="1=1",
                    help="Optional WHERE clause to scope DB queries (use to align with CSV subset)")
    ap.add_argument("--pk", nargs="*", default=["product_id", "style_id"],
                    help="Primary key column(s) for row parity sampling (max 2 cols)")
    ap.add_argument("--parity-sample", type=int, default=0,
                    help="Sample size for row parity check (0 to skip)")
    ap.add_argument("--perf-repeats", type=int, default=20,
                    help="Repetitions per performance query")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="Sleep between performance repetitions (seconds)")
    ap.add_argument("--out-json", default="test_report.json",
                    help="Output JSON file")
    ap.add_argument("--out-md", default="test_report.md",
                    help="Output Markdown file")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # Load CSV lightly (dtype=str to mimic ingestion) then cast within KPIs
    csv_df = pd.read_csv(csv_path, dtype=str, keep_default_na=True,
                         on_bad_lines="skip", encoding="utf-8")
    csv_kpis = compute_kpis_pandas(csv_df)
    sql_kpis = compute_kpis_sql(args.table, args.where)

    # Accuracy comparisons
    kpi_names = [
        ("products", 0.0),
        ("avg_price", 1e-6),
        ("avg_mrp", 1e-6),
        ("avg_discount_pct", 1e-6),
        ("no_discount_items", 0.0),
    ]
    deltas = []
    for name, tol in kpi_names:
        deltas.append(compare_numbers(name, csv_kpis.get(
            name, 0), sql_kpis.get(name, 0), tol))

    bands_cmp = compare_bands(csv_kpis.get(
        "discount_bands", []), sql_kpis.get("discount_bands", []))
    brand_cmp = compare_brand_share(csv_kpis.get(
        "brand_concentration", []), sql_kpis.get("brand_concentration", []))

    # Row parity (optional)
    if args.parity_sample > 0:
        parity = row_parity_sample(
            csv_df, args.table, args.pk, sample_size=args.parity_sample)
    else:
        parity = {"enabled": False, "reason": "not requested"}

    # Performance
    kpi_sql = f"""
        SELECT
          COUNT(*) AS products,
          ROUND(AVG(price),2) AS avg_price,
          ROUND(AVG(mrp),2) AS avg_mrp,
          ROUND(AVG(discount_percent),2) AS avg_discount_pct,
          SUM(CASE WHEN price = mrp THEN 1 ELSE 0 END) AS no_discount_items
        FROM {args.table}
        WHERE {args.where}
    """
    bands_sql = f"""
        SELECT band, COUNT(*) AS items
        FROM (
          SELECT CASE
            WHEN discount_percent = 0 THEN '0%'
            WHEN discount_percent < 20 THEN '0-20%'
            WHEN discount_percent < 40 THEN '20-40%'
            WHEN discount_percent < 60 THEN '40-60%'
            ELSE '60%+'
          END AS band
          FROM {args.table}
          WHERE {args.where}
        ) b
        GROUP BY band
        ORDER BY items DESC
    """
    brand_sql = f"""
        SELECT t.brand, t.items,
               CASE WHEN total.s > 0 THEN ROUND(100.0 * t.items / total.s, 2) ELSE 0 END AS share_pct
        FROM (
          SELECT brand, COUNT(*) AS items
          FROM {args.table}
          WHERE {args.where}
          GROUP BY brand
        ) t
        CROSS JOIN (
          SELECT COUNT(*) AS s
          FROM {args.table}
          WHERE {args.where}
        ) total
        ORDER BY t.items DESC
        LIMIT 10
    """
    kpi_perf = time_query(kpi_sql, repeats=args.perf_repeats, sleep=args.sleep)
    bands_perf = time_query(
        bands_sql, repeats=args.perf_repeats, sleep=args.sleep)
    brand_perf = time_query(
        brand_sql, repeats=args.perf_repeats, sleep=args.sleep)

    report = TestReport(
        timestamp=now_iso(),
        table=args.table,
        where_clause=args.where,
        csv_file=str(csv_path),
        env={
            "perf_repeats": args.perf_repeats,
            "sleep_between_repeats_sec": args.sleep,
        },
        accuracy=AccuracyResult(
            kpi_deltas=deltas,
            bands=bands_cmp,
            brand_share=brand_cmp,
            row_parity_sample=parity
        ),
        performance=PerfResult(
            kpi_latency_ms=kpi_perf,
            bands_latency_ms=bands_perf,
            brand_latency_ms=brand_perf
        )
    )

    # Write outputs
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.write_text(json.dumps(
        asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(to_markdown(report), encoding="utf-8")

    print(f"JSON report: {out_json.resolve()}")
    print(f"Markdown report: {out_md.resolve()}")


if __name__ == "__main__":
    main()
