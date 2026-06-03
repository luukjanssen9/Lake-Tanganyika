"""
Extended metrics for all forecasting models:

    MAE              : mean absolute error (meters)
    RMSE             : root mean squared error (meters)
    bias             : mean of (y_true - y_pred), in meters
    NRMSE_range      : RMSE / (max(y) - min(y))   — error as a fraction of
                       the lake's historical dynamic range
    NRMSE_std        : RMSE / std(y)              — error in units of
                       typical month-to-month variability
    skill_vs_pers    : 1 - MSE_model / MSE_persistence    on aligned dates
    skill_vs_seas    : 1 - MSE_model / MSE_seasonal_naive on aligned dates

Skill scores are evaluated on the intersection of dates each model has in
common with the reference baseline (so the comparison is on identical dates).

Outputs:
    reports/metrics_extended.csv
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_CSV  = REPO_ROOT / "data" / "processed" / "lake_tanganyika_modeling_table.csv"

PREDICTION_FILES = {
    "persistence":    REPO_ROOT / "reports" / "baseline_predictions.csv",
    "seasonal_naive": REPO_ROOT / "reports" / "baseline_predictions.csv",
    "sarimax":        REPO_ROOT / "reports" / "sarimax_predictions.csv",
    "xgboost":        REPO_ROOT / "reports" / "xgboost_predictions.csv",
    "xgboost_diff":   REPO_ROOT / "reports" / "xgboost_diff_predictions.csv",
}
OUT_CSV = REPO_ROOT / "reports" / "metrics_extended.csv"


def load_predictions() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    seen_files: set[Path] = set()
    for model, path in PREDICTION_FILES.items():
        if path in seen_files:
            continue
        seen_files.add(path)
        df = pd.read_csv(path, parse_dates=["date"])
        frames.append(df[["date", "horizon_months", "model", "y_true", "y_pred"]])
    return pd.concat(frames, ignore_index=True)


def lake_scale(stats_period: str = "test") -> tuple[float, float]:
    df = pd.read_csv(DATA_CSV, parse_dates=["date"])
    series = df["lake_level_m"].dropna()
    if stats_period == "test":
        cutoff = df["date"].max() - pd.DateOffset(years=5)
        series = df.loc[df["date"] >= cutoff, "lake_level_m"].dropna()
    return float(series.max() - series.min()), float(series.std())


def base_metrics(preds: pd.DataFrame, lake_range: float, lake_std: float) -> pd.DataFrame:
    rows: list[dict] = []
    for (model, h), g in preds.groupby(["model", "horizon_months"]):
        err = g["y_true"] - g["y_pred"]
        rmse = float(np.sqrt((err ** 2).mean()))
        rows.append({
            "model":          model,
            "horizon_months": int(h),
            "n":              int(len(g)),
            "mae_m":          float(err.abs().mean()),
            "rmse_m":         rmse,
            "bias_m":         float(err.mean()),
            "nrmse_range":    rmse / lake_range,
            "nrmse_std":      rmse / lake_std,
        })
    return pd.DataFrame(rows)


def skill_scores(preds: pd.DataFrame) -> pd.DataFrame:
    pers = preds[preds["model"] == "persistence"][["date", "horizon_months", "y_true", "y_pred"]]
    seas = preds[preds["model"] == "seasonal_naive"][["date", "horizon_months", "y_true", "y_pred"]]
    pers = pers.rename(columns={"y_pred": "y_pred_pers"})
    seas = seas.rename(columns={"y_pred": "y_pred_seas"})

    rows: list[dict] = []
    for (model, h), g in preds.groupby(["model", "horizon_months"]):
        merged = g.merge(pers[["date", "horizon_months", "y_pred_pers"]],
                         on=["date", "horizon_months"], how="inner")
        merged = merged.merge(seas[["date", "horizon_months", "y_pred_seas"]],
                              on=["date", "horizon_months"], how="inner")
        if merged.empty:
            continue
        mse_model = ((merged["y_true"] - merged["y_pred"]) ** 2).mean()
        mse_pers  = ((merged["y_true"] - merged["y_pred_pers"]) ** 2).mean()
        mse_seas  = ((merged["y_true"] - merged["y_pred_seas"]) ** 2).mean()
        rows.append({
            "model":             model,
            "horizon_months":    int(h),
            "n_aligned":         int(len(merged)),
            "skill_vs_pers":     float(1 - mse_model / mse_pers) if mse_pers > 0 else np.nan,
            "skill_vs_seasonal": float(1 - mse_model / mse_seas) if mse_seas > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def main() -> None:
    log.info("Loading predictions for %d model variants", len(set(PREDICTION_FILES.values())))
    preds = load_predictions()

    # Restrict every model to the same recent 5y test window for an apples-to-apples comparison.
    test_cutoff = preds["date"].max() - pd.DateOffset(years=5)
    preds = preds[preds["date"] >= test_cutoff].reset_index(drop=True)
    log.info("Restricted to test window: %s -> %s",
             preds["date"].min().date(), preds["date"].max().date())

    lake_range, lake_std = lake_scale(stats_period="test")
    log.info("Lake-level scale (recent 5y test period): range=%.3f m, std=%.3f m",
             lake_range, lake_std)

    base = base_metrics(preds, lake_range, lake_std)
    skill = skill_scores(preds)
    metrics = base.merge(skill, on=["model", "horizon_months"], how="left")

    metrics = metrics.sort_values(["horizon_months", "model"]).reset_index(drop=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(OUT_CSV, index=False)
    log.info("Wrote %s", OUT_CSV.relative_to(REPO_ROOT))

    print()
    print("=== Extended metrics (recent 5y test period) ===")
    print()
    cols_show = ["model", "horizon_months", "n", "mae_m", "rmse_m", "bias_m",
                 "nrmse_range", "nrmse_std", "skill_vs_pers", "skill_vs_seasonal"]
    print(metrics[cols_show].round(3).to_string(index=False))
    print()
    print("Interpretation guide:")
    print("  nrmse_range   = RMSE / (max(y) - min(y)) over the test window")
    print("  nrmse_std     = RMSE / std(y)            over the test window")
    print("  skill_vs_*    = 1 - MSE_model / MSE_reference, on aligned dates")
    print("                  1.0 = perfect, 0.0 = no better than reference, <0 = worse")


if __name__ == "__main__":
    main()
