"""
Download additional ERA5 variables for flood prediction and merge into existing CSVs.

New variables (all available in the timeseries dataset):
  - 2m_dewpoint_temperature  (d2m)  → humidity / evaporation driver
  - mean_sea_level_pressure  (msl)  → synoptic weather patterns
  - total_column_water_vapour(tcwv) → atmospheric moisture before rainfall events
  - volumetric_soil_water_layer_1(swvl1) → antecedent soil saturation → runoff

The script:
  1. Downloads the 4 extra variables for all 8 locations (full 1940–present range)
  2. Converts each to a temporary DataFrame
  3. Merges on timestamp with the existing CSVs in era5_download/csv/
  4. Overwrites the CSVs in place with the combined data

Run after download_era5.py and convert_to_csv.py have already been run.

Usage:
    python era5_download/download_era5_extra.py
"""

from __future__ import annotations

import logging
import sys
import time
import zipfile
import datetime
from pathlib import Path

import pandas as pd
import xarray as xr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — mirrors download_era5.py
# ---------------------------------------------------------------------------

DATASET = "reanalysis-era5-single-levels-timeseries"

LOCATIONS: dict[str, dict] = {
    "grid_m4.25_29.50": {"latitude": -4.25, "longitude": 29.50},
    "grid_m4.00_29.50": {"latitude": -4.00, "longitude": 29.50},
    "grid_m4.00_29.75": {"latitude": -4.00, "longitude": 29.75},
    "grid_m3.75_29.50": {"latitude": -3.75, "longitude": 29.50},
    "grid_m3.25_29.25": {"latitude": -3.25, "longitude": 29.25},
    "grid_m3.00_29.25": {"latitude": -3.00, "longitude": 29.25},
    "grid_m3.00_29.50": {"latitude": -3.00, "longitude": 29.50},
    "grid_m2.75_29.00": {"latitude": -2.75, "longitude": 29.00},
}

EXTRA_VARIABLES = [
    "2m_dewpoint_temperature",     # d2m  — humidity / evaporation driver
    "mean_sea_level_pressure",     # msl  — synoptic weather patterns
    # total_column_water_vapour and volumetric_soil_water_layer_1 are NOT available
    # in the timeseries dataset and take ~24h per variable from the full reanalysis.
]

FIRST_YEAR = 1940
END_YEAR   = datetime.date.today().year

CSV_DIR  = Path(__file__).parent / "csv"
TEMP_DIR = Path(__file__).parent / "tmp_extra"
REQUEST_PAUSE = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_nc_from_zip(zip_path: Path, out_nc: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        nc_names = [n for n in zf.namelist() if n.endswith(".nc")]
        if not nc_names:
            raise RuntimeError(f"No .nc file inside {zip_path.name}")
        zf.extract(nc_names[0], path=out_nc.parent)
        extracted = out_nc.parent / nc_names[0]
        if extracted != out_nc:
            extracted.rename(out_nc)


def download_extra(client, loc_name: str, location: dict) -> Path:
    tmp_zip = TEMP_DIR / f"extra_{loc_name}.zip"
    tmp_nc  = TEMP_DIR / f"extra_{loc_name}.nc"

    if tmp_nc.exists():
        log.info("  Temp NC already exists, skipping download: %s", tmp_nc.name)
        return tmp_nc

    log.info("  Requesting extra variables for %s …", loc_name)
    request = {
        "variable":    EXTRA_VARIABLES,
        "date":        f"{FIRST_YEAR}-01-01/{END_YEAR}-12-31",
        "location":    location,
        "data_format": "netcdf",
    }
    client.retrieve(DATASET, request, str(tmp_zip))
    _extract_nc_from_zip(tmp_zip, tmp_nc)
    tmp_zip.unlink(missing_ok=True)
    log.info("  Downloaded: %s  (%.1f MB)", tmp_nc.name, tmp_nc.stat().st_size / 1e6)
    return tmp_nc


def nc_to_df(nc_path: Path) -> pd.DataFrame:
    ds = xr.open_dataset(nc_path)
    df = ds.to_dataframe().reset_index()
    ds.close()

    time_col = "valid_time" if "valid_time" in df.columns else "time"
    df = df.rename(columns={time_col: "timestamp"})
    drop = [c for c in ["time", "latitude", "longitude", "number"] if c in df.columns]
    df = df.drop(columns=drop)
    return df.sort_values("timestamp").reset_index(drop=True)


def merge_into_csv(csv_path: Path, extra_df: pd.DataFrame) -> None:
    existing = pd.read_csv(csv_path, parse_dates=["timestamp"])

    # Drop any extra columns already present (idempotent re-runs)
    new_cols = [c for c in extra_df.columns if c != "timestamp"]
    existing = existing.drop(columns=[c for c in new_cols if c in existing.columns])

    merged = existing.merge(extra_df, on="timestamp", how="left")
    merged.to_csv(csv_path, index=False)
    log.info("  Updated CSV: %s  (%d cols, %d rows)", csv_path.name, len(merged.columns), len(merged))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    try:
        import cdsapi
    except ImportError:
        log.error("cdsapi not installed. Run:  pip install cdsapi")
        sys.exit(1)

    if not CSV_DIR.exists():
        log.error("CSV directory not found: %s\nRun download_era5.py and convert_to_csv.py first.", CSV_DIR)
        sys.exit(1)

    TEMP_DIR.mkdir(exist_ok=True)
    client = cdsapi.Client()

    log.info("Downloading extra variables for %d locations …", len(LOCATIONS))
    failed = []

    for i, (loc_name, location) in enumerate(LOCATIONS.items(), start=1):
        csv_path = CSV_DIR / f"era5_{loc_name}_{FIRST_YEAR}_{END_YEAR}.csv"
        if not csv_path.exists():
            log.warning("  [%d/%d] CSV not found, skipping: %s", i, len(LOCATIONS), csv_path.name)
            continue

        log.info("[%d/%d] %s", i, len(LOCATIONS), loc_name)
        try:
            nc_path  = download_extra(client, loc_name, location)
            extra_df = nc_to_df(nc_path)
            merge_into_csv(csv_path, extra_df)
            nc_path.unlink()
        except Exception as exc:
            log.error("  Failed (%s): %s", loc_name, exc)
            failed.append(loc_name)

        if i < len(LOCATIONS):
            time.sleep(REQUEST_PAUSE)

    # Clean up temp dir if empty
    try:
        TEMP_DIR.rmdir()
    except OSError:
        pass

    if failed:
        log.warning("Failed (re-run to retry): %s", failed)
    else:
        log.info("All done. CSVs updated with extra variables.")


if __name__ == "__main__":
    run()
