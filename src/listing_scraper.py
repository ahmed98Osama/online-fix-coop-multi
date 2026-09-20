"""Scrapes online-fix.me /coop/ listing pages and filters for games with fa-check for both Coop and Multiplayer."""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

from src.config import (
    DEFAULT_HEADERS,
    DEFAULT_TOTAL_PAGES,
    FIRECRAWL_API_KEY,
    LISTING_BASE_URL,
    LISTING_JSON_PATH,
    LISTING_MD_PATH,
)
from src.utils import category_from_url

# Regex to verify BOTH Cooperative and Multiplayer have fa-check
BOTH_CHECK_RE = re.compile(
    r"(?is)(?:Режимы|Modes)\s*:</b>\s*"
    r"(?:Кооператив|Cooperative)\s*<span class=\"fa fa-check\"></span>\s*\\?\s*"
    r"(?:Мультиплеер|Multiplayer)\s*<span class=\"fa fa-check\"></span>"
)

ARTICLE_RE = re.compile(r"(?is)<article class=\"news\">(.*?)</article>")
TITLE_RE = re.compile(
    r'(?is)<h2[^>]*>\s*<a[^>]+href="(https?://online-fix\.me/games/[^"]+)"[^>]*>\s*([^<]+?)\s*</a>'
)
LINK_RE = re.compile(
    r'(?is)<a class="(?:img|big-link)"[^>]*href="(https?://online-fix\.me/games/[^"]+)"'
)
ALT_TITLE_RE = re.compile(r'(?is)<img[^>]+alt="([^"]+)"')
RELEASE_RE = re.compile(r"(?is)<b>(?:Релиз игры|Game release):</b>\s*([^<\n]+)")
VIA_RE = re.compile(r'(?is)<b>(?:Игра через|Play via):</b>\s*<a[^>]*>([^<]+)</a>')
POSTED_SIMPLE_RE = re.compile(
    r'(?is)<a href="https://online-fix\.me/\d{4}/\d{2}/\d{2}/"[^>]*>([^<]+)</a>\s*(\d+)'
)
POSTER_IMG_RE = re.compile(
    r'(?is)<a class="img"[^>]*href="(https?://online-fix\.me/games/[^"]+)"[^>]*>\s*'
    r'<img[^>]+(?:data-src|src)="(https?://online-fix\.me/uploads/posts/[^"]+)"'
)


def generate_listing_urls(total_pages: int = DEFAULT_TOTAL_PAGES) -> list[str]:
    """Generate all listing page URLs from 1 to total_pages."""
    urls = [LISTING_BASE_URL]
    for i in range(2, total_pages + 1):
        urls.append(f"{LISTING_BASE_URL}page/{i}/")
    return urls


def parse_articles(html: str, source_page: str) -> list[dict[str, Any]]:
    """Parse article cards and retain only those matching both coop and multiplayer fa-check."""
    games = []
    for art in ARTICLE_RE.findall(html):
        if not BOTH_CHECK_RE.search(art):
            continue

        url = None
        title = None
        tm = TITLE_RE.search(art)
        if tm:
            url, title = tm.group(1), tm.group(2).strip()
        else:
            lm = LINK_RE.search(art)
            am = ALT_TITLE_RE.search(art)
            if lm:
                url = lm.group(1)
            if am:
                title = am.group(1).strip()

        if not url or not title:
            continue

        release = None
        rm = RELEASE_RE.search(art)
        if rm:
            release = rm.group(1).strip()

        via = None
        vm = VIA_RE.search(art)
        if vm:
            via = vm.group(1).strip()

        posted = None
        views = None
        pm = POSTED_SIMPLE_RE.search(art)
        if pm:
            posted = pm.group(1).strip()
            views = int(pm.group(2))

        poster = None
        pim = POSTER_IMG_RE.search(art)
        if pim:
            poster = pim.group(2)

        games.append(
            {
                "title": title,
                "url": url,
                "category": category_from_url(url),
                "release_date": release,
                "play_via": via,
                "posted_date": posted,
                "views": views,
                "image": poster,
                "modes": ["Кооператив", "Мультиплеер"],
                "coop_check": True,
                "multi_check": True,
                "source_page": source_page,
            }
        )
    return games


