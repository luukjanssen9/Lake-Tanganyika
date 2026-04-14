"""
Download JRC Global Surface Water monthly water history for the Lake Tanganyika
river catchment locations via Google Earth Engine.

Dataset: JRC/GSW1_4/MonthlyHistory  (Landsat, 30m, 1984–present)
Band:    waterClassification
         0 = no data, 1 = not water, 2 = water

For each river location the script extracts the fraction of water-covered pixels
within a 5 km radius buffer and saves monthly time series.

Uses server-side GEE mapping (no per-month Python loop) for speed —
all months are computed in a single GEE call per river (~15–45 min total).

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
       python scripts/download/download_jrc_surface_water.py
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

START_DATE = "1984-01-01"
END_DATE   = "2026-01-01"

RIVER_LOCATIONS: dict[str, tuple[float, float]] = {
    "Nyengwe":    (-4.17, 29.54),   # Nyengwe (Rimbo) gauge
    "Buzimba":    (-4.05, 29.48),   # Buzimba (Gatete) gauge
    "Mulembwe":   (-4.00, 29.44),   # Mulembwe (Mutambara) gauge
    "Jiji":       (-3.92, 29.64),   # Jiji (Ndago) gauge
    "Mpanda":     (-3.12, 29.40),   # Mpanda (Gatura) gauge
    "Mutimbuzi":  (-3.32, 29.33),   # Mutimbuzi (Pont Aéroport) gauge
    "Rusizi":     (-3.34, 29.27),   # Rusizi (Gatumba) gauge
    "Kaburantwa": (-2.99, 29.22),   # Kaburantwa (Mission) gauge
    "Nyamagana":  (-2.90, 29.13),   # Nyamagana (Murambi) gauge
    "Nyakagunda": (-2.76, 29.08),   # Nyakagunda (Musenyi) gauge
}

BUFFER_RADIUS_M = 2000

OUTPUT_DIR    = Path(__file__).resolve().parent.parent.parent / "data" / "outputs"
PER_RIVER_DIR = OUTPUT_DIR / "per_river"
COMBINED_PATH = OUTPUT_DIR / "jrc_surface_water_monthly.csv"


# ---------------------------------------------------------------------------
# GEE — server-side computation
# ---------------------------------------------------------------------------

def extract_water_fraction(ee, lat: float, lon: float) -> list[dict]:
    """
    Compute monthly water fraction for a buffered point entirely server-side.
    Returns a list of {year, month, water_fraction, water_pixels, total_pixels}.
    """
    point  = ee.Geometry.Point([lon, lat])
    region = point.buffer(BUFFER_RADIUS_M)

    # Build a sequence of month-start dates
    start    = ee.Date(START_DATE)
    end      = ee.Date(END_DATE)
    n_months = end.difference(start, "month").int()
    offsets  = ee.List.sequence(0, n_months.subtract(1))

    collection = ee.ImageCollection("JRC/GSW1_4/MonthlyHistory")

    def compute_month(offset):
        month_start = start.advance(offset, "month")
        month_end   = month_start.advance(1, "month")

        monthly_col = collection.filterDate(month_start, month_end)

        # If no images exist for this month, use a zero image to avoid band errors
        img = ee.Image(ee.Algorithms.If(
            monthly_col.size().gt(0),
            monthly_col.mosaic(),
            ee.Image.constant(0).rename("waterClassification"),
        ))

        water = img.eq(2).rename("water")
        valid = img.gte(1).rename("valid")

        stats = water.addBands(valid).reduceRegion(
            reducer  = ee.Reducer.sum(),
            geometry = region,
            scale    = 30,
            maxPixels= 1e7,
        )

        water_px = stats.get("water")
        valid_px = stats.get("valid")

        return ee.Feature(None, {
            "year":        month_start.get("year"),
            "month":       month_start.get("month"),
            "water_pixels": water_px,
            "total_pixels": valid_px,
        })

    features = ee.FeatureCollection(offsets.map(compute_month))
    raw = features.getInfo()["features"]

    rows = []
    for f in raw:
        p = f["properties"]
        water_px = p.get("water_pixels")
        total_px = p.get("total_pixels")
        if water_px is not None and total_px and total_px > 0:
            fraction = round(water_px / total_px, 6)
        else:
            fraction = None
        rows.append({
            "year":           int(p["year"]),
            "month":          int(p["month"]),
            "water_fraction": fraction,
            "water_pixels":   int(water_px) if water_px is not None else None,
            "total_pixels":   int(total_px) if total_px is not None else None,
        })

    rows.sort(key=lambda r: (r["year"], r["month"]))
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
        ee.Initialize(project="first-apex-493315-s2")
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
        log.info("[%d/%d] %s  (%.2f, %.2f) — computing server-side …",
                 i, len(RIVER_LOCATIONS), river, lat, lon)
        try:
            rows = extract_water_fraction(ee, lat, lon)
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
