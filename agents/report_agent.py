"""
Report Agent
Generates PDF reports with visualizations.
"""

import logging
from typing import Dict, Any
from core.pdf_exporter import PDFExporter
from core.monkdb_client import MonkDBClient

logger = logging.getLogger(__name__)


class ReportAgent:
    """
    Agent responsible for generating PDF reports.
    """

    def __init__(self, pdf_exporter: PDFExporter, db_client: MonkDBClient):
        """
        Initialize report agent.

        Args:
            pdf_exporter: PDF exporter instance
            db_client: MonkDB client instance
        """
        self.pdf = pdf_exporter
        self.db = db_client
        logger.info("✅ Report Agent initialized")

    def generate_report(self, insights: Dict[str, Any],
                        chart_paths: list = None) -> str:
        """
        Generate PDF report from insights.

        Args:
            insights: Insights dictionary
            chart_paths: List of chart image paths

        Returns:
            Path to generated PDF
        """
        logger.info("📄 Generating PDF report...")

        try:
            pdf_path = self.pdf.generate_report(insights, chart_paths or [])

            if pdf_path:
                logger.info(f"✅ Report generated: {pdf_path}")
            else:
                logger.error("❌ Report generation failed")

            return pdf_path

        except Exception as e:
            logger.error(f"❌ Error generating report: {e}")
            return ""
