"""
Quick inspection helper for downloaded ERA5 NetCDF files.

Usage:
    python inspect_era5.py                  # summarise all files in ./raw/
    python inspect_era5.py raw/era5_*.nc   # pass specific files
"""

from __future__ import annotations

import sys
from pathlib import Path

import xarray as xr


RAW_DIR = Path(__file__).parent / "raw"


def summarise(path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"File : {path.name}  ({path.stat().st_size / 1e6:.1f} MB)")
    ds = xr.open_dataset(path)
    t = ds["valid_time"] if "valid_time" in ds.coords else ds["time"]
    print(f"Time : {t.values[0]}  →  {t.values[-1]}  ({len(t)} steps)")
    lat = float(ds.latitude) if ds.latitude.ndim == 0 else float(ds.latitude.min())
    lon = float(ds.longitude) if ds.longitude.ndim == 0 else float(ds.longitude.min())
    print(f"Lat  : {lat:.2f}")
    print(f"Lon  : {lon:.2f}")
    print("Vars :")
    for var in ds.data_vars:
        v = ds[var]
        print(f"  {var:40s}  units={v.attrs.get('units','?'):10s}  shape={v.shape}")
    ds.close()


def main() -> None:
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        paths = sorted(RAW_DIR.rglob("era5_*_1940_*.nc"))

    if not paths:
        print(f"No NetCDF files found in {RAW_DIR}")
        return

    for p in paths:
        try:
            summarise(p)
        except Exception as exc:
            print(f"  ERROR reading {p.name}: {exc}")


if __name__ == "__main__":
    main()
