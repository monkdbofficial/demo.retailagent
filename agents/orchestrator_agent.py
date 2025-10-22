"""
Orchestrator Agent
Coordinates all agents and manages workflow.
"""

import logging
from typing import Dict, Any
from core.monkdb_client import MonkDBClient
from core.ollama_client import OllamaClient
from core.pdf_exporter import PDFExporter
from core.watcher import DirectoryWatcher
from agents.ingestion_agent import IngestionAgent
from agents.insight_agent import InsightAgent
from agents.report_agent import ReportAgent
from agents.chatbot_agent import ChatbotAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Main orchestrator that coordinates all agents.
    """

    def __init__(self, db_client: MonkDBClient, ollama_client: OllamaClient,
                 watch_dir: str = "watch_folder"):
        """
        Initialize orchestrator agent.

        Args:
            db_client: MonkDB client instance
            ollama_client: Ollama client instance
            watch_dir: Directory to watch for CSV files
        """
        self.db = db_client
        self.ollama = ollama_client

        # Initialize all agents
        self.ingestion_agent = IngestionAgent(db_client)
        self.insight_agent = InsightAgent(db_client, ollama_client)
        self.pdf_exporter = PDFExporter()
        self.report_agent = ReportAgent(self.pdf_exporter, db_client)
        self.chatbot_agent = ChatbotAgent(db_client, ollama_client)

        # Initialize watcher
        self.watcher = DirectoryWatcher(watch_dir, self.on_new_csv)

        logger.info("✅ Orchestrator Agent initialized")

    def on_new_csv(self, csv_path: str):
        """
        Callback function when new CSV is detected.

        Args:
            csv_path: Path to new CSV file
        """
        logger.info(f"🔄 New CSV detected: {csv_path}")

        try:
            # 1. Ingest data
            result = self.ingestion_agent.process_csv_file(csv_path)

            if result['status'] == 'success':
                # 2. Generate insights
                self.regenerate_insights()

                logger.info("✅ Pipeline completed successfully")
            else:
                logger.error(f"❌ Ingestion failed: {result['message']}")

        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")

    def regenerate_insights(self):
        """Regenerate insights from current database state."""
        logger.info("🔄 Regenerating insights...")

        try:
            insights = self.insight_agent.generate_insights()
            logger.info("✅ Insights regenerated")
            return insights
        except Exception as e:
            logger.error(f"❌ Failed to regenerate insights: {e}")
            return {}

    def start_watching(self):
        """Start watching directory for new files."""
        logger.info("👁️  Starting directory watcher...")
        self.watcher.start()

    def stop_watching(self):
        """Stop watching directory."""
        logger.info("⏹️  Stopping directory watcher...")
        self.watcher.stop()

    def get_chatbot_response(self, query: str) -> Dict[str, Any]:
        """Get response from chatbot agent."""
        return self.chatbot_agent.process_query(query)

    def generate_report(self, insights: Dict[str, Any],
                        chart_paths: list = None) -> str:
        """Generate PDF report."""
        return self.report_agent.generate_report(insights, chart_paths)
