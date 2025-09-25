# csv_insertation_batch.py
import os
import sys
import time
import logging
from pathlib import Path
import pandas as pd
import dask.dataframe as  dd
from dask.distributed import Client, LocalCluster

from utils import logger

# monk client - ensure this import path is correct
from monkdb import client as monk_client

# Config from config.ini (keep your config loading; sample omitted for brevity)
import configparser
CURRENT_DIR = Path(__file__).parent
CONFIG_FILE_PATH = CURRENT_DIR / "config" / "config.ini"
config = configparser.ConfigParser()
config.read(CONFIG_FILE_PATH)

DB_HOST = config.get("database", "DB_HOST")
DB_PORT = config.get("database", "DB_PORT")
DB_USER = config.get("database", "DB_USER")
DB_PASSWORD = config.get("database", "DB_PASSWORD")
DB_SCHEMA = config.get("database", "DB_SCHEMA")
TABLE_NAME = config.get("database", "TABLE_NAME")

BLOCKSIZE = "64MB"
N_WORKERS = min((os.cpu_count() or 4), 8)
THREADS_PER_W = 2
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))

INSERT_SQL = f"""
INSERT INTO {DB_SCHEMA}.{TABLE_NAME}
(product_id, style_id, title, brand, price, mrp, discount_percent, rating, rating_total, img_primary, img_count)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

def _as_int(x):
    try:
        if pd.isna(x):
            return None
        return int(float(x))
    except Exception:
        return None

def _as_float(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None

def _as_str(x):
    try:
        if pd.isna(x):
            return None
        s = str(x)
        return s if s.lower() != "nan" else None
    except Exception:
        return None

def _connect(retries=3, delay=1.0):
    for i in range(retries):
        try:
            url = f"http://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
            conn = monk_client.connect(url, username=DB_USER)
            return conn
        except Exception as e:
            logger.warning(f"Connect attempt {i+1} failed: {e}")
            time.sleep(delay)
    raise RuntimeError("Failed to connect to MonkDB after retries")

def _ingest_partition(pdf: pd.DataFrame) -> pd.DataFrame:
    if pdf.empty:
        return pd.DataFrame({"rows_inserted": [0]})
    cols_needed = ["product_id", "style_id", "title", "brand", "price", "mrp",
                   "discount_percent", "rating", "rating_total", "img_primary", "img_count"]
    for c in cols_needed:
        if c not in pdf.columns:
            pdf[c] = None

    batch = []
    total = 0
    conn = _connect()
    cur = conn.cursor()
    try:
        for _, row in pdf.iterrows():
            values = (
                _as_int(row["product_id"]),
                _as_int(row["style_id"]),
                _as_str(row["title"]),
                _as_str(row["brand"]),
                _as_float(row["price"]),
                _as_float(row["mrp"]),
                _as_float(row["discount_percent"]),
                _as_float(row["rating"]),
                _as_int(row["rating_total"]),
                _as_str(row["img_primary"]),
                _as_int(row["img_count"]),
            )
            batch.append(values)
            if len(batch) >= BATCH_SIZE:
                cur.executemany(INSERT_SQL, batch)
                conn.commit()
                total += len(batch)
                logger.info(f"Inserted batch of {len(batch)} rows")
                batch.clear()
        if batch:
            cur.executemany(INSERT_SQL, batch)
            conn.commit()
            total += len(batch)
            logger.info(f"Inserted final batch of {len(batch)} rows")
    except Exception as e:
        logger.exception(f"Error inserting partition: {e}")
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass
    return pd.DataFrame({"rows_inserted": [total]})

def main(csv_file_path: str):
    logger.info("Starting orchestrator ingestion")
    if not Path(csv_file_path).exists():
        logger.error("CSV not found: %s", csv_file_path)
        raise FileNotFoundError(csv_file_path)

    cluster = LocalCluster(n_workers=N_WORKERS, threads_per_worker=THREADS_PER_W, processes=True, dashboard_address=None)
    client = Client(cluster)
    try:
        ddf = dd.read_csv(csv_file_path, blocksize=BLOCKSIZE, assume_missing=True, dtype=str, encoding="utf-8", on_bad_lines="skip")
        for col in ["product_id","style_id","title","brand","price","mrp","discount_percent","rating","rating_total","img_primary","img_count"]:
            if col not in ddf.columns:
                ddf[col] = None
                logger.warning("Column missing, filling with None: %s", col)
        results = ddf.map_partitions(_ingest_partition, meta={"rows_inserted":"int64"}).compute()
        total_inserted = int(results["rows_inserted"].sum()) if not results.empty else 0
        logger.info("Inserted %d rows", total_inserted)
    finally:
        client.close()
        cluster.close()
    return total_inserted

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python csv_insertation_batch.py <csv_file>")
        sys.exit(1)
    csv = sys.argv[1].strip()
    print(f"[DEBUG] Current working dir: {os.getcwd()}")
    print(f"[DEBUG] Received path: '{csv}'")
    print(f"[DEBUG] Files in dir: {os.listdir(os.path.dirname(csv))}")
    main(csv)
