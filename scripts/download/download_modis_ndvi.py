"""
Download MODIS NDVI (MOD13A1 v061) for the Lake Tanganyika river catchments.

For each river, the nearest ERA5 grid point is used as the sample location,
consistent with the rest of the project. NDVI is extracted from the 500m
16-day composite and aggregated to monthly means.

Dataset: MODIS/061/MOD13A1  (Terra, 500 m, 16-day)
Band:    NDVI  (scale factor 0.0001 → values in [-1, 1])

Output:
    outputs/ndvi_monthly.csv          — all rivers combined (long format)
    outputs/per_river/<river>_ndvi_monthly.csv  — one file per river

Setup
-----
1. Sign up at https://earthengine.google.com/ (free for research)
2. pip install earthengine-api
3. Authenticate once:
       python -c "import ee; ee.Authenticate()"
4. Run:
       python scripts/download_modis_ndvi.py
"""

from __future__ import annotations

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
# Configuration — grid points match ERA5 locations in download_era5.py
# ---------------------------------------------------------------------------

START_DATE = "2000-01-01"   # MOD13A1 begins Feb 2000
END_DATE   = "2026-01-01"

# River → (latitude, longitude)  — nearest ERA5 0.25° grid point
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

OUTPUT_DIR     = Path(__file__).resolve().parent.parent.parent / "data" / "outputs"
PER_RIVER_DIR  = OUTPUT_DIR / "per_river"
COMBINED_PATH  = OUTPUT_DIR / "ndvi_monthly.csv"

NDVI_SCALE = 0.0001   # MOD13A1 raw integer → float NDVI


# ---------------------------------------------------------------------------
# GEE helpers
# ---------------------------------------------------------------------------

def _build_monthly_ndvi(ee, river: str, lat: float, lon: float):
    """Return a list of (year, month, ndvi) tuples for one river location."""
    import ee  # noqa: F811 — already imported, just for type clarity

    point      = ee.Geometry.Point([lon, lat])
    collection = (
        ee.ImageCollection("MODIS/061/MOD13A1")
        .filterDate(START_DATE, END_DATE)
        .select("NDVI")
    )

    # Generate a list of year-month start dates covering the full range
    start  = ee.Date(START_DATE)
    end    = ee.Date(END_DATE)
    n_months = end.difference(start, "month").int()
    months = ee.List.sequence(0, n_months.subtract(1))

    def monthly_mean(offset):
        month_start = start.advance(offset, "month")
        month_end   = month_start.advance(1, "month")
        mean_img    = (
            collection
            .filterDate(month_start, month_end)
            .mean()
        )
        value = mean_img.reduceRegion(
            reducer  = ee.Reducer.mean(),
            geometry = point,
            scale    = 500,
        ).get("NDVI")

        return ee.Feature(None, {
            "year":  month_start.get("year"),
            "month": month_start.get("month"),
            "ndvi":  value,
        })

    features = ee.FeatureCollection(months.map(monthly_mean))
    return features.getInfo()["features"]


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

    all_rows: list[dict] = []

    for i, (river, (lat, lon)) in enumerate(RIVER_LOCATIONS.items(), start=1):
        log.info("[%d/%d] %s  (%.2f, %.2f)", i, len(RIVER_LOCATIONS), river, lat, lon)

        try:
            features = _build_monthly_ndvi(ee, river, lat, lon)
        except Exception as exc:
            log.error("  Failed: %s", exc)
            continue

        rows = []
        for f in features:
            props = f["properties"]
            ndvi_raw = props.get("ndvi")
            ndvi = round(ndvi_raw * NDVI_SCALE, 6) if ndvi_raw is not None else None
            rows.append({
                "river": river,
                "year":  int(props["year"]),
                "month": int(props["month"]),
                "ndvi":  ndvi,
            })

        rows.sort(key=lambda r: (r["year"], r["month"]))

        # Per-river file
        import csv
        river_path = PER_RIVER_DIR / f"{river.lower()}_ndvi_monthly.csv"
        with open(river_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["river", "year", "month", "ndvi"])
            writer.writeheader()
            writer.writerows(rows)
        log.info("  Saved %d rows → %s", len(rows), river_path.name)

        all_rows.extend(rows)

    # Combined file
    all_rows.sort(key=lambda r: (r["river"], r["year"], r["month"]))
    import csv
    with open(COMBINED_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["river", "year", "month", "ndvi"])
        writer.writeheader()
        writer.writerows(all_rows)
    log.info("Combined NDVI saved → %s", COMBINED_PATH)


if __name__ == "__main__":
    run()
