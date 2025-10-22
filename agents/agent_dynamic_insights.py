import json
import re
import pandas as pd
from typing import Dict, List
from langchain_ollama import ChatOllama
from mcp_monkdb.mcp_server import run_select_query

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
You are an experienced SQL analyst producing KPIs on a CrateDB/MonkDB table.

Table name: {table_name}

Table DDL (authoritative):
{table_ddl}
CSV sample (first rows) preview:
{preview_md}
LLM's earlier understanding:
{summary_md}

Column list (derived from CSV, for quick reference):
{columns}

REFERENCE EXAMPLES (style/mould to follow; use same table and column names):
{ref_block}

Now produce 3–5 useful SELECT queries for KPIs/insights on {table_name}.
RULES (strict):
- Use only this table: {table_name}
- SELECT-only. No INSERT/UPDATE/DELETE/DDL.
- Prefer simple aggregates or ranked lists; include LIMIT where appropriate.
- Only use columns that exist in the DDL.
- Keep queries executable as-is (no placeholders).
- Output JSON ONLY in this exact structure (no prose outside JSON):

[
  {{ "name": "kpi_slug", "sql": "SELECT ... FROM {table_name} ..." }},
  {{ "name": "another_kpi", "sql": "SELECT ... FROM {table_name} ..." }}
]
    """

    response = llm.invoke(prompt)
    text = (response.content or "").strip()
    print("\n=== AUTO-GENERATED INSIGHT PLAN (RAW) ===\n",
          text, "\n=========================================\n")

    # Parse JSON
    try:
        plan = json.loads(text)
        if not isinstance(plan, list):
            raise ValueError("Expected a JSON list")
    except Exception as e:
        print(f"⚠️ LLM response not valid JSON: {e}")
        return {}

    # Validate & execute
    results = {}
    for item in plan:
        name = item.get("name", "unnamed")
        sql = item.get("sql", "")
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

    return results
