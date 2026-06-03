#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.catalog import build_data_catalog, render_catalog_markdown
from src.utils import resolve_path, resolve_project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build data catalog for Lake Tanganyika project.")
    parser.add_argument("--root", type=str, default="", help="Project root path (optional).")
    parser.add_argument("--out_reports", type=str, default="reports", help="Output reports directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(args.root, __file__)
    root = project_root
    scan_root = root / "Lake Tanganyika Data" if (root / "Lake Tanganyika Data").exists() else root
    out_reports = resolve_path(args.out_reports, project_root).resolve()
    out_reports.mkdir(parents=True, exist_ok=True)

    catalog = build_data_catalog(scan_root)
    csv_path = out_reports / "data_catalog.csv"
    md_path = out_reports / "data_catalog.md"

    catalog.to_csv(csv_path, index=False)
    md_text = render_catalog_markdown(catalog)
    md_path.write_text(md_text, encoding="utf-8")

    usable = catalog[catalog["machine_readable"] == True]
    water_like = usable[
        usable["path"].str.contains("niveaux|haut|niveau|water|riviere", case=False, regex=True)
        | usable["columns_or_bands"].str.contains("haut|level|water|niveau", case=False, regex=True, na=False)
    ]
    meteo_like = usable[
        usable["path"].str.contains("temp|precip|rain|pluie|meteo", case=False, regex=True)
        | usable["columns_or_bands"].str.contains("temp|precip|rain|pluie", case=False, regex=True, na=False)
    ]
    meteo_like = meteo_like[~meteo_like["path"].isin(water_like["path"])]

    print(f"Scan root: {scan_root}")
    print(f"Catalog written: {csv_path}")
    print(f"Markdown written: {md_path}")
    print("\nShort summary:")
    print(f"- Total files scanned: {len(catalog)}")
    print(f"- Machine-readable files: {len(usable)}")
    print(f"- Candidate water-level sources: {len(water_like)}")
    print(f"- Candidate meteo sources: {len(meteo_like)}")

    if not water_like.empty:
        print("\nWater-level candidate paths:")
        for p in water_like["path"].head(20).tolist():
            print(f"  - {p}")

    if not meteo_like.empty:
        print("\nMeteo candidate paths:")
        for p in meteo_like["path"].head(20).tolist():
            print(f"  - {p}")


if __name__ == "__main__":
    main()
