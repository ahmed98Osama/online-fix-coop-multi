"""Helper utility functions for sanitization, category parsing, and path generation."""
from __future__ import annotations

import re
from pathlib import Path

INVALID_WIN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MULTI_SPACE = re.compile(r"\s+")
HTML_TAGS = re.compile(r"<[^>]+>")
CAT_RE = re.compile(r"https?://online-fix\.me/games/([^/]+)/", re.I)


def clean_text(text: str | None) -> str | None:
    """Strip HTML tags and normalize whitespace."""
    if not text:
        return None
    cleaned = HTML_TAGS.sub("", text)
    cleaned = MULTI_SPACE.sub(" ", cleaned).strip()
    return cleaned or None


def safe_filename(text: str | None, max_len: int = 120) -> str:
    """Sanitize text for safe use as a Windows file or directory name."""
    s = (text or "").strip()
    s = INVALID_WIN_CHARS.sub("", s)
    s = s.replace("™", "").replace("®", "").replace("©", "")
    s = MULTI_SPACE.sub(" ", s).strip(" .")
    if not s:
        s = "unknown"
    if len(s) > max_len:
        s = s[:max_len].rstrip(" .")
    return s


def category_from_url(url: str | None) -> str | None:
    """Extract game category from URL path e.g. /games/{category}/..."""
    if not url:
        return None
    m = CAT_RE.search(url)
    return m.group(1).lower() if m else None


def ext_from_url(url: str | None) -> str:
    """Extract and normalize image file extension from image URL."""
    if not url:
        return ".jpg"
    clean_path = url.split("?", 1)[0].lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if clean_path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def get_image_target_path(title: str, category: str, image_url: str, images_dir: Path) -> Path:
    """Construct destination path for image: {title} - {category}.jpg"""
    stem = f"{safe_name(title)} - {safe_name(category)}"
    ext = ext_from_url(image_url)
    return images_dir / f"{stem}{ext}"


def safe_name(text: str | None, max_len: int = 120) -> str:
    """Alias for safe_filename."""
    return safe_filename(text, max_len=max_len)
