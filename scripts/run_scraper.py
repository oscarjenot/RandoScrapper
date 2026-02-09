#!/usr/bin/env python3
"""Run the scraper and save hikes to the default SQLite DB."""

import argparse
import sys
import time
from pathlib import Path

# Allow importing rando_scrapper from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from rando_scrapper.scraper import (
    fetch_all_post_urls,
    parse_hike_page,
    save_hikes_to_db,
)

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "hikes.db"


def main():
    parser = argparse.ArgumentParser(
        description="Scrape randoromandie.com and save to SQLite"
    )
    parser.add_argument(
        "--max-pages", type=int, default=0, help="Max listing pages (0 = all)"
    )
    parser.add_argument(
        "--max-hikes", type=int, default=0, help="Max hikes to scrape (0 = all)"
    )
    parser.add_argument(
        "--delay", type=float, default=0.8, help="Delay between requests (seconds)"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=DEFAULT_DB, help="Output DB path"
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "RandoScrapper/1.0 (hike browser project)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr,en;q=0.9",
        }
    )

    print("Fetching post URLs...")
    max_pages = args.max_pages or 200
    urls = fetch_all_post_urls(session, max_pages=max_pages)
    if args.max_hikes and len(urls) > args.max_hikes:
        urls = urls[: args.max_hikes]
        print(f"Limiting to first {len(urls)} hikes.")
    print(f"Found {len(urls)} hike URLs.")

    hikes = []
    for i, url in enumerate(urls):
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            hike = parse_hike_page(url, r.text)
            hikes.append(hike)
            print(f"[{i+1}/{len(urls)}] {hike.title[:55]}...")
        except Exception as e:
            print(f"Error {url}: {e}")
        time.sleep(args.delay)

    if not hikes:
        print("No hikes scraped. Check the site or your connection.")
        return 1
    save_hikes_to_db(hikes, args.output)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
