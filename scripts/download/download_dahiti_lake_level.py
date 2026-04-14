"""
Download Lake Tanganyika water level time series from DAHITI.

DAHITI (Database for Hydrological Time Series of Inland Waters) provides
satellite altimetry-derived water levels for inland lakes and rivers.
Lake Tanganyika is available as object ID 6.

Source: https://dahiti.dgfi.tum.de/en/products/water-level-inland-waters/
Data:   Satellite altimetry, ~10-day intervals, ~1992–present

Output:
    outputs/dahiti/lake_tanganyika_water_level.csv

Setup
-----
1. Register (free) at https://dahiti.dgfi.tum.de/en/register/
2. Log in and find your API key at https://dahiti.dgfi.tum.de/en/profile/
3. pip install requests
4. Run:
       python scripts/download/download_dahiti_lake_level.py --api-key <key>

   Or set environment variable:
       DAHITI_API_KEY
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

DAHITI_API_URL     = "https://dahiti.dgfi.tum.de/api/v2/"
LAKE_TANGANYIKA_ID = 25  # DAHITI object ID for Lake Tanganyika (API v2)

OUTPUT_DIR  = Path(__file__).resolve().parent.parent.parent / "data" / "outputs" / "dahiti"
OUTPUT_PATH = OUTPUT_DIR / "lake_tanganyika_water_level.csv"


def fetch_water_level(api_key: str) -> list[dict]:
    try:
        import requests
    except ImportError:
        log.error("requests not installed. Run:  pip install requests")
        sys.exit(1)

    log.info("Fetching water level data for Lake Tanganyika (ID=%d) …", LAKE_TANGANYIKA_ID)
    resp = requests.get(
        DAHITI_API_URL + "download-water-level/",
        params={"api_key": api_key, "dahiti_id": LAKE_TANGANYIKA_ID, "format": "json"},
        timeout=60,
    )
    if resp.status_code != 200:
        log.error("Request failed (status %d): %s", resp.status_code, resp.text[:500])
        sys.exit(1)

    data = resp.json()
    # v2 response: {"data": [...]} or a list directly
    entries = data.get("data", data) if isinstance(data, dict) else data
    log.info("  Received %d records", len(entries))
    return entries


def run(api_key: str) -> None:
    entries = fetch_water_level(api_key)

    rows = []
    for e in entries:
        rows.append({
            "date":          e.get("datetime"),
            "water_level_m": e.get("wse"),
            "uncertainty_m": e.get("wse_u"),
        })

    rows = [r for r in rows if r["date"] is not None]
    rows.sort(key=lambda r: r["date"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "water_level_m", "uncertainty_m"])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Saved %d rows → %s", len(rows), OUTPUT_PATH)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Lake Tanganyika water level from DAHITI (API v2)."
    )
    parser.add_argument("--api-key", default=os.environ.get("DAHITI_API_KEY"), help="DAHITI API key")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if not args.api_key:
        print("Provide your API key via --api-key or the DAHITI_API_KEY environment variable.")
        print("Find your key at: https://dahiti.dgfi.tum.de/en/profile/")
        sys.exit(1)
    run(args.api_key)