def fetch_direct(url: str) -> str:
    """Direct HTTP request using standard urllib."""
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def firecrawl_batch_scrape(urls: list[str], api_key: str) -> list[dict]:
    """Execute Firecrawl batch scrape API call."""
    payload = json.dumps({
        "urls": urls,
        "formats": ["rawHtml"],
        "onlyMainContent": False,
        "timeout": 90000,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.firecrawl.dev/v1/batch/scrape",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode("utf-8"))

    if not res.get("success"):
        raise RuntimeError(f"Firecrawl batch start failed: {res}")

    job_id = res["id"]
    print(f"Firecrawl batch job started: {job_id} ({len(urls)} URLs)")

    while True:
        status_req = urllib.request.Request(
            f"https://api.firecrawl.dev/v1/batch/scrape/{job_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        with urllib.request.urlopen(status_req, timeout=120) as s_resp:
            status_data = json.loads(s_resp.read().decode("utf-8"))

        status = status_data.get("status")
        completed = status_data.get("completed", 0)
        total = status_data.get("total", len(urls))
        print(f"  Batch status: {status} ({completed}/{total})")

        if status in ("completed", "failed"):
            break
        time.sleep(5)

    if status != "completed":
        raise RuntimeError(f"Batch scrape failed: {status_data}")

    return status_data.get("data") or []


def scrape_listings(
    total_pages: int = DEFAULT_TOTAL_PAGES,
    use_firecrawl: bool = True,
    output_json: Path = LISTING_JSON_PATH,
    output_md: Path = LISTING_MD_PATH,
) -> list[dict[str, Any]]:
    """Scrape listing pages and save games matching both coop and multiplayer."""
    urls = generate_listing_urls(total_pages)
    all_games: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    pages_scraped = 0

    if use_firecrawl and FIRECRAWL_API_KEY:
        print(f"Scraping {len(urls)} pages via Firecrawl Batch API...")
        items = firecrawl_batch_scrape(urls, FIRECRAWL_API_KEY)
        for item in items:
            meta = item.get("metadata") or {}
            page_url = meta.get("sourceURL") or meta.get("url") or ""
            html = item.get("rawHtml") or ""
            if not html:
                continue
            pages_scraped += 1
            for g in parse_articles(html, page_url):
                if g["url"] not in seen_urls:
                    seen_urls.add(g["url"])
                    all_games.append(g)
    else:
        print(f"Scraping {len(urls)} pages directly via HTTP...")
        for i, url in enumerate(urls, 1):
            try:
                html = fetch_direct(url)
                pages_scraped += 1
                for g in parse_articles(html, url):
                    if g["url"] not in seen_urls:
                        seen_urls.add(g["url"])
                        all_games.append(g)
                print(f"  [{i}/{len(urls)}] Scraped {url} - total matches: {len(all_games)}")
                time.sleep(1)
            except Exception as e:
                print(f"  Error on {url}: {e}")

    # Write output JSON
    payload = {
        "filter": "Кооператив fa-check AND Мультиплеер fa-check",
        "pages_requested": total_pages,
        "pages_scraped": pages_scraped,
        "games_count": len(all_games),
        "games": all_games,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write output Markdown
    lines = [
        "# Coop + Multi (Both fa-check Checked)",
        "",
        f"- **Pages scraped**: {pages_scraped}/{total_pages}",
        f"- **Matching Games**: **{len(all_games)}**",
        "",
        "| # | Title | Category | Via | Release | Views | URL |",
        "|---|-------|----------|-----|---------|-------|-----|",
    ]
    for idx, g in enumerate(all_games, 1):
        lines.append(
            f"| {idx} | {g['title']} | {g.get('category') or ''} | {g.get('play_via') or ''} | "
            f"{g.get('release_date') or ''} | {g.get('views') or ''} | {g['url']} |"
        )
    output_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Listing scrape complete. Found {len(all_games)} games across {pages_scraped} pages.")
    print(f"Saved: {output_json} and {output_md}")
    return all_games
