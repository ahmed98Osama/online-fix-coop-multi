"""Configuration, directory paths, and environment settings."""
from __future__ import annotations

import os
from pathlib import Path

# Base directories
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = PROJECT_ROOT / "images"

# Data file paths
LISTING_JSON_PATH = DATA_DIR / "online-fix-coop-multi-both.json"
LISTING_MD_PATH = DATA_DIR / "online-fix-coop-multi-both.md"
DETAILS_JSON_PATH = DATA_DIR / "online-fix-game-details.json"
DETAILS_CSV_PATH = DATA_DIR / "online-fix-game-details.csv"
DETAILS_MD_PATH = DATA_DIR / "online-fix-game-details.md"
DOWNLOAD_LOG_PATH = DATA_DIR / "_download_log.csv"
PROGRESS_PATH = DATA_DIR / ".scrape_progress.json"

# Load .env file manually or with python-dotenv
def _load_env() -> None:
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            # Fallback parser if python-dotenv is not yet installed
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v

_load_env()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "").strip()

# Default request headers for web requests
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://online-fix.me/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

DEFAULT_IMAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://online-fix.me/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

BASE_SITE_URL = "https://online-fix.me"
LISTING_BASE_URL = "https://online-fix.me/coop/"
DEFAULT_TOTAL_PAGES = 78
