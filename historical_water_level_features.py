"""
Create historical water level lag features for prediction / imputation.

This script does not modify the original water_level column or overwrite the
input dataset. It creates new predictor columns such as water_level_lag_1,
water_level_lag_2, and water_level_lag_3, then saves the updated dataframe to
a new CSV file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Configurable parameters
# ---------------------------------------------------------------------------

DEFAULT_INPUT_PATH = Path("data/outputs/master_dataset_inputed.csv")
DEFAULT_OUTPUT_PATH = Path("data/outputs/master_dataset_with_historical_water_level_features.csv")
DEFAULT_SUMMARY_OUTPUT_PATH = Path("data/outputs/historical_water_level_features_summary.csv")

DEFAULT_WATER_LEVEL_COL = "water_level"
DEFAULT_DATE_COL = "date"

# Set to None to auto-detect a group column. In this project, "river" is the
# station/location identifier, so lag features are created separately by river.
DEFAULT_GROUP_COL = "river"

# Change this list to create a different number of historical lag predictors.
# Example: [1, 2, 3, 6, 12] creates 1-, 2-, 3-, 6-, and 12-month lag features.
DEFAULT_LAG_MONTHS = [1, 2, 3]

GROUP_COLUMN_CANDIDATES = [
    "river",
    "lake",
    "station",
    "station_id",
    "basin",
    "location",
    "site",
]


def load_dataset(input_path: Path, date_col: str) -> pd.DataFrame:
    """Load the dataset and parse the date column."""
    print(f"Loading dataset from {input_path}")
    df = pd.read_csv(input_path, parse_dates=[date_col])
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns")
    return df


def detect_column(df: pd.DataFrame, preferred_col: str | None, candidates: list[str]) -> str | None:
    """
    Return the preferred column if it exists; otherwise return the first
    matching candidate column. If none exists, return None.
    """
    if preferred_col and preferred_col in df.columns:
        return preferred_col

    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def validate_inputs(
    df: pd.DataFrame,
    water_level_col: str,
    date_col: str,
    lag_months: list[int],
) -> None:
    """Validate required columns and lag values before feature creation."""
    missing_cols = [col for col in [water_level_col, date_col] if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required column(s): {missing_cols}")

    if not lag_months:
        raise ValueError("lag_months must contain at least one positive integer.")

    invalid_lags = [lag for lag in lag_months if not isinstance(lag, int) or lag <= 0]
    if invalid_lags:
        raise ValueError(f"All lag values must be positive integers. Invalid values: {invalid_lags}")


def sort_for_lag_creation(df: pd.DataFrame, date_col: str, group_col: str | None) -> pd.DataFrame:
    """
    Sort rows before creating lag features.

    If a group column exists, each station/river/lake is sorted independently
    by date. This prevents values from one group being used as lag predictors
    for another group.
    """
    sort_cols = [date_col] if group_col is None else [group_col, date_col]
    return df.sort_values(sort_cols).reset_index(drop=True)


def create_water_level_lag_features(
    df: pd.DataFrame,
    water_level_col: str,
    date_col: str,
    group_col: str | None,
    lag_months: list[int],
) -> tuple[pd.DataFrame, list[str]]:
    """
    Create lag features from previous water level values only.

    A positive shift is used, so row t receives values from t-1, t-2, etc.
    This prevents future water level values from being used as predictors.
    """
    validate_inputs(df, water_level_col, date_col, lag_months)

    out = sort_for_lag_creation(df.copy(), date_col, group_col)
    created_cols: list[str] = []

    for lag in lag_months:
        lag_col = f"{water_level_col}_lag_{lag}"

        if group_col is None:
            out[lag_col] = out[water_level_col].shift(lag)
        else:
            out[lag_col] = out.groupby(group_col, sort=False)[water_level_col].shift(lag)

        created_cols.append(lag_col)

    return out, created_cols


def save_dataset(df: pd.DataFrame, output_path: Path) -> None:
    """Save the dataframe with lag features to a new CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved dataset with historical water level features to {output_path}")


def save_summary(
    summary_path: Path,
    input_path: Path,
    output_path: Path,
    water_level_col: str,
    date_col: str,
    group_col: str | None,
    lag_months: list[int],
    created_cols: list[str],
    row_count: int,
    column_count: int,
) -> None:
    """Save a compact summary file that can be shared with the outputs."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(
        [
            {
                "input_file": str(input_path),
                "output_file": str(output_path),
                "water_level_column": water_level_col,
                "date_column": date_col,
                "group_column": group_col if group_col else "",
                "lag_months": ", ".join(str(lag) for lag in lag_months),
                "created_lag_columns": ", ".join(created_cols),
                "row_count": row_count,
                "column_count": column_count,
            }
        ]
    )
    summary.to_csv(summary_path, index=False)
    print(f"Saved feature creation summary to {summary_path}")


def print_summary(
    water_level_col: str,
    date_col: str,
    group_col: str | None,
    created_cols: list[str],
    output_path: Path,
) -> None:
    """Print a short run summary."""
    print("\nHistorical water level feature summary")
    print("--------------------------------------")
    print(f"Detected water level column: {water_level_col}")
    print(f"Detected date column: {date_col}")
    print(f"Detected group column: {group_col if group_col else 'None'}")
    print(f"Created lag feature columns: {', '.join(created_cols)}")
    print(f"Output file path: {output_path}")


def run_feature_creation(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    summary_output_path: Path = DEFAULT_SUMMARY_OUTPUT_PATH,
    water_level_col: str = DEFAULT_WATER_LEVEL_COL,
    date_col: str = DEFAULT_DATE_COL,
    group_col: str | None = DEFAULT_GROUP_COL,
    lag_months: list[int] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Load the dataset, create historical water level lag features, and save the
    updated dataframe to a new CSV file.
    """
    if lag_months is None:
        lag_months = DEFAULT_LAG_MONTHS

    df = load_dataset(input_path, date_col)
    detected_group_col = detect_column(df, group_col, GROUP_COLUMN_CANDIDATES)

    out, created_cols = create_water_level_lag_features(
        df=df,
        water_level_col=water_level_col,
        date_col=date_col,
        group_col=detected_group_col,
        lag_months=lag_months,
    )

    save_dataset(out, output_path)
    save_summary(
        summary_path=summary_output_path,
        input_path=input_path,
        output_path=output_path,
        water_level_col=water_level_col,
        date_col=date_col,
        group_col=detected_group_col,
        lag_months=lag_months,
        created_cols=created_cols,
        row_count=len(out),
        column_count=len(out.columns),
    )
    print_summary(water_level_col, date_col, detected_group_col, created_cols, output_path)
    return out, created_cols


if __name__ == "__main__":
    run_feature_creation()
