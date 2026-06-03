#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.modeling import CVConfig, evaluate_models, render_model_report
from src.utils import resolve_path, resolve_project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate forecasting models.")
    parser.add_argument("--root", type=str, default="", help="Project root path (optional).")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Config YAML path.")
    parser.add_argument("--processed", type=str, default="data/processed/main_modeling_table.parquet", help="Processed modeling table path.")
    parser.add_argument("--out_reports", type=str, default="reports", help="Report output directory.")
    parser.add_argument("--out_preds", type=str, default="data/predictions", help="Prediction output directory.")
    parser.add_argument("--out_models", type=str, default="data/models", help="Model artifacts output directory.")
    return parser.parse_args()


def _load_processed(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, parse_dates=["date"])


def _resolve_processed(path_arg: str, project_root: Path) -> Path:
    requested = resolve_path(path_arg, project_root).resolve()
    if requested.exists():
        return requested
    fallback_csv = requested.with_suffix(".csv")
    if fallback_csv.exists():
        return fallback_csv
    raise FileNotFoundError(f"Processed table not found: {requested}")


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(args.root, __file__)
    config_path = resolve_path(args.config, project_root).resolve()
    processed_path = _resolve_processed(args.processed, project_root)
    out_reports = resolve_path(args.out_reports, project_root).resolve()
    out_preds = resolve_path(args.out_preds, project_root).resolve()
    out_models = resolve_path(args.out_models, project_root).resolve()
    out_reports.mkdir(parents=True, exist_ok=True)
    out_preds.mkdir(parents=True, exist_ok=True)
    out_models.mkdir(parents=True, exist_ok=True)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    table = _load_processed(processed_path)
    table["date"] = pd.to_datetime(table["date"], errors="coerce")

    modeling_cfg = cfg.get("modeling", {})
    horizons = modeling_cfg.get("horizons_months", [1, 2, 3])
    cv = CVConfig(
        n_splits=int(modeling_cfg.get("n_splits", 5)),
        min_train_size=int(modeling_cfg.get("min_train_size", 60)),
    )

    results = evaluate_models(
        modeling_table=table,
        horizons=horizons,
        cv_config=cv,
        sarimax_order=tuple(modeling_cfg.get("sarimax_order", [1, 0, 1])),
        sarimax_seasonal_order=tuple(modeling_cfg.get("sarimax_seasonal_order", [1, 0, 1, 12])),
        rf_params={
            "n_estimators": modeling_cfg.get("rf_n_estimators", 400),
            "max_depth": modeling_cfg.get("rf_max_depth", 10),
            "min_samples_leaf": modeling_cfg.get("rf_min_samples_leaf", 2),
        },
        random_seed=int(cfg.get("pipeline", {}).get("random_seed", 42)),
    )

    # Save outputs.
    metrics_by_fold = results.get("metrics_by_fold", pd.DataFrame())
    metrics_summary = results.get("metrics_summary", pd.DataFrame())
    event_by_fold = results.get("event_metrics_by_fold", pd.DataFrame())
    event_summary = results.get("event_metrics_summary", pd.DataFrame())
    forecasts = results.get("forecasts", pd.DataFrame())
    cv_preds = results.get("cv_predictions", pd.DataFrame())

    metrics_by_fold.to_csv(out_reports / "cv_metrics_by_fold.csv", index=False)
    metrics_summary.to_csv(out_reports / "cv_metrics_summary.csv", index=False)
    event_by_fold.to_csv(out_reports / "event_metrics_by_fold.csv", index=False)
    event_summary.to_csv(out_reports / "event_metrics_summary.csv", index=False)
    cv_preds.to_csv(out_preds / "cv_predictions.csv", index=False)
    forecasts.to_csv(out_preds / "horizon_forecasts.csv", index=False)

    # Per-horizon prediction files.
    if not forecasts.empty:
        for h in sorted(forecasts["horizon_months"].unique()):
            sub = forecasts[forecasts["horizon_months"] == h]
            sub.to_csv(out_preds / f"forecast_h{int(h)}.csv", index=False)

    metadata = {
        "target_station": table["target_station"].dropna().iloc[0] if "target_station" in table.columns and table["target_station"].notna().any() else "unknown",
        "date_min": str(pd.to_datetime(table["date"]).min().date()) if not table.empty else "n/a",
        "date_max": str(pd.to_datetime(table["date"]).max().date()) if not table.empty else "n/a",
        "n_rows": int(len(table)),
    }

    model_report = render_model_report(results, metadata)
    model_report_path = out_reports / "model_report.md"
    model_report_path.write_text(model_report, encoding="utf-8")

    artifact_meta = {
        "config": cfg,
        "metadata": metadata,
        "horizons": horizons,
        "outputs": {
            "metrics_summary": str(out_reports / "cv_metrics_summary.csv"),
            "event_summary": str(out_reports / "event_metrics_summary.csv"),
            "forecasts": str(out_preds / "horizon_forecasts.csv"),
        },
    }
    with open(out_models / "modeling_artifacts.json", "w", encoding="utf-8") as f:
        json.dump(artifact_meta, f, indent=2)

    print(f"Model report written: {model_report_path}")
    print(f"Forecasts written: {out_preds / 'horizon_forecasts.csv'}")


if __name__ == "__main__":
    main()
