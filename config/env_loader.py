"""
Environment Configuration Loader
Loads configuration from .env and config.ini files.
"""

import os
from pathlib import Path
from configparser import ConfigParser
from dotenv import load_dotenv


def load_config():
    """
    Load configuration from environment and config files.

    Returns:
        Dictionary with configuration values
    """
    # Load .env file if exists
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    # Load config.ini
    config_path = Path(__file__).parent / 'config.ini'
    config = ConfigParser()

    if config_path.exists():
        config.read(config_path)

    # Build configuration dictionary
    return {
        'monkdb': {
            'host': os.getenv('MONKDB_HOST', 'localhost'),
            'port': os.getenv('MONKDB_PORT', '4200'),
            'user': os.getenv('MONKDB_USER', 'testuser'),
            'password': os.getenv('MONKDB_PASSWORD', 'testpassword'),
            'schema': os.getenv('MONKDB_SCHEMA', 'monkdb')
        },
        'ollama': {
            'base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'model': os.getenv('OLLAMA_MODEL', 'mistral')
        },
        'watcher': {
            'watch_dir': os.getenv('WATCH_DIR', 'watch_folder')
        }
    }
