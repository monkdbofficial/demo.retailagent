# watchdog_.py
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from utils import abspath, logger
from pathlib import Path

class CSVHandler(FileSystemEventHandler):
    def __init__(self, folder_to_watch):
        self.folder_to_watch = folder_to_watch

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            file_path = event.src_path
            logger.info("CSV created: %s", file_path)
            for i in range(6):
                if Path(file_path).exists():
                    break
                time.sleep(0.5)
            try:
                subprocess.run(['python3', abspath("langchain_orch.py"), file_path], check=True)
            except Exception as e:
                logger.exception("Failed to invoke orchestrator: %s", e)

if __name__ == "__main__":
    folder_to_watch = os.path.abspath('csv_folder')
    Path(folder_to_watch).mkdir(parents=True, exist_ok=True)
    event_handler = CSVHandler(folder_to_watch)
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()
    logger.info("Watching folder: %s", folder_to_watch)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
