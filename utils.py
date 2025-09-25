# utils.py
import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from typing import Callable, Any

ROOT = Path(__file__).parent.resolve()

# logging config (module-level logger)
LOG_FILE = ROOT / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("agentic_ai")

def abspath(*parts: str) -> str:
    """Return an absolute path anchored to repo root for safer relative file access."""
    return str(ROOT.joinpath(*parts))

def retry(fn: Callable[..., Any], retries: int = 5, delay: float = 0.5, exc_types=(Exception,), **kwargs):
    """Simple retry wrapper used for file reads / network calls."""
    last_exc = None
    for i in range(retries):
        try:
            return fn(**kwargs) if kwargs else fn()
        except exc_types as e:
            last_exc = e
            logger.warning(f"Retry {i+1}/{retries} failed for {fn.__name__}: {e}")
            time.sleep(delay)
    logger.error(f"All retries failed for {fn.__name__}: {last_exc}")
    raise last_exc

def run_command(cmd: list[str], cwd: str | None = None, check: bool = False, timeout: int | None = None):
    """Run a subprocess command robustly and return (stdout, stderr, returncode)."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.SubprocessError as e:
        logger.exception("Subprocess failed")
        raise

def safe_read_csv(path: str, **kwargs):
    """Read CSV with retries to avoid race conditions."""
    from pandas import read_csv
    return retry(lambda: read_csv(path, **kwargs), retries=6, delay=0.5, exc_types=(FileNotFoundError, IOError))

def ensure_dir(path: str):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)
