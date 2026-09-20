"""Direct HTTP image downloader for game posters with rate limiting, resume, and sanitization."""
from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from src.config import (
    DEFAULT_IMAGE_HEADERS,
    DETAILS_CSV_PATH,
    DETAILS_JSON_PATH,
    DOWNLOAD_LOG_PATH,
    IMAGES_DIR,
)
from src.utils import get_image_target_path, safe_name


def is_image_already_downloaded(title: str, category: str, images_dir: Path = IMAGES_DIR) -> Path | None:
    """Check if image already exists on disk and is not empty (> 500 bytes)."""
    stem = f"{safe_name(title)} - {safe_name(category)}"
    for ext in (".jpg", ".png", ".webp", ".gif", ".jpeg"):
        p = images_dir / f"{stem}{ext}"
        if p.exists() and p.stat().st_size > 500:
            return p
    return None


def fetch_image(url: str, headers: dict[str, str] = DEFAULT_IMAGE_HEADERS, timeout: int = 45) -> bytes:
    """Perform a single HTTP GET request to fetch image binary data."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_single_image(
    row: dict[str, Any],
    images_dir: Path = IMAGES_DIR,
    max_retries: int = 3,
    delay_between_retries: float = 2.0,
) -> dict[str, Any]:
    """Download a single game poster image with retry logic."""
    title = row.get("title") or "unknown"
    category = row.get("category") or "unknown"
    image_url = (row.get("image") or "").strip()

    result = {
        "title": title,
        "category": category,
        "image_url": image_url,
        "file": "",
        "status": "",
        "error": "",
        "size_bytes": 0,
    }

    if not image_url:
        result["status"] = "skip"
        result["error"] = "no_image_url"
        return result

    existing_file = is_image_already_downloaded(title, category, images_dir)
    if existing_file:
        result["status"] = "already_exists"
        result["file"] = str(existing_file.name)
        result["size_bytes"] = existing_file.stat().st_size
        return result

    dest_path = get_image_target_path(title, category, image_url, images_dir)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_retries + 1):
        try:
            data = fetch_image(image_url)
            if len(data) < 200:
                raise ValueError(f"Image too small ({len(data)} bytes), likely an error page")

            dest_path.write_bytes(data)
            result["status"] = "downloaded"
            result["file"] = str(dest_path.name)
            result["size_bytes"] = len(data)
            return result

        except Exception as e:
            if attempt < max_retries:
                time.sleep(delay_between_retries * attempt)
            else:
                result["status"] = "error"
                result["error"] = str(e)
                return result

    return result


def download_all_images(
    csv_path: Path = DETAILS_CSV_PATH,
    json_path: Path = DETAILS_JSON_PATH,
    images_dir: Path = IMAGES_DIR,
    log_path: Path = DOWNLOAD_LOG_PATH,
    max_workers: int = 4,
    sleep_between_requests: float = 0.5,
) -> dict[str, int]:
    """Download all game poster images from dataset."""
    images_dir.mkdir(parents=True, exist_ok=True)

    # Load rows from CSV or JSON
    rows: list[dict[str, Any]] = []
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    elif json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        rows = data.get("games", [])
    else:
        raise FileNotFoundError(f"Neither {csv_path} nor {json_path} found.")

    print(f"Starting image download check for {len(rows)} games...")

    stats = {"already_exists": 0, "downloaded": 0, "skip": 0, "error": 0}
    log_records: list[dict[str, Any]] = []

    # Sequential or low-concurrency to avoid 429 rate limits
    for i, row in enumerate(rows, 1):
        res = download_single_image(row, images_dir=images_dir)
        status = res["status"]
        stats[status] = stats.get(status, 0) + 1
        log_records.append(res)

        if status == "downloaded":
            print(f"[{i}/{len(rows)}] Downloaded: {res['file']} ({res['size_bytes']} bytes)")
            time.sleep(sleep_between_requests)
        elif status == "already_exists":
            pass
        elif status == "error":
            print(f"[{i}/{len(rows)}] Error downloading {row.get('title')}: {res['error']}")

        if i % 50 == 0:
            print(f"Progress: {i}/{len(rows)} checked. (Downloaded: {stats['downloaded']}, Existing: {stats['already_exists']}, Errors: {stats['error']})")

    # Write log file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["title", "category", "status", "file", "size_bytes", "error", "image_url"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in log_records:
            writer.writerow(r)

    print("\nImage Download Summary:")
    print(f"  - Total checked: {len(rows)}")
    print(f"  - Already existed: {stats['already_exists']}")
    print(f"  - Newly downloaded: {stats['downloaded']}")
    print(f"  - Skipped (no URL): {stats['skip']}")
    print(f"  - Errors: {stats['error']}")
    print(f"Log written to: {log_path}")

    return stats
