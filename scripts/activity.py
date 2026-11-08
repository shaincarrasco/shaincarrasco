#!/usr/bin/env python3
"""Draw the last year of GitHub contributions as an SVG in the portfolio's palette,
and write the total into README.md between the activity markers.

Standard library only. In GitHub Actions it reads GITHUB_TOKEN and queries GraphQL.
For local testing: python3 scripts/activity.py --fixture tests/calendar.json
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

USER = "shaincarrasco"
ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT / "assets" / "activity.svg"
README = ROOT / "README.md"
START, END = "<!-- activity:start -->", "<!-- activity:end -->"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""

# Night ground, then four steps of the poster amber. Level 0 is an empty cell.
COLORS = ["#141a20", "#4a3a1e", "#7d5d24", "#b5812f", "#e3a33c"]
CELL, GAP, BG = 11, 3, "#07090c"


def fetch(token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-activity"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(count: int, cutoffs: list[int]) -> int:
    if count <= 0:
        return 0
    for i, c in enumerate(cutoffs, start=1):
        if count <= c:
            return i
    return 4


def render(calendar: dict) -> str:
    weeks = calendar["weeks"]
    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"] > 0)
    # Quartiles of active days, so one huge day does not wash out the rest.
    if counts:
        q = lambda p: counts[min(len(counts) - 1, int(p * len(counts)))]
        cutoffs = [q(0.25), q(0.5), q(0.75)]
    else:
        cutoffs = [1, 2, 3]
    width = len(weeks) * (CELL + GAP) - GAP
    height = 7 * (CELL + GAP) - GAP
    cells = []
    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:
            # GitHub weeks start on Sunday; a partial first week is padded at the top.
            y = (date.fromisoformat(day["date"]).weekday() + 1) % 7
            fill = COLORS[level(day["contributionCount"], cutoffs)]
            cells.append(
                f'<rect x="{x * (CELL + GAP)}" y="{y * (CELL + GAP)}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}">'
                f'<title>{day["date"]}: {day["contributionCount"]}</title></rect>'
            )
    pad = 16
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width + 2 * pad}" height="{height + 2 * pad}" '
        f'viewBox="0 0 {width + 2 * pad} {height + 2 * pad}" role="img" '
        f'aria-label="{calendar["totalContributions"]} contributions in the last year">'
        f'<rect width="100%" height="100%" rx="8" fill="{BG}"/>'
        f'<g transform="translate({pad},{pad})">{"".join(cells)}</g></svg>\n'
    )


def update_readme(total: int) -> None:
    text = README.read_text()
    block = f"{START}\n**{total:,} contributions in the last year.**\n{END}"
    new, n = re.subn(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.S)
    if n != 1:
        raise SystemExit("README is missing the activity markers")
    README.write_text(new)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", help="read the calendar from a JSON file instead of the API")
    args = ap.parse_args()
    if args.fixture:
        calendar = json.loads(Path(args.fixture).read_text())
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is not set")
        calendar = fetch(token)
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render(calendar))
    update_readme(calendar["totalContributions"])
    print(f"wrote {SVG_PATH.relative_to(ROOT)}; total {calendar['totalContributions']}")


if __name__ == "__main__":
    main()
