"""
Baseline forecasts for Lake Tanganyika water level.

Two parameter-free models — the floor that every later model must beat:

    persistence    :  L_hat[t+h] = L[t]
    seasonal_naive :  L_hat[t+h] = L[t+h-12]

Horizons: 1, 3, 6 months ahead.

Outputs:
    reports/baseline_predictions.csv  per-row: date, horizon, model, y_true, y_pred
    reports/baseline_metrics.csv      MAE / RMSE / bias per (model, horizon, period)

Usage:
    python scripts/06_baselines.py
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

REPO_ROOT   = Path(__file__).resolve().parents[1]
DATA_CSV    = REPO_ROOT / "data" / "processed" / "lake_tanganyika_modeling_table.csv"
OUT_METRICS = REPO_ROOT / "reports" / "baseline_metrics.csv"
OUT_PREDS   = REPO_ROOT / "reports" / "baseline_predictions.csv"

HORIZONS     = [1, 3, 6]
RECENT_YEARS = 5


def build_predictions(y: pd.Series) -> pd.DataFrame:
    """For each horizon h, build prediction series aligned by target date."""
    records: list[dict] = []
    for h in HORIZONS:
        # Persistence: prediction for target date t was made h months earlier using L[t-h].
        pers_pred = y.shift(h)
        # Seasonal naïve: prediction for target date t uses L[t-12] (made at t-h; t-12 ≤ t-h since h ≤ 12).
        seas_pred = y.shift(12)

        for model_name, pred in [("persistence", pers_pred), ("seasonal_naive", seas_pred)]:
            for date, y_true, y_pred in zip(y.index, y.values, pred.values):
                if pd.notna(y_true) and pd.notna(y_pred):
                    records.append({
                        "date": date,
                        "horizon_months": h,
                        "model": model_name,
                        "y_true": float(y_true),
                        "y_pred": float(y_pred),
                    })
    return pd.DataFrame(records)


def compute_metrics(preds: pd.DataFrame, recent_years: int) -> pd.DataFrame:
    cutoff = preds["date"].max() - pd.DateOffset(years=recent_years)
    rows: list[dict] = []
    for (model, h), g in preds.groupby(["model", "horizon_months"]):
        for period, mask in [
            ("overall",            pd.Series(True, index=g.index)),
            (f"recent_{recent_years}y", g["date"] >= cutoff),
        ]:
            sub = g[mask]
            if sub.empty:
                continue
            err = sub["y_true"] - sub["y_pred"]
            rows.append({
                "model": model,
                "horizon_months": h,
                "period": period,
                "n": int(len(sub)),
                "mae_m":  float(err.abs().mean()),
                "rmse_m": float(np.sqrt((err ** 2).mean())),
                "bias_m": float(err.mean()),
            })
    return pd.DataFrame(rows).sort_values(["period", "horizon_months", "model"]).reset_index(drop=True)


def main() -> None:
    log.info("Reading %s", DATA_CSV.name)
    df = pd.read_csv(DATA_CSV, parse_dates=["date"])
    y = df.set_index("date")["lake_level_m"].sort_index()
    log.info("Target series: %d months (%s -> %s)",
             y.notna().sum(), y.index.min().date(), y.index.max().date())

    preds = build_predictions(y)
    log.info("Built %d (date × horizon × model) prediction rows", len(preds))

    metrics = compute_metrics(preds, RECENT_YEARS)

    OUT_PREDS.parent.mkdir(parents=True, exist_ok=True)
    preds.to_csv(OUT_PREDS, index=False)
    metrics.to_csv(OUT_METRICS, index=False)
    log.info("Wrote %s", OUT_PREDS.relative_to(REPO_ROOT))
    log.info("Wrote %s", OUT_METRICS.relative_to(REPO_ROOT))

    print()
    print("Baseline metrics (lower MAE / RMSE is better; bias near 0 is better):")
    print()
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
