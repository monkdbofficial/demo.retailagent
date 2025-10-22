"""
Ingestion Agent
Handles CSV file ingestion into MonkDB.
"""

import logging
from pathlib import Path
from typing import Dict, Any
from core.monkdb_client import MonkDBClient

logger = logging.getLogger(__name__)


class IngestionAgent:
    """
    Agent responsible for ingesting CSV data into MonkDB.
    """

    def __init__(self, db_client: MonkDBClient):
        """
        Initialize ingestion agent.

        Args:
            db_client: MonkDB client instance
        """
        self.db = db_client
        logger.info("✅ Ingestion Agent initialized")

    def process_csv_file(self, csv_path: str) -> Dict[str, Any]:
        """
        Process a single CSV file.

        Args:
            csv_path: Path to CSV file

        Returns:
            Processing result dictionary
        """
        logger.info(f"📥 Processing CSV file: {csv_path}")

        try:
            # Ensure table exists
            self.db.create_table_if_not_exists()

            # Insert products
            result = self.db.insert_products_from_csv(csv_path)

            if result['status'] == 'success':
                logger.info(
                    f"✅ Successfully ingested {result['inserted']} products")
            else:
                logger.error(f"❌ Ingestion failed: {result['message']}")

            return result

        except Exception as e:
            logger.error(f"❌ Error processing file: {e}")
            return {
                "status": "error",
                "file": csv_path,
                "message": str(e)
            }

    def validate_csv(self, csv_path: str) -> bool:
        """
        Validate CSV file before processing.

        Args:
            csv_path: Path to CSV file

        Returns:
            True if valid, False otherwise
        """
        try:
            import pandas as pd
            df = pd.read_csv(csv_path, nrows=1)

            required_cols = ['product_id', 'title', 'brand', 'price']
            missing = [col for col in required_cols if col not in df.columns]

            if missing:
                logger.error(f"❌ Missing columns: {missing}")
                return False

            logger.info("✅ CSV validation passed")
            return True

        except Exception as e:
            logger.error(f"❌ CSV validation failed: {e}")
            return False
