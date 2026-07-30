"""
Build the monthly modeling table for Lake Tanganyika water-level forecasting.

Target:
    data/processed/lake_tanganyika_monthly.csv     (DAHITI altimetry, Step 1)

Exogenous drivers:
    data/era5/csv_monthly/era5_grid_*_monthly.csv   (ERA5 catchment cells)
    data/station_level/*.csv                        (12 river-level stations)

Output:
    data/processed/lake_tanganyika_modeling_table.csv

Usage:
    python scripts/forecasting/01_build_lake_level_table.py
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

REPO_ROOT  = Path(__file__).resolve().parents[2]
LAKE_CSV   = REPO_ROOT / "data" / "processed" / "lake_tanganyika_monthly.csv"
ERA5_DIR   = REPO_ROOT / "data" / "era5" / "csv_monthly"
RIVERS_DIR = REPO_ROOT / "data" / "station_level"
OUT_CSV    = REPO_ROOT / "data" / "processed" / "lake_tanganyika_modeling_table.csv"

LAGS    = [1, 2, 3, 6, 12]
WINDOWS = [3, 6, 12, 24, 36]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_target() -> pd.DataFrame:
    log.info("Loading target: %s", LAKE_CSV.name)
    df = pd.read_csv(LAKE_CSV, parse_dates=["date"])
    df = df[["date", "water_level_m", "n_obs"]].rename(
        columns={"water_level_m": "lake_level_m", "n_obs": "lake_level_n_obs"}
    )
    df["lake_level_m"] = df["lake_level_m"].interpolate(method="linear", limit_direction="both")
    return df


def load_era5_catchment_mean() -> pd.DataFrame:
    files = sorted(ERA5_DIR.glob("era5_grid_*_monthly.csv"))
    log.info("Loading ERA5 monthly: %d grid-cell files", len(files))
    frames = [pd.read_csv(f, parse_dates=["month_start"]) for f in files]
    raw = pd.concat(frames, ignore_index=True)

    catchment = (
        raw.groupby("month_start", as_index=False)
           .agg(
               era5_t2m_C=("t2m_mean_C", "mean"),
               era5_d2m_C=("d2m_mean_C", "mean"),
               era5_tp_mm=("tp_sum_mm", "mean"),
               era5_msl_hPa=("msl_mean_hPa", "mean"),
               era5_u10=("u10_mean", "mean"),
               era5_v10=("v10_mean", "mean"),
           )
           .rename(columns={"month_start": "date"})
    )
    catchment["era5_wind_speed"] = np.sqrt(catchment["era5_u10"] ** 2 + catchment["era5_v10"] ** 2)
    return catchment


def load_river_levels() -> pd.DataFrame:
    files = sorted(RIVERS_DIR.glob("*.csv"))
    log.info("Loading river-station levels: %d files", len(files))

    merged: pd.DataFrame | None = None
    for f in files:
        name = f.stem.lower()
        df = pd.read_csv(f, parse_dates=["date"])[["date", "target_value"]]
        df = df.rename(columns={"target_value": f"river_{name}_level_m"})
        merged = df if merged is None else merged.merge(df, on="date", how="outer")
    return merged.sort_values("date").reset_index(drop=True) if merged is not None else pd.DataFrame(columns=["date"])


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12.0)
    return df


def add_lag_features(df: pd.DataFrame, cols: list[str], lags: list[int]) -> pd.DataFrame:
    for c in cols:
        for lag in lags:
            df[f"{c}_lag_{lag}"] = df[c].shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame, cols: list[str], windows: list[int]) -> pd.DataFrame:
    for c in cols:
        for w in windows:
            df[f"{c}_roll_mean_{w}"] = df[c].shift(1).rolling(window=w, min_periods=max(2, w // 2)).mean()
    return df


def add_precip_cumulative_anomaly(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    monthly_climatology = df.groupby("month")["era5_tp_mm"].transform("mean")
    df["era5_tp_anom"] = df["era5_tp_mm"] - monthly_climatology
    for w in windows:
        df[f"era5_tp_anom_cumsum_{w}"] = (
            df["era5_tp_anom"].shift(1).rolling(window=w, min_periods=max(2, w // 2)).sum()
        )
    return df


def add_seasonal_anomaly(df: pd.DataFrame, col: str) -> pd.DataFrame:
    climatology = df.groupby("month")[col].transform("mean")
    climatology_std = df.groupby("month")[col].transform("std").replace(0, np.nan)
    df[f"{col}_anom"] = df[col] - climatology
    df[f"{col}_zscore"] = df[f"{col}_anom"] / climatology_std
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    target = load_target()
    era5   = load_era5_catchment_mean()
    rivers = load_river_levels()

    base = pd.DataFrame({"date": pd.date_range(target["date"].min(), target["date"].max(), freq="MS")})
    df = base.merge(target, on="date", how="left")
    df = df.merge(era5,   on="date", how="left")
    df = df.merge(rivers, on="date", how="left")

    df = add_time_features(df)

    lag_cols = ["lake_level_m", "era5_tp_mm", "era5_t2m_C"] + [c for c in df.columns if c.startswith("river_")]
    df = add_lag_features(df, lag_cols, LAGS)

    rolling_cols = ["lake_level_m", "era5_tp_mm", "era5_t2m_C", "era5_d2m_C", "era5_wind_speed"]
    df = add_rolling_features(df, rolling_cols, WINDOWS)

    df = add_precip_cumulative_anomaly(df, WINDOWS)
    df = add_seasonal_anomaly(df, "lake_level_m")

    df = df.sort_values("date").reset_index(drop=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)

    n_target = int(df["lake_level_m"].notna().sum())
    log.info("Wrote modeling table: %s  (%d rows x %d cols; target non-null: %d)",
             OUT_CSV, len(df), df.shape[1], n_target)
    log.info("Date range: %s -> %s", df["date"].min().date(), df["date"].max().date())


if __name__ == "__main__":
    main()
