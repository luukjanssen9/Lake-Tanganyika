"""
XGBoost forecasts for Lake Tanganyika water level — trained on DIFFERENCES.

Why this script exists:
    The level-based XGBoost (scripts/forecasting/04_xgboost.py) loses to SARIMAX because
    tree models cannot extrapolate trends. During the 2020+ lake rise the
    test data sat above anything the model had seen in training, and trees
    "freeze" at the last training value → systematic underprediction
    (positive bias of 0.09–0.28 m, which accounted for 60–85% of total error).

The fix:
    Predict the CHANGE  dL = L[t+h] - L[t]  instead of the absolute level.
    Differences are roughly stationary (no monotonic trend), so trees can
    work within their training distribution. Then reconstruct the level
    forecast as  L_hat[t+h] = L[t] + dL_hat .

    `year` is also dropped from features — it's a pure trend term that
    forces extrapolation outside training range.

Training scheme:
    Identical expanding-window rolling forecast as scripts/forecasting/04_xgboost.py.
    Training set for cutoff `train_end` uses rows whose target is known by
    `train_end` (i.e., feature row index i must satisfy i + h <= train_end).

Outputs:
    reports/xgboost_diff_predictions.csv
    reports/xgboost_diff_metrics.csv
    reports/xgboost_diff_feature_importance.csv
    reports/model_comparison.csv  (baselines + SARIMAX + both XGBoost variants)
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

REPO_ROOT      = Path(__file__).resolve().parents[2]
DATA_CSV       = REPO_ROOT / "data" / "processed" / "lake_tanganyika_modeling_table.csv"
BASELINE_CSV   = REPO_ROOT / "reports" / "baseline_metrics.csv"
SARIMAX_CSV    = REPO_ROOT / "reports" / "sarimax_metrics.csv"
XGB_LEVEL_CSV  = REPO_ROOT / "reports" / "xgboost_metrics.csv"
OUT_PREDS      = REPO_ROOT / "reports" / "xgboost_diff_predictions.csv"
OUT_METRICS    = REPO_ROOT / "reports" / "xgboost_diff_metrics.csv"
OUT_FEAT_IMP   = REPO_ROOT / "reports" / "xgboost_diff_feature_importance.csv"
OUT_COMPARISON = REPO_ROOT / "reports" / "model_comparison.csv"

HORIZONS   = [1, 3, 6]
TEST_YEARS = 5

# Drop:
#   - climatology-based features (mild leakage, computed using full series)
#   - `year` (pure trend term — trees can't extrapolate it)
DROP_COLS = {
    "year",
    "era5_tp_anom",
    "era5_tp_anom_cumsum_3", "era5_tp_anom_cumsum_6",  "era5_tp_anom_cumsum_12",
    "era5_tp_anom_cumsum_24", "era5_tp_anom_cumsum_36",
    "lake_level_m_anom",
    "lake_level_m_zscore",
}

XGB_PARAMS = dict(
    n_estimators=500,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=2,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    verbosity=0,
)


def get_feature_cols(df: pd.DataFrame, target_col: str) -> list[str]:
    drop = {"date", target_col} | DROP_COLS
    return [c for c in df.columns if c not in drop]


def rolling_forecast(df_base: pd.DataFrame) -> pd.DataFrame:
    df_base = df_base.sort_values("date").reset_index(drop=True)
    test_cutoff = df_base["date"].max() - pd.DateOffset(years=TEST_YEARS)
    test_start_idx = int((df_base["date"] >= test_cutoff).idxmax())
    n_total = len(df_base)

    log.info("Test period: %s -> %s (%d months)",
             df_base["date"].iloc[test_start_idx].date(),
             df_base["date"].iloc[-1].date(),
             n_total - test_start_idx)

    records: list[dict] = []
    for h in HORIZONS:
        df = df_base.copy()
        # Target = change over h months
        target_col = f"dy_h{h}"
        df[target_col] = df["lake_level_m"].shift(-h) - df["lake_level_m"]
        feature_cols = get_feature_cols(df, target_col)

        log.info("Horizon %d: %d features (target = dL over %d months)",
                 h, len(feature_cols), h)

        for train_end in range(test_start_idx - 1, n_total - 1):
            target_idx = train_end + h
            if target_idx >= n_total:
                break

            train = df.iloc[: train_end - h + 1].dropna(subset=[target_col])
            X_train, y_train = train[feature_cols], train[target_col]
            X_test = df.iloc[[train_end]][feature_cols]

            model = xgb.XGBRegressor(**XGB_PARAMS)
            model.fit(X_train, y_train, verbose=False)
            dL_pred = float(model.predict(X_test)[0])

            current_level = float(df["lake_level_m"].iloc[train_end])
            pred_level    = current_level + dL_pred

            records.append({
                "date":            df["date"].iloc[target_idx],
                "horizon_months":  h,
                "model":           "xgboost_diff",
                "y_true":          float(df["lake_level_m"].iloc[target_idx]),
                "y_pred":          pred_level,
                "dL_true":         float(df["lake_level_m"].iloc[target_idx]) - current_level,
                "dL_pred":         dL_pred,
            })

        log.info("  ... horizon %d done (%d forecasts)", h, sum(r["horizon_months"] == h for r in records))

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


def feature_importance(df_base: pd.DataFrame, top_k: int = 15) -> pd.DataFrame:
    df_base = df_base.sort_values("date").reset_index(drop=True)
    importance_rows: list[dict] = []
    for h in HORIZONS:
        df = df_base.copy()
        target_col = f"dy_h{h}"
        df[target_col] = df["lake_level_m"].shift(-h) - df["lake_level_m"]
        feature_cols = get_feature_cols(df, target_col)
        train = df.dropna(subset=[target_col])

        model = xgb.XGBRegressor(**XGB_PARAMS)
        model.fit(train[feature_cols], train[target_col], verbose=False)

        imp = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
        for rank, (feat, val) in enumerate(imp.head(top_k).items(), start=1):
            importance_rows.append({
                "horizon_months": h,
                "rank":           rank,
                "feature":        feat,
                "importance":     float(val),
            })
    return pd.DataFrame(importance_rows)


def main() -> None:
    log.info("Reading %s", DATA_CSV.name)
    df = pd.read_csv(DATA_CSV, parse_dates=["date"])
    log.info("Modeling data: %d months x %d cols", *df.shape)

    preds = rolling_forecast(df)
    metrics = metrics_table(preds, "xgboost_diff")

    log.info("Computing feature importance on full training data ...")
    feat_imp = feature_importance(df)

    OUT_PREDS.parent.mkdir(parents=True, exist_ok=True)
    preds.to_csv(OUT_PREDS, index=False)
    metrics.to_csv(OUT_METRICS, index=False)
    feat_imp.to_csv(OUT_FEAT_IMP, index=False)
    log.info("Wrote %s", OUT_PREDS.relative_to(REPO_ROOT))
    log.info("Wrote %s", OUT_METRICS.relative_to(REPO_ROOT))
    log.info("Wrote %s", OUT_FEAT_IMP.relative_to(REPO_ROOT))

    baseline       = pd.read_csv(BASELINE_CSV)
    sarimax        = pd.read_csv(SARIMAX_CSV)
    xgb_level      = pd.read_csv(XGB_LEVEL_CSV)
    recent_baseline = baseline[baseline["period"] == f"recent_{TEST_YEARS}y"]
    comparison = pd.concat([recent_baseline, sarimax, xgb_level, metrics], ignore_index=True)
    comparison = comparison.sort_values(["horizon_months", "model"]).reset_index(drop=True)
    comparison.to_csv(OUT_COMPARISON, index=False)

    print()
    print(f"=== All models, recent {TEST_YEARS}-year test period ===")
    print()
    print(comparison[["model", "horizon_months", "n", "mae_m", "rmse_m", "bias_m"]].to_string(index=False))
    print()

    pivot = comparison.pivot(index="horizon_months", columns="model", values="mae_m")[
        ["persistence", "seasonal_naive", "sarimax", "xgboost", "xgboost_diff"]
    ]
    print("MAE (m) by model and horizon (lower = better):")
    print()
    print(pivot.round(3).to_string())
    print()
    print("Top 5 features per horizon (XGBoost on differences):")
    print()
    print(feat_imp.groupby("horizon_months").head(5).to_string(index=False))


if __name__ == "__main__":
    main()
