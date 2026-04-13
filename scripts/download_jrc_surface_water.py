"""
Download JRC Global Surface Water monthly water history for the Lake Tanganyika
river catchment locations via Google Earth Engine.

Dataset: JRC/GSW1_4/MonthlyHistory  (Landsat, 30m, 1984–present)
Band:    waterClassification
         0 = no data, 1 = not water, 2 = water

For each river location the script extracts the fraction of water-covered pixels
within a 5 km radius buffer and saves monthly time series.

Source: https://global-surface-water.appspot.com/
Paper:  Pekel et al. (2016) Nature 540, 418–422

Output:
    outputs/jrc_surface_water_monthly.csv          — all rivers combined
    outputs/per_river/<river>_jrc_water_monthly.csv

Setup
-----
1. Sign up at https://earthengine.google.com/ (free for research)
2. pip install earthengine-api
3. Authenticate once:
       python -c "import ee; ee.Authenticate()"
4. Run:
       python scripts/download_jrc_surface_water.py
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — same grid points as ERA5 and NDVI scripts
# ---------------------------------------------------------------------------

START_YEAR = 1984
END_YEAR   = 2025

# River → (latitude, longitude)
RIVER_LOCATIONS: dict[str, tuple[float, float]] = {
    "Nyengwe":    (-4.25, 29.50),
    "Buzimba":    (-4.00, 29.50),
    "Mulembwe":   (-4.00, 29.50),
    "Jiji":       (-4.00, 29.75),
    "Mpanda":     (-3.00, 29.50),
    "Mutimbuzi":  (-3.25, 29.25),
    "Rusizi":     (-3.25, 29.25),
    "Kaburantwa": (-3.00, 29.25),
    "Nyamagana":  (-3.00, 29.25),
    "Nyakagunda": (-2.75, 29.00),
}

BUFFER_RADIUS_M = 5000   # 5 km radius around each point

OUTPUT_DIR     = Path(__file__).resolve().parent.parent / "outputs"
PER_RIVER_DIR  = OUTPUT_DIR / "per_river"
COMBINED_PATH  = OUTPUT_DIR / "jrc_surface_water_monthly.csv"


# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def _extract_water_fraction(ee, lat: float, lon: float) -> list[dict]:
    """Return monthly water fraction records for a buffered point."""
    point  = ee.Geometry.Point([lon, lat])
    region = point.buffer(BUFFER_RADIUS_M)

    collection = ee.ImageCollection("JRC/GSW1_4/MonthlyHistory")

    rows = []
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            date_str = f"{year}-{month:02d}-01"
            img = collection.filterDate(date_str, f"{year}-{month:02d}-28").first()

            # Water pixels = class 2; total valid pixels = class 1 or 2
            water  = img.eq(2)
            valid  = img.gte(1)

            stats = water.reduceRegion(
                reducer  = ee.Reducer.sum().combine(ee.Reducer.count(), sharedInputs=True),
                geometry = region,
                scale    = 30,
                maxPixels= 1e7,
            ).getInfo()

            water_px = stats.get("waterClassification_sum", None)
            total_px = stats.get("waterClassification_count", None)

            fraction = (water_px / total_px) if (water_px is not None and total_px and total_px > 0) else None

            rows.append({
                "year":           year,
                "month":          month,
                "water_fraction": round(fraction, 6) if fraction is not None else None,
                "water_pixels":   int(water_px) if water_px is not None else None,
                "total_pixels":   int(total_px) if total_px is not None else None,
            })

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    try:
        import ee
    except ImportError:
        log.error("earthengine-api not installed. Run:  pip install earthengine-api")
        sys.exit(1)

    try:
        ee.Initialize()
    except Exception:
        log.error(
            "GEE authentication required. Run once:\n"
            "    python -c \"import ee; ee.Authenticate()\""
        )
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PER_RIVER_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = ["river", "year", "month", "water_fraction", "water_pixels", "total_pixels"]
    all_rows: list[dict] = []

    for i, (river, (lat, lon)) in enumerate(RIVER_LOCATIONS.items(), start=1):
        log.info("[%d/%d] %s  (%.2f, %.2f)", i, len(RIVER_LOCATIONS), river, lat, lon)

        try:
            rows = _extract_water_fraction(ee, lat, lon)
        except Exception as exc:
            log.error("  Failed: %s", exc)
            continue

        for r in rows:
            r["river"] = river

        river_path = PER_RIVER_DIR / f"{river.lower()}_jrc_water_monthly.csv"
        with open(river_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        log.info("  Saved %d rows → %s", len(rows), river_path.name)

        all_rows.extend(rows)

    all_rows.sort(key=lambda r: (r["river"], r["year"], r["month"]))
    with open(COMBINED_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    log.info("Combined surface water saved → %s", COMBINED_PATH)


if __name__ == "__main__":
    run()
