"""
Main Entry Point for MonkDB Agent System
Runs the complete autonomous pipeline and launches Streamlit dashboard.
"""

import logging
import sys
import time
import subprocess
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monkdb_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

from config.env_loader import load_config
from core.monkdb_client import MonkDBClient
from core.ollama_client import OllamaClient
from agents.orchestrator_agent import OrchestratorAgent


def launch_streamlit_dashboard():
    """Launch Streamlit dashboard in a subprocess."""
    dashboard_path = Path("dashboard/app.py")
    if dashboard_path.exists():
        logger.info("🌐 Launching Streamlit dashboard...")
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
    else:
        logger.warning("⚠️ Dashboard file not found, skipping Streamlit launch.")


def main():
    """Main function to run the agent system."""

    logger.info("=" * 80)
    logger.info("🚀 Starting MonkDB Agent System")
    logger.info("=" * 80)

    try:
        # Load configuration
        config = load_config()
        print(config)
        logger.info("✅ Configuration loaded")

        logger.info("Connecting to DB")

        # Initialize MonkDB client
        db_client = MonkDBClient(
            host=config['monkdb']['host'],
            port=int(config['monkdb']['port']),
            user=config['monkdb']['user'],
            password=config['monkdb']['password'],
            schema=config['monkdb']['schema']
        )
        logger.info("✅ MonkDB client initialized")

        # Check database health
        health = db_client.health_check()
        if health['status'] != 'ok':
            logger.error(f"❌ Database health check failed: {health['message']}")
            return

        # Initialize Ollama client
        ollama_client = OllamaClient(
            base_url=config['ollama']['base_url'],
            model=config['ollama']['model']
        )
        logger.info("✅ Ollama client initialized")

        # Check Ollama health
        if not ollama_client.health_check():
            logger.warning("⚠️ Ollama server not accessible - AI features will be limited")

        # Initialize orchestrator
        orchestrator = OrchestratorAgent(
            db_client,
            ollama_client,
            watch_dir=config['watcher']['watch_dir']
        )
        logger.info("✅ Orchestrator initialized")

        # Start watching directory for new CSVs
        orchestrator.start_watching()
        logger.info("👁️ Directory watcher started")

        # Launch Streamlit dashboard automatically
        launch_streamlit_dashboard()

        # Keep running
        logger.info("=" * 80)
        logger.info("✅ System is running. Watching for new CSV files...")
        logger.info(f"📁 Watch folder: {config['watcher']['watch_dir']}/")
        logger.info("🌐 Dashboard is running and will auto-refresh on new data")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n⏹️ Stopping system...")
            orchestrator.stop_watching()
            db_client.close()
            logger.info("✅ System stopped gracefully")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
