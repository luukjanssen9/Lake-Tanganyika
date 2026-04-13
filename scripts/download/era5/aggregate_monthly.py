"""
Aggregate hourly ERA5 CSVs to monthly resolution.

Unit conversions applied before aggregation:
  t2m, d2m : K  → °C  (subtract 273.15)   — monthly mean
  tp        : m  → mm  (×1000)             — monthly sum
  msl       : Pa → hPa (/100)              — monthly mean
  u10, v10  : m/s (unchanged)              — monthly mean

Output: era5_download/csv_monthly/era5_<location>_monthly.csv
Columns: year, month, location, t2m_mean_C, d2m_mean_C, tp_sum_mm,
         msl_mean_hPa, u10_mean, v10_mean

Usage:
    python era5_download/aggregate_monthly.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

_ROOT   = Path(__file__).resolve().parent.parent.parent.parent
CSV_DIR = _ROOT / "data" / "era5" / "csv"
OUT_DIR = _ROOT / "data" / "era5" / "csv_monthly"

# Aggregation rules (applied after unit conversion)
AGG = {
    "t2m": "mean",
    "d2m": "mean",
    "tp":  "sum",
    "msl": "mean",
    "u10": "mean",
    "v10": "mean",
}

RENAME = {
    "t2m": "t2m_mean_C",
    "d2m": "d2m_mean_C",
    "tp":  "tp_sum_mm",
    "msl": "msl_mean_hPa",
    "u10": "u10_mean",
    "v10": "v10_mean",
}


def aggregate(csv_path: Path, out_dir: Path) -> None:
    loc_name = csv_path.stem.removeprefix("era5_").rsplit("_1940_", 1)[0]
    out_path = out_dir / f"era5_{loc_name}_monthly.csv"

    log.info("Processing %s …", csv_path.name)
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    # Unit conversions
    for col in ("t2m", "d2m"):
        if col in df.columns:
            df[col] = df[col] - 273.15          # K → °C
    if "tp" in df.columns:
        df["tp"] = df["tp"] * 1000              # m → mm
    if "msl" in df.columns:
        df["msl"] = df["msl"] / 100             # Pa → hPa

    df = df.set_index("timestamp")

    # Only aggregate columns that exist
    present = {k: v for k, v in AGG.items() if k in df.columns}
    monthly = df[list(present.keys())].resample("MS").agg(present)

    monthly = monthly.rename(columns={k: RENAME[k] for k in present})
    monthly.index.name = "month_start"
    monthly = monthly.reset_index()
    monthly.insert(0, "location", loc_name)

    monthly.to_csv(out_path, index=False)
    log.info("  → %s  (%d rows, %d cols)", out_path.name, len(monthly), len(monthly.columns))


def run() -> None:
    if not CSV_DIR.exists():
        log.error("CSV directory not found: %s", CSV_DIR)
        return

    files = sorted(CSV_DIR.glob("era5_grid_m*.csv"))
    if not files:
        log.error("No ERA5 CSVs found in %s", CSV_DIR)
        return

    OUT_DIR.mkdir(exist_ok=True)
    log.info("Aggregating %d files to monthly resolution …", len(files))

    for f in files:
        try:
            aggregate(f, OUT_DIR)
        except Exception as exc:
            log.error("  Failed (%s): %s", f.name, exc)

    log.info("Done. Monthly CSVs written to %s", OUT_DIR)


if __name__ == "__main__":
    run()
