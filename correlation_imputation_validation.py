"""
Correlation-based validation pipeline for water level imputation.

This script was created in the workspace root:
    /Users/ezgi/Desktop/Lake-Tanganyika/correlation_imputation_validation.py

It reads the existing master dataset, creates a validation mask, fills it using
a correlation-based donor regression, evaluates the imputed values, and
writes both the full validation dataframe and a metrics summary to CSV files.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path


DEFAULT_INPUT_PATH = Path("data/outputs/master_dataset_inputed.csv")
DEFAULT_OUTPUT_RESULTS = Path("correlation_validation_results.csv")
DEFAULT_OUTPUT_METRICS = Path("correlation_validation_metrics.csv")
DEFAULT_ORIGINAL_COL = "water_level"
DEFAULT_VALIDATION_COL = "water_level_validation"
DEFAULT_IMPUTED_COL = "water_level_imputed_corr_validation"
DEFAULT_MASK_COLUMN = "water_level_validation_masked"
DEFAULT_MASK_FRACTION = 0.10
DEFAULT_RANDOM_SEED = 2026
DEFAULT_MIN_CORR = 0.25
DEFAULT_MIN_OVERLAP = 12


def load_dataset(input_path: Path) -> pd.DataFrame:
    print(f"Loading dataset from {input_path}")
    df = pd.read_csv(input_path, parse_dates=["date"])
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns")
    return df


def create_validation_column(df: pd.DataFrame, original_col: str, validation_col: str) -> pd.DataFrame:
    df = df.copy()
    df[validation_col] = df[original_col]
    print(f"Created validation column: {validation_col}")
    return df


def mask_validation_values(
    df: pd.DataFrame,
    original_col: str,
    validation_col: str,
    mask_fraction: float,
    random_seed: int,
    mask_col: str,
) -> pd.DataFrame:
    df = df.copy()
    valid_indices = df.index[df[original_col].notna()]
    n_to_mask = int(np.floor(len(valid_indices) * mask_fraction))
    if n_to_mask <= 0:
        raise ValueError("Not enough non-missing original values to mask with the given fraction.")

    masked_idx = df.loc[valid_indices].sample(n=n_to_mask, random_state=random_seed).index
    df.loc[masked_idx, validation_col] = np.nan
    df[mask_col] = False
    df.loc[masked_idx, mask_col] = True
    print(f"Masked {n_to_mask} rows in {validation_col} (out of {len(valid_indices)} known values)")
    return df


def build_pivot(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    pivot = df.pivot(index="date", columns="river", values=value_col)
    pivot.index.name = "date"
    return pivot


def compute_correlations(pivot: pd.DataFrame) -> pd.DataFrame:
    return pivot.corr(method="pearson", min_periods=DEFAULT_MIN_OVERLAP)


def fit_simple_regression(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if len(x) < 2:
        return 0.0, np.nan
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def impute_correlation_validation(
    df: pd.DataFrame,
    original_col: str,
    validation_col: str,
    imputed_col: str,
    min_corr: float,
    min_overlap: int,
) -> pd.DataFrame:
    df = df.copy()
    df[imputed_col] = df[validation_col].copy()

    pivot_orig = build_pivot(df, original_col)
    pivot_valid = build_pivot(df, validation_col)
    corr_matrix = compute_correlations(pivot_orig)

    print("Computing donor rivers for each target river using correlation matrix...")

    for target_river in pivot_valid.columns:
        donor_corr = corr_matrix[target_river].drop(labels=[target_river], errors="ignore").dropna()
        donor_corr = donor_corr.sort_values(ascending=False)
        donor_corr = donor_corr[donor_corr >= min_corr]

        if donor_corr.empty:
            print(f"  No donor rivers with correlation >= {min_corr} for {target_river}")
            continue

        masked_dates = pivot_valid.index[pivot_valid[target_river].isna()]
        if len(masked_dates) == 0:
            continue

        target_series_orig = pivot_orig[target_river]

        for donor_river, corr_value in donor_corr.items():
            donor_series_orig = pivot_orig[donor_river]
            valid_overlap = target_series_orig.notna() & donor_series_orig.notna()
            if valid_overlap.sum() < min_overlap:
                continue

            x = donor_series_orig[valid_overlap].to_numpy()
            y = target_series_orig[valid_overlap].to_numpy()
            slope, intercept = fit_simple_regression(x, y)
            if np.isnan(intercept):
                continue

            donor_values = donor_series_orig.reindex(masked_dates)
            fillable = donor_values.notna()
            if not fillable.any():
                continue

            predicted_values = slope * donor_values[fillable].to_numpy() + intercept
            fill_dates = masked_dates[fillable]

            for date_value, predicted in zip(fill_dates, predicted_values):
                row_mask = (
                    (df["river"] == target_river)
                    & (df["date"] == date_value)
                    & (df[validation_col].isna())
                )
                df.loc[row_mask, imputed_col] = predicted

            remaining = df.loc[
                (df["river"] == target_river)
                & (df[validation_col].isna()),
                imputed_col,
            ].isna().sum()
            if remaining == 0:
                break

        print(f"  Finished target river {target_river}, remaining masked values: {remaining}")

    return df


def calculate_metrics(
    df: pd.DataFrame,
    original_col: str,
    imputed_col: str,
    mask_col: str,
) -> pd.DataFrame:
    mask = df[mask_col] == True
    validation_df = df.loc[mask, [original_col, imputed_col]].dropna(subset=[imputed_col])
    n_points = len(validation_df)

    if n_points == 0:
        print("No validation points were imputed; metrics cannot be computed.")
        return pd.DataFrame(
            [
                {
                    "method": "correlation",
                    "MAE": np.nan,
                    "RMSE": np.nan,
                    "R2": np.nan,
                    "n_validated_points": 0,
                }
            ]
        )

    y_true = validation_df[original_col].to_numpy()
    y_pred = validation_df[imputed_col].to_numpy()
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    metrics = pd.DataFrame(
        [
            {
                "method": "correlation",
                "MAE": mae,
                "RMSE": rmse,
                "R2": r2,
                "n_validated_points": n_points,
            }
        ]
    )

    print("Validation metrics:")
    print(metrics.to_string(index=False))
    return metrics


def save_results(df: pd.DataFrame, metrics: pd.DataFrame, results_path: Path, metrics_path: Path) -> None:
    df.to_csv(results_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    print(f"Saved full validation results to {results_path}")
    print(f"Saved validation metrics to {metrics_path}")


def run_validation(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_results: Path = DEFAULT_OUTPUT_RESULTS,
    output_metrics: Path = DEFAULT_OUTPUT_METRICS,
    original_col: str = DEFAULT_ORIGINAL_COL,
    validation_col: str = DEFAULT_VALIDATION_COL,
    imputed_col: str = DEFAULT_IMPUTED_COL,
    mask_fraction: float = DEFAULT_MASK_FRACTION,
    random_seed: int = DEFAULT_RANDOM_SEED,
    mask_col: str = DEFAULT_MASK_COLUMN,
    min_corr: float = DEFAULT_MIN_CORR,
    min_overlap: int = DEFAULT_MIN_OVERLAP,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_dataset(input_path)
    df = create_validation_column(df, original_col, validation_col)
    df = mask_validation_values(df, original_col, validation_col, mask_fraction, random_seed, mask_col)
    df = impute_correlation_validation(df, original_col, validation_col, imputed_col, min_corr, min_overlap)
    metrics = calculate_metrics(df, original_col, imputed_col, mask_col)
    save_results(df, metrics, output_results, output_metrics)
    return df, metrics


if __name__ == "__main__":
    print("Starting correlation-based validation pipeline.")
    _, metrics_df = run_validation()
    print("Done.")
    print(metrics_df.to_string(index=False))
