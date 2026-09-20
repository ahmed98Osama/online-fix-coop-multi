"""Main CLI entrypoint for the Online-Fix Scraper and Dataset project."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Ensure src package can be imported directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import (
    DATA_DIR,
    DEFAULT_TOTAL_PAGES,
    DETAILS_CSV_PATH,
    DETAILS_JSON_PATH,
    DETAILS_MD_PATH,
    IMAGES_DIR,
    LISTING_JSON_PATH,
)
from src.detail_scraper import scrape_details
from src.image_downloader import download_all_images
from src.listing_scraper import scrape_listings


def print_summary() -> None:
    """Display comprehensive dataset statistics."""
    print("=" * 60)
    print(" ONLINE-FIX DATASET & REPOSITORY SUMMARY")
    print("=" * 60)

    # 1. Dataset stats
    if DETAILS_JSON_PATH.exists():
        data = json.loads(DETAILS_JSON_PATH.read_text(encoding="utf-8"))
        games = data.get("games", [])
        total = len(games)

        has_coop = sum(1 for g in games if g.get("coop") is not None)
        has_multi = sum(1 for g in games if g.get("multiplayer") is not None)
        has_views = sum(1 for g in games if g.get("views") is not None)
        has_date = sum(1 for g in games if g.get("post_date"))

        # Category breakdown
        cat_counts: dict[str, int] = {}
        for g in games:
            c = g.get("category") or "unknown"
            cat_counts[c] = cat_counts.get(c, 0) + 1

        print(f"Total Games in Dataset: {total}")
        print(f"  - With CO-OP value:      {has_coop}/{total}")
        print(f"  - With MULTIPLAYER value:{has_multi}/{total}")
        print(f"  - With Views count:      {has_views}/{total}")
        print(f"  - With Post Date:        {has_date}/{total}")

        print("\nCategories Breakdown:")
        for cat, count in sorted(cat_counts.items(), key=lambda x: (-x[1], x[0])):
            print(f"  - {cat:<20}: {count}")
    else:
        print("Details dataset not found at:", DETAILS_JSON_PATH)

    # 2. Images stats
    if IMAGES_DIR.exists():
        images = list(IMAGES_DIR.glob("*.*"))
        valid_images = [img for img in images if img.is_file() and img.suffix.lower() in {".jpg", ".png", ".webp", ".gif"}]
        total_size_mb = sum(img.stat().st_size for img in valid_images) / (1024 * 1024)
        print(f"\nLocal Images Directory ({IMAGES_DIR}):")
        print(f"  - Downloaded images count: {len(valid_images)}")
        print(f"  - Total disk space:        {total_size_mb:.2f} MB")
    else:
        print("\nImages directory not found at:", IMAGES_DIR)

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Online-Fix Co-op & Multiplayer Scraper CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: summary
    subparsers.add_parser("summary", help="Show current dataset and local image stats")

    # Command: scrape-listings
    p_listings = subparsers.add_parser("scrape-listings", help="Scrape coop listing pages 1..N")
    p_listings.add_argument("--pages", type=int, default=DEFAULT_TOTAL_PAGES, help=f"Total pages to crawl (default: {DEFAULT_TOTAL_PAGES})")
    p_listings.add_argument("--no-firecrawl", action="store_true", help="Scrape directly via HTTP instead of Firecrawl API")

    # Command: scrape-details
    p_details = subparsers.add_parser("scrape-details", help="Scrape game detail pages (COOP, MULTI, views, date)")
    p_details.add_argument("--no-resume", action="store_true", help="Do not resume from cached progress")

    # Command: download-images
    p_images = subparsers.add_parser("download-images", help="Download poster images directly via HTTP")
    p_images.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between downloads (default: 0.5)")

    # Command: run-all
    p_all = subparsers.add_parser("run-all", help="Execute complete pipeline (listings -> details -> images)")
    p_all.add_argument("--pages", type=int, default=DEFAULT_TOTAL_PAGES, help=f"Total pages to crawl (default: {DEFAULT_TOTAL_PAGES})")

    args = parser.parse_args()

    if not args.command or args.command == "summary":
        print_summary()
    elif args.command == "scrape-listings":
        scrape_listings(total_pages=args.pages, use_firecrawl=not args.no_firecrawl)
    elif args.command == "scrape-details":
        scrape_details(resume=not args.no_resume)
    elif args.command == "download-images":
        download_all_images(sleep_between_requests=args.delay)
    elif args.command == "run-all":
        print("Starting complete pipeline execution...")
        scrape_listings(total_pages=args.pages)
        scrape_details()
        download_all_images()
        print_summary()


if __name__ == "__main__":
    main()
