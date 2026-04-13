"""
Download ERA5 hourly single-level reanalysis data for the Lake Tanganyika region.

Dataset: reanalysis-era5-single-levels-timeseries (1940 – present)
Source:  https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-timeseries

One request is made per location covering the full 1940–present date range,
producing a single NetCDF file per location. This is much faster than splitting
by year (~10 minutes total vs several hours).

Locations are derived from the actual station coordinates in the project data,
snapped to the nearest ERA5 0.25° grid point:

  Folder / file               Lat      Lon    Stations covered
  ─────────────────────────────────────────────────────────────────────────────
  grid_m4.25_29.50          -4.25    29.50    NYANZA LAC (IRAT), NYENGWE (RIMBO)
  grid_m4.00_29.50          -4.00    29.50    BASSE-MULEMBWE, BUZIMBA, DAMA, MULEMBWE
  grid_m4.00_29.75          -4.00    29.75    JIJI (NDAGO)
  grid_m3.75_29.50          -3.75    29.50    MPOTA (TORA)
  grid_m3.25_29.25          -3.25    29.25    BUJUMBURA (AEROPORT), IMBO, MUTIMBUZI, RUSIZI
  grid_m3.00_29.25          -3.00    29.25    KABURANTWA (MISSION), NYAMAGANA (MURAMBI)
  grid_m3.00_29.50          -3.00    29.50    RWEGURA, MPANDA (GATURA)
  grid_m2.75_29.00          -2.75    29.00    MPARAMBO, NYAKAGUNDA (MUSENYI)

Variables:
  - 2m_temperature              (matches station temperature files)
  - total_precipitation          (matches station precipitation files)
  - 10m_u_component_of_wind      (wind-driven evaporation / mixing)
  - 10m_v_component_of_wind
  - evaporation                  (lake water-balance)
  - surface_runoff               (river runoff proxy)
  - potential_evapotranspiration (water-balance driver)

Output: raw/<location>/era5_<location>_1940_<current_year>.nc

Setup
-----
1.  Register at https://cds.climate.copernicus.eu/ and accept the ERA5 licence.
2.  pip install cdsapi
3.  Create ~/.cdsapirc:
        url: https://cds.climate.copernicus.eu/api
        key: <your-personal-access-token>
4.  Run:
        python era5_download/download_era5.py
"""

from __future__ import annotations

import argparse
import datetime
import logging
import sys
import time
import zipfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATASET = "reanalysis-era5-single-levels-timeseries"

LOCATIONS: dict[str, dict] = {
    # lat=-4.25, lon=29.50 → NYANZA LAC (IRAT), NYENGWE (RIMBO)
    "grid_m4.25_29.50": {"latitude": -4.25, "longitude": 29.50},
    # lat=-4.00, lon=29.50 → BASSE-MULEMBWE, BUZIMBA, DAMA, MULEMBWE
    "grid_m4.00_29.50": {"latitude": -4.00, "longitude": 29.50},
    # lat=-4.00, lon=29.75 → JIJI (NDAGO)
    "grid_m4.00_29.75": {"latitude": -4.00, "longitude": 29.75},
    # lat=-3.75, lon=29.50 → MPOTA (TORA)
    "grid_m3.75_29.50": {"latitude": -3.75, "longitude": 29.50},
    # lat=-3.25, lon=29.25 → BUJUMBURA (AEROPORT), IMBO (SEMS), MUTIMBUZI, RUSIZI
    "grid_m3.25_29.25": {"latitude": -3.25, "longitude": 29.25},
    # lat=-3.00, lon=29.25 → KABURANTWA (MISSION), NYAMAGANA (MURAMBI)
    "grid_m3.00_29.25": {"latitude": -3.00, "longitude": 29.25},
    # lat=-3.00, lon=29.50 → RWEGURA, MPANDA (GATURA)
    "grid_m3.00_29.50": {"latitude": -3.00, "longitude": 29.50},
    # lat=-2.75, lon=29.00 → MPARAMBO, NYAKAGUNDA (MUSENYI)
    "grid_m2.75_29.00": {"latitude": -2.75, "longitude": 29.00},
}

VARIABLES = [
    "2m_temperature",
    "total_precipitation",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "evaporation",
    "surface_runoff",
    "potential_evapotranspiration",
]

FIRST_YEAR = 1940
RAW_DIR    = Path(__file__).resolve().parent.parent.parent.parent / "data" / "era5" / "raw"
REQUEST_PAUSE = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_nc_from_zip(zip_path: Path, out_nc: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        nc_names = [n for n in zf.namelist() if n.endswith(".nc")]
        if not nc_names:
            raise RuntimeError(f"No .nc file found inside {zip_path.name}")
        zf.extract(nc_names[0], path=out_nc.parent)
        extracted = out_nc.parent / nc_names[0]
        if extracted != out_nc:
            extracted.rename(out_nc)


def download_location(
    client,
    loc_name: str,
    location: dict,
    end_year: int,
    loc_dir: Path,
    overwrite: bool = False,
) -> Path:
    out_nc  = loc_dir / f"era5_{loc_name}_{FIRST_YEAR}_{end_year}.nc"
    tmp_zip = loc_dir / f"era5_{loc_name}_{FIRST_YEAR}_{end_year}.zip"

    if out_nc.exists() and not overwrite:
        log.info("  Already exists, skipping: %s", out_nc.name)
        return out_nc

    log.info("  Requesting %s (%d–%d) …", loc_name, FIRST_YEAR, end_year)
    request = {
        "variable":    VARIABLES,
        "date":        f"{FIRST_YEAR}-01-01/{end_year}-12-31",
        "location":    location,
        "data_format": "netcdf",
    }

    try:
        client.retrieve(DATASET, request, str(tmp_zip))
    except Exception as exc:
        log.error("  CDS request failed (%s): %s", loc_name, exc)
        raise

    try:
        _extract_nc_from_zip(tmp_zip, out_nc)
        tmp_zip.unlink()
        log.info("  Saved: %s  (%.1f MB)", out_nc.name, out_nc.stat().st_size / 1e6)
    except Exception as exc:
        log.error("  Extraction failed (%s): %s", loc_name, exc)
        raise

    return out_nc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(end_year: int, overwrite: bool) -> None:
    try:
        import cdsapi
    except ImportError:
        log.error("cdsapi not installed. Run:  pip install cdsapi")
        sys.exit(1)

    client = cdsapi.Client()
    log.info("Downloading %d location(s), %d–%d …", len(LOCATIONS), FIRST_YEAR, end_year)

    failed = []
    for i, (loc_name, location) in enumerate(LOCATIONS.items(), start=1):
        loc_dir = RAW_DIR / loc_name
        loc_dir.mkdir(parents=True, exist_ok=True)
        log.info("[%d/%d] %s", i, len(LOCATIONS), loc_name)
        try:
            download_location(client, loc_name, location, end_year, loc_dir, overwrite)
        except Exception:
            failed.append(loc_name)
        if i < len(LOCATIONS):
            time.sleep(REQUEST_PAUSE)

    if failed:
        log.warning("Failed (re-run to retry): %s", failed)
    else:
        log.info("All downloads complete.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download ERA5 hourly timeseries for Lake Tanganyika stations."
    )
    parser.add_argument(
        "--end-year", type=int, default=datetime.date.today().year,
        help="Last year to include (default: current year)",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Re-download files that already exist.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(args.end_year, args.overwrite)
