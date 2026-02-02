#!/usr/bin/env python3
"""
Scrape Smogon draft pages for "Price Range" and append it to a CSV.

Input CSV (example): Standard_Pokemon.csv
Expected URL column: smogon_draft_url (override via --url-col)

Outputs:
- smogon_price_low_high: e.g., "8-9" or "N/A"
- smogon_price_low: numeric low bound (blank if N/A)
- smogon_price_high: numeric high bound (blank if N/A)

Usage:
  python scrape_smogon_price_range.py --input Standard_Pokemon.csv --output Standard_Pokemon_with_prices.csv
  python scrape_smogon_price_range.py --input Standard_Pokemon.csv --output out.csv --url-col smogon_draft_url --delay 0.4
"""

import argparse
import re
import time
from typing import Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


PRICE_RANGE_RE = re.compile(
    r"Price Range:\s*(?P<low>\d+)\s*-\s*(?P<high>\d+)\s*points",
    flags=re.IGNORECASE,
)
PRICE_SINGLE_RE = re.compile(
    r"Price Range:\s*(?P<val>\d+)\s*points",
    flags=re.IGNORECASE,
)


def extract_price_range_from_html(html: str) -> Optional[Tuple[int, int]]:
    """
    Return (low, high) if found, else None.
    """
    soup = BeautifulSoup(html, "lxml")

    # Smogon pages are mostly static; parsing text is usually sufficient.
    text = soup.get_text(separator=" ", strip=True)

    m = PRICE_RANGE_RE.search(text)
    if m:
        return int(m.group("low")), int(m.group("high"))

    m = PRICE_SINGLE_RE.search(text)
    if m:
        v = int(m.group("val"))
        return v, v

    return None


def fetch_html(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to input CSV")
    ap.add_argument("--output", required=True, help="Path to output CSV")
    ap.add_argument("--url-col", default="smogon_draft_url", help="Name of the URL column")
    ap.add_argument("--delay", type=float, default=0.35, help="Delay (seconds) between requests")
    ap.add_argument("--timeout", type=int, default=25, help="Request timeout (seconds)")
    args = ap.parse_args()

    df = pd.read_csv(args.input)

    if args.url_col not in df.columns:
        raise SystemExit(
            f"URL column '{args.url_col}' not found. Available columns: {list(df.columns)}"
        )

    low_high_col = "smogon_price_low_high"
    low_col = "smogon_price_low"
    high_col = "smogon_price_high"

    # Initialize columns
    df[low_high_col] = "N/A"
    df[low_col] = pd.NA
    df[high_col] = pd.NA

    for i, url in tqdm(list(df[args.url_col].items()), total=len(df), desc="Scraping"):
        if pd.isna(url) or not str(url).strip():
            continue

        url = str(url).strip()

        try:
            html = fetch_html(url, timeout=args.timeout)
            pr = extract_price_range_from_html(html)
            if pr is None:
                # leave N/A
                pass
            else:
                low, high = pr
                df.at[i, low_high_col] = f"{low}-{high}"
                df.at[i, low_col] = low
                df.at[i, high_col] = high

        except Exception:
            # Any failure -> N/A
            pass

        time.sleep(max(0.0, args.delay))

    df.to_csv(args.output, index=False)
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
