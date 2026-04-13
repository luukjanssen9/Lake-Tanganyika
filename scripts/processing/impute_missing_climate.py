"""
Impute missing temperature and precipitation in the per-river monthly CSVs
using ERA5 reanalysis data that is already embedded in each file.

Strategy
--------
Temperature (temp_max_observed, temp_min_observed, temp_mean_observed):
    Filled directly from the ERA5 monthly min/max/mean of 2m temperature
    (era5_t2m_max, era5_t2m_min, era5_t2m_mean).  ERA5 t2m is already in °C
    in the output files.  Taking the monthly min/max of hourly values is
    the standard approach for deriving daily-range proxies from reanalysis.

Precipitation (precip_observed):
    ERA5 total precipitation (era5_tp_sum, mm/month) is used, but with a
    per-river bias correction:

        bias_factor = mean(precip_observed) / mean(era5_tp_sum)

    computed over months where BOTH observed and ERA5 values are present.
    The corrected ERA5 value (era5_tp_sum * bias_factor) is then used to
    fill gaps.  This removes the systematic offset between the coarse ERA5
    grid and local rain gauges.

Output columns added
--------------------
    temp_max_imputed   bool  — True if temp_max_observed was filled
    temp_min_imputed   bool  — True if temp_min_observed was filled
    temp_mean_imputed  bool  — True if temp_mean_observed was filled
    precip_imputed     bool  — True if precip_observed was filled
    precip_bias_factor float — bias correction factor applied to ERA5 precip
                               (NaN if not enough overlap to compute)

Output files
------------
    outputs/per_river/<river>_imputed_monthly.csv  — one per river
    outputs/master_dataset_imputed.csv             — all rivers combined

Usage
-----
    python scripts/impute_missing_climate.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

OUTPUT_DIR    = Path(__file__).resolve().parent.parent.parent / "data" / "outputs"
PER_RIVER_IN  = OUTPUT_DIR / "per_river"
PER_RIVER_OUT = OUTPUT_DIR / "per_river"
COMBINED_OUT  = OUTPUT_DIR / "imputed_output_ezgi.csv"

# Minimum number of overlapping months required to compute a bias factor.
# If fewer overlap months exist, ERA5 is used uncorrected.
MIN_OVERLAP_MONTHS = 12


# ---------------------------------------------------------------------------
# Core imputation
# ---------------------------------------------------------------------------

def compute_precip_bias_factor(df: pd.DataFrame) -> float | None:
    """
    Return mean(precip_observed) / mean(era5_tp_sum) over months where both
    are non-null, or None if there is insufficient overlap.
    """
    overlap = df[df["precip_observed"].notna() & df["era5_tp_sum"].notna()]
    if len(overlap) < MIN_OVERLAP_MONTHS:
        return None
    era5_mean = overlap["era5_tp_sum"].mean()
    if era5_mean == 0:
        return None
    return float(overlap["precip_observed"].mean() / era5_mean)


def impute_river(df: pd.DataFrame, river: str) -> pd.DataFrame:
    out = df.copy()

    # ---- Temperature -------------------------------------------------------
    for obs_col, era5_col, flag_col in [
        ("temp_max_observed", "era5_t2m_max", "temp_max_imputed"),
        ("temp_min_observed", "era5_t2m_min", "temp_min_imputed"),
    ]:
        missing = out[obs_col].isna()
        out[flag_col] = False
        if era5_col in out.columns:
            out.loc[missing, obs_col]  = out.loc[missing, era5_col]
            out.loc[missing, flag_col] = True

    n_temp_filled = out["temp_max_imputed"].sum()

    # ---- Precipitation -----------------------------------------------------
    bias_factor = compute_precip_bias_factor(out)
    out["precip_bias_factor"] = bias_factor if bias_factor is not None else float("nan")
    out["precip_imputed"] = False

    missing_precip = out["precip_observed"].isna()
    if "era5_tp_sum" in out.columns and missing_precip.any():
        era5_corrected = out["era5_tp_sum"] * (bias_factor if bias_factor is not None else 1.0)
        out.loc[missing_precip, "precip_observed"] = era5_corrected.loc[missing_precip]
        out.loc[missing_precip, "precip_imputed"]  = True

    n_precip_filled = out["precip_imputed"].sum()

    bias_str = f"{bias_factor:.3f}" if bias_factor is not None else "N/A (uncorrected)"
    log.info(
        "  %s: temp filled=%d  precip filled=%d  precip_bias_factor=%s",
        river, n_temp_filled, n_precip_filled, bias_str,
    )

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    river_files = sorted(PER_RIVER_IN.glob("*_monthly.csv"))
    # Exclude already-imputed files if re-running
    river_files = [f for f in river_files if "_imputed" not in f.stem]

    if not river_files:
        log.error("No per-river CSVs found in %s", PER_RIVER_IN)
        return

    log.info("Imputing %d river files …", len(river_files))
    all_frames: list[pd.DataFrame] = []

    for path in river_files:
        river = path.stem.replace("_monthly", "").title()
        log.info("[%s]  %s", river, path.name)

        df = pd.read_csv(path, parse_dates=["date"])
        imputed = impute_river(df, river)

        out_path = PER_RIVER_OUT / f"{path.stem.replace('_monthly', '')}_imputed_monthly.csv"
        imputed.to_csv(out_path, index=False)

        all_frames.append(imputed)

    combined = pd.concat(all_frames, ignore_index=True).sort_values(["river", "date"])
    combined.to_csv(COMBINED_OUT, index=False)
    log.info("Combined imputed dataset → %s  (%d rows)", COMBINED_OUT.name, len(combined))

    # Summary
    print("\n--- Imputation summary ---")
    for df in all_frames:
        river = df["river"].iloc[0]
        n_total = len(df)
        n_temp  = int(df["temp_max_imputed"].sum())
        n_prec  = int(df["precip_imputed"].sum())
        bf      = df["precip_bias_factor"].iloc[0]
        bf_str  = f"{bf:.3f}" if pd.notna(bf) else "N/A"
        print(
            f"  {river:<14}  temp_filled={n_temp:>3}/{n_total}  "
            f"precip_filled={n_prec:>3}/{n_total}  bias_factor={bf_str}"
        )


if __name__ == "__main__":
    run()
