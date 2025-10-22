"""
Insight Agent
Generates AI-powered insights from database data.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from core.monkdb_client import MonkDBClient
from core.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


def safe_round(value, digits=2):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


class InsightAgent:
    """
    Agent responsible for generating data insights using AI.
    """

    def __init__(self, db_client: MonkDBClient,
                 ollama_client: OllamaClient,
                 insights_dir: str = "insights"):
        """
        Initialize insight agent.

        Args:
            db_client: MonkDB client instance
            ollama_client: Ollama client instance
            insights_dir: Directory to save insights
        """
        self.db = db_client
        self.ollama = ollama_client
        self.insights_dir = Path(insights_dir)
        self.insights_dir.mkdir(parents=True, exist_ok=True)

        logger.info("✅ Insight Agent initialized")

    def generate_insights(self) -> Dict[str, Any]:
        """
        Generate comprehensive insights from database.

        Returns:
            Dictionary containing all insights
        """
        logger.info("🧠 Generating insights...")

        insights = {
            "generated_at": datetime.now().isoformat(),
            "summary_stats": {},
            "top_brands": [],
            "rating_distribution": [],
            "product_segments": [],
            "outliers": [],
            "ai_insights": "",
            "executive_summary": ""
        }

        try:
            # Get summary statistics
            insights['summary_stats'] = self.db.get_summary_stats()

            # Get top brands
            top_brands_df = self.db.query_top_brands(limit=10)
            insights['top_brands'] = top_brands_df.to_dict(
                'records') if not top_brands_df.empty else []

            # Get rating distribution
            rating_dist_df = self.db.query_rating_distribution()
            insights['rating_distribution'] = rating_dist_df.to_dict(
                'records') if not rating_dist_df.empty else []

            # Get product segments
            segments_df = self.db.query_product_segments()
            insights['product_segments'] = segments_df.to_dict(
                'records') if not segments_df.empty else []

            # Get outliers
            outliers_df = self.db.query_outliers()
            insights['outliers'] = outliers_df.to_dict(
                'records') if not outliers_df.empty else []

            # Generate AI insights
            logger.info("🤖 Generating AI insights...")

            ai_summary = {
                "total_products": insights['summary_stats'].get('total_products', 0) or 0,
                "total_brands": insights['summary_stats'].get('total_brands', 0) or 0,
                "avg_price": safe_round(insights['summary_stats'].get('avg_price')),
                "avg_rating": safe_round(insights['summary_stats'].get('avg_rating')),
                "avg_discount": safe_round(insights['summary_stats'].get('avg_discount')),
                "top_3_brands": [b.get('brand', '') for b in insights['top_brands'][:3]],
                "outlier_count": len(insights['outliers'])
            }

            insights['ai_insights'] = self.ollama.generate_insights(ai_summary)
            insights['executive_summary'] = self.ollama.generate_report_summary(
                insights)

            # Save insights
            self._save_insights(insights)

            logger.info("✅ Insights generated successfully")
            return insights

        except Exception as e:
            logger.error(f"❌ Failed to generate insights: {e}")
            return insights

    def _save_insights(self, insights: Dict[str, Any]):
        """Save insights to JSON file."""
        try:
            filepath = self.insights_dir / "ai_summary.json"
            with open(filepath, 'w') as f:
                json.dump(insights, f, indent=2)
            logger.info(f"💾 Insights saved to {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to save insights: {e}")

    def load_insights(self) -> Dict[str, Any]:
        """Load insights from JSON file."""
        try:
            filepath = self.insights_dir / "ai_summary.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load insights: {e}")

        return {}
