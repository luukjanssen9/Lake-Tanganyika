"""
SARIMAX forecasts for Lake Tanganyika water level.

Order:   SARIMAX(1, 1, 1) x (1, 1, 1, 12)
    - non-seasonal: AR(1), one difference, MA(1)
    - seasonal at lag 12: AR(1), one difference, MA(1)
    - one difference (d=1) removes the 2020+ trend
    - one seasonal difference (D=1) removes the annual cycle

Exogenous regressors:
    - era5_tp_mm  (catchment-mean monthly precipitation)
    - era5_t2m_C  (catchment-mean monthly 2 m temperature)

Evaluation:
    Expanding-window rolling forecast over the last 5 years (matches the
    baseline 'recent_5y' period). For each training cutoff, refit on all
    history and forecast 1, 3, and 6 months ahead.

Note on exogenous values:
    Future precip/temp are taken as known (ERA5 reanalysis exists for the
    whole period). This is "perfect-foresight" for weather and so represents
    an upper bound; an operational forecast would need a seasonal weather
    forecast (NMME / SEAS5) as input.

Outputs:
    reports/sarimax_predictions.csv
    reports/sarimax_metrics.csv
    reports/model_comparison.csv      (sarimax vs baselines, side by side)
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

REPO_ROOT       = Path(__file__).resolve().parents[1]
DATA_CSV        = REPO_ROOT / "data" / "processed" / "lake_tanganyika_modeling_table.csv"
BASELINE_CSV    = REPO_ROOT / "reports" / "baseline_metrics.csv"
OUT_PREDS       = REPO_ROOT / "reports" / "sarimax_predictions.csv"
OUT_METRICS     = REPO_ROOT / "reports" / "sarimax_metrics.csv"
OUT_COMPARISON  = REPO_ROOT / "reports" / "model_comparison.csv"

HORIZONS        = [1, 3, 6]
TEST_YEARS      = 5
EXOG_COLS       = ["era5_tp_mm", "era5_t2m_C"]
ORDER           = (1, 1, 1)
SEASONAL_ORDER  = (1, 1, 1, 12)


def rolling_forecast(df: pd.DataFrame) -> pd.DataFrame:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    df = df.set_index("date").sort_index()
    y = df["lake_level_m"]
    X = df[EXOG_COLS]

    cutoff = df.index.max() - pd.DateOffset(years=TEST_YEARS)
    train_end_indices = df.index.get_indexer(df.index[df.index >= cutoff])
    n_total = len(df)
    log.info("Test period: %s -> %s (%d months)",
             df.index[train_end_indices[0]].date(),
             df.index[-1].date(),
             len(train_end_indices))
    log.info("Order: SARIMAX%s x %s   Exog: %s", ORDER, SEASONAL_ORDER, EXOG_COLS)

    records: list[dict] = []
    last_logged = 0
    for i, train_end in enumerate(train_end_indices):
        if train_end + max(HORIZONS) >= n_total:
            break

        y_train = y.iloc[: train_end + 1]
        X_train = X.iloc[: train_end + 1]

        model = SARIMAX(y_train, exog=X_train,
                        order=ORDER, seasonal_order=SEASONAL_ORDER,
                        enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit(disp=False, maxiter=200)

        max_h = max(HORIZONS)
        X_future = X.iloc[train_end + 1: train_end + 1 + max_h]
        fc = fit.get_forecast(steps=max_h, exog=X_future)
        forecast = fc.predicted_mean
        # 95% prediction interval (statsmodels returns lower/upper columns)
        conf = fc.conf_int(alpha=0.05)

        for h in HORIZONS:
            target_idx = train_end + h
            records.append({
                "date":           df.index[target_idx],
                "horizon_months": h,
                "model":          "sarimax",
                "y_true":         float(y.iloc[target_idx]),
                "y_pred":         float(forecast.iloc[h - 1]),
                "y_lower":        float(conf.iloc[h - 1, 0]),
                "y_upper":        float(conf.iloc[h - 1, 1]),
            })

        if i - last_logged >= 12 or i == len(train_end_indices) - 1:
            log.info("  ... fitted %d / %d training cutoffs", i + 1, len(train_end_indices))
            last_logged = i

    return pd.DataFrame(records)


def metrics_table(preds: pd.DataFrame, model_name: str) -> pd.DataFrame:
    rows: list[dict] = []
    for h, g in preds.groupby("horizon_months"):
        err = g["y_true"] - g["y_pred"]
        rows.append({
            "model":          model_name,
            "horizon_months": int(h),
            "period":         f"recent_{TEST_YEARS}y",
            "n":              int(len(g)),
            "mae_m":          float(err.abs().mean()),
            "rmse_m":         float(np.sqrt((err ** 2).mean())),
            "bias_m":         float(err.mean()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    log.info("Reading %s", DATA_CSV.name)
    df = pd.read_csv(DATA_CSV, parse_dates=["date"])
    df = df[["date", "lake_level_m"] + EXOG_COLS].dropna()
    log.info("Modeling data: %d months (%s -> %s)",
             len(df), df["date"].min().date(), df["date"].max().date())

    preds = rolling_forecast(df)
    metrics = metrics_table(preds, "sarimax")

    OUT_PREDS.parent.mkdir(parents=True, exist_ok=True)
    preds.to_csv(OUT_PREDS, index=False)
    metrics.to_csv(OUT_METRICS, index=False)
    log.info("Wrote %s", OUT_PREDS.relative_to(REPO_ROOT))
    log.info("Wrote %s", OUT_METRICS.relative_to(REPO_ROOT))

    baseline = pd.read_csv(BASELINE_CSV)
    recent_baseline = baseline[baseline["period"] == f"recent_{TEST_YEARS}y"].copy()
    comparison = pd.concat([recent_baseline, metrics], ignore_index=True)
    comparison = comparison.sort_values(["horizon_months", "model"]).reset_index(drop=True)
    comparison.to_csv(OUT_COMPARISON, index=False)

    print()
    print(f"=== Recent {TEST_YEARS}-year test period ===")
    print()
    print(comparison[["model", "horizon_months", "n", "mae_m", "rmse_m", "bias_m"]].to_string(index=False))
    print()

    pivot = comparison.pivot(index="horizon_months", columns="model", values="mae_m")
    pivot["sarimax_beats_persistence"] = pivot["sarimax"] < pivot["persistence"]
    pivot["sarimax_beats_seasonal"]    = pivot["sarimax"] < pivot["seasonal_naive"]
    print("MAE comparison (lower = better):")
    print()
    print(pivot.round(3).to_string())


if __name__ == "__main__":
    main()
