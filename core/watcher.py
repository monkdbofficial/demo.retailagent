"""
File System Watcher Module
Monitors directory for new CSV files and triggers processing.
"""

import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class CSVFileHandler(FileSystemEventHandler):
    """
    Custom file system event handler for CSV files.
    """

    def __init__(self, callback: Callable[[str], None]):
        """
        Initialize handler with callback function.

        Args:
            callback: Function to call when CSV file is detected
        """
        super().__init__()
        self.callback = callback
        self.processed_files = set()

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Check if it's a CSV file
        if file_path.endswith('.csv'):
            # Avoid duplicate processing
            if file_path not in self.processed_files:
                logger.info(f"📁 New CSV file detected: {file_path}")
                self.processed_files.add(file_path)

                # Small delay to ensure file is fully written
                time.sleep(2)

                # Trigger callback
                try:
                    self.callback(file_path)
                except Exception as e:
                    logger.error(f"❌ Error processing {file_path}: {e}")

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Only process CSV files that haven't been processed
        if file_path.endswith('.csv') and file_path not in self.processed_files:
            logger.info(f"📝 CSV file modified: {file_path}")
            self.processed_files.add(file_path)

            time.sleep(2)

            try:
                self.callback(file_path)
            except Exception as e:
                logger.error(f"❌ Error processing {file_path}: {e}")


class DirectoryWatcher:
    """
    Production-grade directory watcher with robust error handling.
    """

    def __init__(self, watch_dir: str, callback: Callable[[str], None]):
        """
        Initialize directory watcher.

        Args:
            watch_dir: Directory to monitor
            callback: Function to call when CSV file is detected
        """
        self.watch_dir = Path(watch_dir)
        self.callback = callback
        self.observer = None

        # Create directory if it doesn't exist
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📂 Initialized watcher for: {self.watch_dir}")

    def start(self):
        """Start watching the directory."""
        try:
            event_handler = CSVFileHandler(self.callback)
            self.observer = Observer()
            self.observer.schedule(
                event_handler,
                str(self.watch_dir),
                recursive=False
            )
            self.observer.start()
            logger.info(f"👁️  Watching directory: {self.watch_dir}")

        except Exception as e:
            logger.error(f"❌ Failed to start watcher: {e}")
            raise

    def stop(self):
        """Stop watching the directory."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("⏹️  Directory watcher stopped")

    def is_alive(self) -> bool:
        """Check if watcher is running."""
        return self.observer and self.observer.is_alive()
