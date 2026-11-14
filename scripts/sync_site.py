#!/usr/bin/env python3
"""Keep this profile in step with shaincarrasco.github.io.

The site publishes /profile.json (tagline + the projects it features) and /profile/banner.svg
(drawn in the site's own fonts and colours). This script copies the banner into assets/ and
rewrites the README between the banner and work markers. Change the site, and within the hour
the profile follows.

Standard library only. For local testing: python3 scripts/sync_site.py --fixture tests/site
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

SITE = "https://shaincarrasco.github.io"
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
BANNER = ROOT / "assets" / "banner.svg"
MARKERS = {
    "banner": ("<!-- banner:start -->", "<!-- banner:end -->"),
    "work": ("<!-- work:start -->", "<!-- work:end -->"),
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-site-sync", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def cell(text: str) -> str:
    """Make text safe inside a Markdown table cell."""
    return " ".join(text.split()).replace("|", "\\|")


def attr(text: str) -> str:
    return " ".join(text.split()).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def render_banner(feed: dict) -> str:
    alt = attr(f'{feed["name"]}. {feed["tagline"]}')
    return f'<a href="{feed["site"]}">\n  <img src="assets/banner.svg" alt="{alt}" width="100%">\n</a>'


def render_work(feed: dict) -> str:
    rows = ["| Project | What it is |", "| --- | --- |"]
    for w in feed["work"]:
        name = f'**[{cell(w["title"])}]({w["href"]})**'
        extra = []
        if w.get("caseStudy") and w["caseStudy"] != w["href"]:
            extra.append(f'[case study]({w["caseStudy"]})')
        if w.get("code"):
            extra.append(f'[code]({w["code"]})')
        rows.append(f'| {" · ".join([name, *extra])} | {cell(w["line"])} |')
    return "\n".join(rows)


def replace_block(text: str, key: str, body: str) -> str:
    start, end = MARKERS[key]
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"README.md is missing the {start} … {end} markers")
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text, count=1)


def validate(feed: dict, svg: bytes) -> None:
    for k in ("name", "site", "tagline", "work"):
        if not feed.get(k):
            raise ValueError(f"profile.json has no {k}")
    for w in feed["work"]:
        if not (w.get("title") and w.get("href", "").startswith("https://") and w.get("line")):
            raise ValueError(f"bad work entry: {w}")
    if not svg.lstrip().startswith(b"<svg") or len(svg) < 1000:
        raise ValueError("banner.svg does not look like an SVG")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", help="read profile.json and banner.svg from this folder instead of the site")
    args = ap.parse_args()

    try:
        if args.fixture:
            d = Path(args.fixture)
            feed_raw, svg = (d / "profile.json").read_bytes(), (d / "banner.svg").read_bytes()
        else:
            feed_raw, svg = get(f"{SITE}/profile.json"), get(f"{SITE}/profile/banner.svg")
        feed = json.loads(feed_raw)
        validate(feed, svg)
    except (OSError, ValueError) as e:  # URLError/HTTPError/missing file are OSError; bad JSON is ValueError
        # Site not deployed yet, or mid-deploy: leave the profile exactly as it is.
        print(f"Skipped: could not read the site's profile feed ({e}).")
        return 0

    text = README.read_text()
    text = replace_block(text, "banner", render_banner(feed))
    text = replace_block(text, "work", render_work(feed))
    README.write_text(text)
    BANNER.parent.mkdir(parents=True, exist_ok=True)
    BANNER.write_bytes(svg)
    print(f'Synced {len(feed["work"])} projects and the banner from {feed["site"]}.')
    return 0


if __name__ == "__main__":
    sys.exit(main())
