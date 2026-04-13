"""
Convert merged ERA5 NetCDF files to CSV.

Reads  raw/<location>/era5_<location>_1940_2026.nc
Writes csv/era5_<location>_1940_2026.csv

Each CSV has one row per hour with columns:
    timestamp, latitude, longitude, t2m, tp, u10, v10, e, ro, pev

Usage:
    python era5_download/convert_to_csv.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import xarray as xr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent / "raw"
CSV_DIR = Path(__file__).parent / "csv"


def convert(nc_path: Path, csv_path: Path) -> None:
    ds = xr.open_dataset(nc_path)
    df = ds.to_dataframe().reset_index()

    # Drop redundant index columns if present, keep valid_time as timestamp
    if "valid_time" in df.columns:
        df = df.rename(columns={"valid_time": "timestamp"})
    if "time" in df.columns:
        df = df.drop(columns=["time"])

    df = df.sort_values("timestamp").reset_index(drop=True)
    df.to_csv(csv_path, index=False)
    ds.close()
    log.info("  Saved: %s  (%.1f MB)", csv_path.name, csv_path.stat().st_size / 1e6)


def main() -> None:
    CSV_DIR.mkdir(exist_ok=True)

    nc_files = sorted(RAW_DIR.rglob("era5_*_1940_2026.nc"))
    if not nc_files:
        log.error("No merged NetCDF files found. Run merge_era5.py first.")
        return

    log.info("Converting %d file(s) to CSV …", len(nc_files))
    for nc_path in nc_files:
        csv_path = CSV_DIR / nc_path.with_suffix(".csv").name
        if csv_path.exists():
            log.info("  Already exists, skipping: %s", csv_path.name)
            continue
        log.info("[%s]", nc_path.parent.name)
        convert(nc_path, csv_path)

    log.info("Done. CSVs in: %s", CSV_DIR)


if __name__ == "__main__":
    main()
