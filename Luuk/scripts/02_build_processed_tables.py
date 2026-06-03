#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.cleaning import missingness_matrix_summary, prepare_clean_datasets
from src.features import build_main_modeling_table
from src.loaders import load_all_sources
from src.utils import resolve_path, resolve_project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build processed modeling tables.")
    parser.add_argument("--root", type=str, default="", help="Project root path (optional).")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Config YAML path.")
    parser.add_argument("--out_processed", type=str, default="data/processed", help="Processed output directory.")
    parser.add_argument("--out_reports", type=str, default="reports", help="Report output directory.")
    return parser.parse_args()


def _resolve_data_root(project_root: Path, cfg: dict) -> Path:
    rel = cfg.get("paths", {}).get("root_data_dir", "Lake Tanganyika Data")
    candidate = project_root / rel
    return candidate if candidate.exists() else project_root


def render_quality_report(
    quality: dict,
    missing_summary: pd.DataFrame,
    main_table: pd.DataFrame,
    metadata: dict,
) -> str:
    lines: list[str] = []
    lines.append("# Data Quality Report")
    lines.append("")
    lines.append("## Missingness Matrix Summary")
    lines.append(missing_summary.to_markdown(index=False))
    lines.append("")

    lines.append("## Outlier Rules Used")
    lines.append("- Rule: IQR-based with bounds [Q1 - 3*IQR, Q3 + 3*IQR], applied per station.")
    lines.append("")

    lines.append("## Outlier Counts")
    outlier_counts = quality.get("outlier_counts", {})
    for k, v in outlier_counts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Unit Harmonization")
    for note in quality.get("unit_notes", []):
        lines.append(f"- {note}")
    lines.append("")

    lines.append("## Duplicate Timestamps")
    dup_counts = quality.get("duplicate_counts", {})
    for k, v in dup_counts.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Inconsistent Station Names")
    name_map = quality.get("station_name_map", pd.DataFrame())
    if isinstance(name_map, pd.DataFrame) and not name_map.empty:
        changed = name_map[name_map["original_name"] != name_map["canonical_name"]].head(100)
        if not changed.empty:
            lines.append(changed.to_markdown(index=False))
        else:
            lines.append("No station name normalization differences detected.")
    else:
        lines.append("No station name map available.")
    lines.append("")

    lines.append("## Suspicious Values Found")
    suspicious = quality.get("suspicious_values", {})
    for k, df in suspicious.items():
        if isinstance(df, pd.DataFrame) and not df.empty:
            lines.append(f"### {k}")
            lines.append(df.head(20).to_markdown(index=False))
            lines.append("")
        else:
            lines.append(f"- {k}: none")
    lines.append("")

    lines.append("## Target Selection")
    lines.append(f"- Primary target station selected: {quality.get('primary_target_station')}")
    target_scores = quality.get("target_scores", pd.DataFrame())
    if isinstance(target_scores, pd.DataFrame) and not target_scores.empty:
        lines.append(target_scores.head(15).to_markdown(index=False))
    lines.append("")

    lines.append("## Main Modeling Table")
    lines.append(f"- Rows: {metadata.get('n_rows', 0)}")
    lines.append(f"- Date range: {metadata.get('date_min')} to {metadata.get('date_max')}")
    lines.append(f"- Event threshold q95: {metadata.get('event_threshold_q95')}")
    lines.append(f"- Event threshold q98: {metadata.get('event_threshold_q98')}")
    lines.append("")

    lines.append("## Assumptions")
    lines.append("- Monthly frequency was selected because most sources are monthly.")
    lines.append("- Water-level units were assumed meters unless heuristic conversion was triggered.")
    lines.append("- If lake-level records are unavailable, best river-level proxy is used as target.")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(args.root, __file__)
    config_path = resolve_path(args.config, project_root).resolve()
    out_processed = resolve_path(args.out_processed, project_root).resolve()
    out_reports = resolve_path(args.out_reports, project_root).resolve()
    out_station = out_processed / "station_level"
    out_processed.mkdir(parents=True, exist_ok=True)
    out_reports.mkdir(parents=True, exist_ok=True)
    out_station.mkdir(parents=True, exist_ok=True)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_root = _resolve_data_root(project_root, cfg)
    missing_tokens = cfg.get("missing_tokens", ["", "-", "NA", "N/A", "nan"])

    sources = load_all_sources(data_root, missing_tokens=missing_tokens)
    cleaned, quality = prepare_clean_datasets(sources)

    fcfg = cfg.get("feature_windows", {})
    eq = cfg.get("event_thresholds", {})

    main_table, station_tables, metadata = build_main_modeling_table(
        cleaned,
        quality,
        frequency=cfg.get("pipeline", {}).get("frequency", "MS"),
        lags=fcfg.get("lags", [1, 2, 3, 6, 12]),
        windows=fcfg.get("rolling_windows", [3, 6, 12]),
        event_q95=eq.get("primary_quantile", 0.95),
        event_q98=eq.get("sensitivity_quantile", 0.98),
    )

    main_parquet = out_processed / "main_modeling_table.parquet"
    main_csv = out_processed / "main_modeling_table.csv"

    main_table.to_parquet(main_parquet, index=False)
    main_table.to_csv(main_csv, index=False)

    for existing_csv in out_station.glob("*.csv"):
        existing_csv.unlink()

    for station, table in station_tables.items():
        safe_name = station.replace(" ", "_").replace("/", "_")
        table.to_csv(out_station / f"{safe_name}.csv", index=False)

    missing_summary = missingness_matrix_summary(cleaned)

    quality_report = render_quality_report(quality, missing_summary, main_table, metadata)
    quality_path = out_reports / "data_quality_report.md"
    quality_path.write_text(quality_report, encoding="utf-8")

    # Persist useful tabular diagnostics.
    target_scores = quality.get("target_scores", pd.DataFrame())
    if isinstance(target_scores, pd.DataFrame) and not target_scores.empty:
        target_scores.to_csv(out_reports / "target_candidate_scores.csv", index=False)

    missing_summary.to_csv(out_reports / "missingness_matrix_summary.csv", index=False)

    print(f"Processed table written: {main_parquet}")
    print(f"Processed table written: {main_csv}")
    print(f"Station-level tables written to: {out_station}")
    print(f"Quality report written: {quality_path}")
    print(f"Primary target station: {quality.get('primary_target_station')}")


if __name__ == "__main__":
    main()
