from __future__ import annotations

import html
from datetime import date
from pathlib import Path

BASE_URL = "https://greatdatalabs.github.io/great-generator/"
DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
SITEMAP_PATH = DOCS_DIR / "sitemap.xml"

EXCLUDED_DIRS = {
    "assets",
    "adr",
    "rfcs",
    "__pycache__",
}
EXCLUDED_FILES = {
    "404.html",
}


def _url_for_html(path: Path) -> str:
    relative = path.relative_to(DOCS_DIR).as_posix()
    if relative == "index.html":
        return BASE_URL
    if relative.endswith("/index.html"):
        slug = relative[: -len("index.html")]
        return BASE_URL + slug
    slug = relative.removesuffix(".html") + "/"
    return BASE_URL + slug


def _lastmod(path: Path) -> str:
    timestamp = path.stat().st_mtime
    return date.fromtimestamp(timestamp).isoformat()


def discover_pages() -> list[Path]:
    pages: list[Path] = []
    for path in DOCS_DIR.rglob("*.html"):
        relative_parts = set(path.relative_to(DOCS_DIR).parts[:-1])
        if relative_parts & EXCLUDED_DIRS:
            continue
        if path.name in EXCLUDED_FILES:
            continue
        if path.name.startswith("google") and path.name.endswith(".html"):
            continue
        pages.append(path)
    return sorted(pages, key=lambda item: _url_for_html(item))


def build_sitemap(pages: list[Path]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in pages:
        loc = html.escape(_url_for_html(page), quote=False)
        lines.extend(
            [
                "  <url>",
                f"    <loc>{loc}</loc>",
                f"    <lastmod>{_lastmod(page)}</lastmod>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    pages = discover_pages()
    if not pages:
        raise SystemExit("No public HTML pages found under docs/.")
    SITEMAP_PATH.write_text(build_sitemap(pages), encoding="utf-8")
    print(f"Wrote {SITEMAP_PATH} with {len(pages)} URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
