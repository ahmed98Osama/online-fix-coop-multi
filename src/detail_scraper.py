"""Scrapes individual game detail pages to extract CO-OP, MULTIPLAYER, views, post date, and poster images."""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

from src.config import (
    DEFAULT_HEADERS,
    DETAILS_CSV_PATH,
    DETAILS_JSON_PATH,
    DETAILS_MD_PATH,
    FIRECRAWL_API_KEY,
    LISTING_JSON_PATH,
    PROGRESS_PATH,
)
from src.utils import category_from_url, clean_text

COOP_MULTI_RE = re.compile(
    r'(?is)<div class="coop1">\s*(?:КООПЕРАТИВ|CO-?OP|Cooperative)\s*:\s*([^<]*?)\s*</div>\s*'
    r'(?:&nbsp;|\s)*'
    r'<div class="multi1">\s*(?:МУЛЬТИПЛЕЕР|MULTIPLAYER|Multiplayer)\s*:\s*([^<]*?)\s*</div>'
)
COOP_ONLY_RE = re.compile(
    r'(?is)<div class="coop1">\s*(?:КООПЕРАТИВ|CO-?OP|Cooperative)\s*:\s*([^<]*?)\s*</div>'
)
MULTI_ONLY_RE = re.compile(
    r'(?is)<div class="multi1">\s*(?:МУЛЬТИПЛЕЕР|MULTIPLAYER|Multiplayer)\s*:\s*([^<]*?)\s*</div>'
)
VIEWS_RE = re.compile(
    r'(?is)<div class="views[^\"]*">\s*(?:<span[^>]*>.*?</span>\s*)?([\d\s]+)'
)
TIME_RE = re.compile(r'(?is)<time datetime="([^"]+)">\s*([^<]*?)\s*</time>')
H1_RE = re.compile(r"(?is)<h1[^>]*>(.*?)</h1>")


def parse_game_page(html: str, url: str) -> dict[str, Any]:
    """Parse HTML of a single game page to extract detailed metadata."""
    coop = None
    multiplayer = None
    m = COOP_MULTI_RE.search(html)
    if m:
        coop, multiplayer = m.group(1).strip(), m.group(2).strip()
    else:
        cm = COOP_ONLY_RE.search(html)
        mm = MULTI_ONLY_RE.search(html)
        if cm:
            coop = cm.group(1).strip()
        if mm:
            multiplayer = mm.group(1).strip()

    views = None
    vm = VIEWS_RE.search(html)
    if vm:
        views = int(re.sub(r"\s+", "", vm.group(1)))

    post_datetime = None
    post_date = None
    tm = TIME_RE.search(html)
    if tm:
        post_datetime = tm.group(1).strip()
        post_date = tm.group(2).strip()

    title = None
    hm = H1_RE.search(html)
    if hm:
        title = clean_text(hm.group(1))

    return {
        "url": url,
        "title": title,
        "category": category_from_url(url),
        "coop": coop,
        "multiplayer": multiplayer,
        "views": views,
        "post_date": post_date,
        "post_datetime": post_datetime,
    }


def export_dataset(
    games: list[dict[str, Any]],
    json_path: Path = DETAILS_JSON_PATH,
    csv_path: Path = DETAILS_CSV_PATH,
    md_path: Path = DETAILS_MD_PATH,
) -> None:
    """Export the enriched dataset into JSON, CSV, and Markdown formats."""
    json_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. JSON Export
    payload = {"games_count": len(games), "games": games}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. CSV Export
    fields = [
        "title",
        "url",
        "category",
        "coop",
        "multiplayer",
        "views",
        "post_date",
        "post_datetime",
        "image",
        "release_date",
        "play_via",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for g in games:
            writer.writerow(g)

    # 3. Markdown Export
    counts: dict[str, int] = {}
    for g in games:
        c = g.get("category") or "unknown"
        counts[c] = counts.get(c, 0) + 1

    lines = [
        "# Online-Fix Games (CO-OP + MULTIPLAYER Details)",
        "",
        f"- **Total Games**: **{len(games)}**",
        "",
        "## Categories Breakdown",
        "",
    ]
    for cat, num in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- `{cat}`: {num}")

    lines += [
        "",
        "| # | Image | Title | Category | COOP | MULTI | Views | Post date | Via | URL |",
        "|---|-------|-------|----------|------|-------|-------|-----------|-----|-----|",
    ]
    for i, r in enumerate(games, 1):
        img = r.get("image") or ""
        img_cell = f"![img]({img})" if img else ""
        lines.append(
            f"| {i} | {img_cell} | {r.get('title') or ''} | {r.get('category') or ''} | "
            f"{r.get('coop') or ''} | {r.get('multiplayer') or ''} | {r.get('views') or ''} | "
            f"{r.get('post_date') or ''} | {r.get('play_via') or ''} | {r.get('url') or ''} |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported {len(games)} records to:")
    print(f"  - {json_path}")
    print(f"  - {csv_path}")
    print(f"  - {md_path}")


def load_input_games() -> list[dict[str, Any]]:
    """Load games from existing details file or listing file."""
    if DETAILS_JSON_PATH.exists():
        data = json.loads(DETAILS_JSON_PATH.read_text(encoding="utf-8"))
        return data.get("games", [])
    if LISTING_JSON_PATH.exists():
        data = json.loads(LISTING_JSON_PATH.read_text(encoding="utf-8"))
        return data.get("games", [])
    raise FileNotFoundError(f"Neither {DETAILS_JSON_PATH} nor {LISTING_JSON_PATH} found.")


def scrape_details(
    games: list[dict[str, Any]] | None = None,
    resume: bool = True,
    chunk_size: int = 30,
) -> list[dict[str, Any]]:
    """Scrape details for all games, supporting resume from progress."""
    if games is None:
        games = load_input_games()

    progress: dict[str, Any] = {}
    if resume and PROGRESS_PATH.exists():
        try:
            progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except Exception:
            progress = {}

    done_by_url = progress.get("by_url", {})

    print(f"Total games to scrape: {len(games)} (already completed: {len(done_by_url)})")

    for i, g in enumerate(games, 1):
        u = g["url"]
        if resume and u in done_by_url:
            g.update(done_by_url[u])
            continue

        try:
            req = urllib.request.Request(u, headers=DEFAULT_HEADERS, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            parsed = parse_game_page(html, u)
            if parsed.get("title"):
                g["title"] = parsed["title"]
            g["category"] = parsed.get("category") or category_from_url(u)
            g["coop"] = parsed.get("coop")
            g["multiplayer"] = parsed.get("multiplayer")
            g["views"] = parsed.get("views")
            g["post_date"] = parsed.get("post_date")
            g["post_datetime"] = parsed.get("post_datetime")

            done_by_url[u] = {
                "title": g.get("title"),
                "category": g.get("category"),
                "coop": g.get("coop"),
                "multiplayer": g.get("multiplayer"),
                "views": g.get("views"),
                "post_date": g.get("post_date"),
                "post_datetime": g.get("post_datetime"),
            }
            print(f"[{i}/{len(games)}] Scraped {g.get('title')} | COOP: {g.get('coop')} | MULTI: {g.get('multiplayer')}")
            time.sleep(1)

        except Exception as e:
            print(f"[{i}/{len(games)}] Error on {u}: {e}")

        if i % 10 == 0:
            PROGRESS_PATH.write_text(json.dumps({"by_url": done_by_url}, ensure_ascii=False), encoding="utf-8")

    export_dataset(games)
    return games
