"""
Download Lake Tanganyika water level time series from DAHITI.

DAHITI (Database for Hydrological Time Series of Inland Waters) provides
satellite altimetry-derived water levels for inland lakes and rivers.
Lake Tanganyika is available as object ID 6.

Source: https://dahiti.dgfi.tum.de/en/products/water-level-inland-waters/
Data:   Satellite altimetry, ~10-day intervals, ~1992–present

Output:
    outputs/lake_tanganyika_water_level.csv

Setup
-----
1. Register (free) at https://dahiti.dgfi.tum.de/en/register/
2. pip install requests
3. Run:
       python scripts/download_dahiti_lake_level.py --username <u> --password <p>

   Or set environment variables:
       DAHITI_USER and DAHITI_PASS
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

DAHITI_API_URL  = "https://dahiti.dgfi.tum.de/api/v1/"
LAKE_TANGANYIKA_ID = 6   # DAHITI object ID for Lake Tanganyika

OUTPUT_DIR  = Path(__file__).resolve().parent.parent.parent / "data" / "outputs" / "dahiti"
OUTPUT_PATH = OUTPUT_DIR / "lake_tanganyika_water_level.csv"


def fetch_water_level(username: str, password: str) -> list[dict]:
    try:
        import requests
    except ImportError:
        log.error("requests not installed. Run:  pip install requests")
        sys.exit(1)

    log.info("Authenticating with DAHITI …")
    session = requests.Session()

    # Authenticate
    auth_resp = session.post(
        DAHITI_API_URL + "auth/",
        json={"username": username, "password": password},
        timeout=30,
    )
    if auth_resp.status_code != 200:
        log.error("Authentication failed (status %d): %s", auth_resp.status_code, auth_resp.text)
        sys.exit(1)

    token = auth_resp.json().get("token")
    if not token:
        log.error("No token in response: %s", auth_resp.json())
        sys.exit(1)

    headers = {"Authorization": f"Token {token}"}

    log.info("Fetching water level data for Lake Tanganyika (ID=%d) …", LAKE_TANGANYIKA_ID)
    data_resp = session.get(
        DAHITI_API_URL + f"water-level/{LAKE_TANGANYIKA_ID}/",
        headers=headers,
        timeout=60,
    )
    if data_resp.status_code != 200:
        log.error("Data request failed (status %d): %s", data_resp.status_code, data_resp.text)
        sys.exit(1)

    entries = data_resp.json()
    log.info("  Received %d records", len(entries))
    return entries


def run(username: str, password: str) -> None:
    entries = fetch_water_level(username, password)

    rows = []
    for e in entries:
        rows.append({
            "date":            e.get("date"),
            "water_level_m":   e.get("water_level"),
            "uncertainty_m":   e.get("uncertainty"),
        })

    rows.sort(key=lambda r: r["date"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "water_level_m", "uncertainty_m"])
        writer.writeheader()
        writer.writerows(rows)

    log.info("Saved %d rows → %s", len(rows), OUTPUT_PATH)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Lake Tanganyika water level from DAHITI."
    )
    parser.add_argument("--username", default=os.environ.get("DAHITI_USER"), help="DAHITI username")
    parser.add_argument("--password", default=os.environ.get("DAHITI_PASS"), help="DAHITI password")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if not args.username or not args.password:
        print("Provide credentials via --username/--password or DAHITI_USER/DAHITI_PASS env vars.")
        sys.exit(1)
    run(args.username, args.password)
