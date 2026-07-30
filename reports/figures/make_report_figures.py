"""
Generate report figures for Lake Tanganyika from existing repo data.

Outputs (into this folder):
    lake_prediction_h1.png, lake_prediction_h3.png, lake_prediction_h6.png
        Observed vs predicted lake level (SARIMAX + XGBoost) for each forecast
        horizon, with the SARIMAX 95% prediction interval shaded.
    dahiti_lake_level_trend.png
        Full DAHITI satellite-altimetry water-level record with a linear trend.

Run:
    python reports/figures/make_report_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "reports"
DAHITI_CSV = REPO / "data" / "outputs" / "dahiti" / "lake_tanganyika_water_level.csv"
OUT = REPO / "reports" / "figures"

HORIZONS = [1, 3, 6]
OBS_COLOR = "#172033"
SARIMAX_COLOR = "#207c7a"
XGB_COLOR = "#2f68b1"
TREND_COLOR = "#b24a62"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#e9eef2",
    "grid.linewidth": 0.8,
    "figure.dpi": 150,
})


def prediction_figures() -> None:
    sarimax = pd.read_csv(REPORTS / "sarimax_predictions.csv", parse_dates=["date"])
    xgb = pd.read_csv(REPORTS / "xgboost_predictions.csv", parse_dates=["date"])

    for h in HORIZONS:
        s = sarimax[sarimax["horizon_months"] == h].sort_values("date")
        x = xgb[xgb["horizon_months"] == h].sort_values("date")

        fig, ax = plt.subplots(figsize=(9, 4.2))

        # Observed (y_true carried in the prediction rows).
        ax.plot(x["date"], x["y_true"], color=OBS_COLOR, lw=2.4, label="Observed", zorder=3)

        # SARIMAX mean forecast (single line, no interval band).
        ax.plot(s["date"], s["y_pred"], color=SARIMAX_COLOR, lw=2.0,
                label="SARIMAX forecast", zorder=2)

        # XGBoost mean forecast.
        ax.plot(x["date"], x["y_pred"], color=XGB_COLOR, lw=2.0, ls="--",
                label="XGBoost forecast", zorder=2)

        ax.set_title(f"Observed vs predicted lake level — {h}-month horizon", fontsize=13)
        ax.set_ylabel("Lake level (m)")
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.legend(loc="upper left", frameon=False, fontsize=9.5, ncol=2)
        fig.tight_layout()
        out = OUT / f"lake_prediction_h{h}.png"
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        print(f"wrote {out.relative_to(REPO)}")


def dahiti_trend_figure() -> None:
    df = pd.read_csv(DAHITI_CSV, parse_dates=["date"]).sort_values("date")
    df = df.dropna(subset=["water_level_m"])

    # Linear trend in meters per year (x = fractional years since first obs).
    t0 = df["date"].iloc[0]
    years = (df["date"] - t0).dt.total_seconds() / (365.25 * 24 * 3600)
    slope, intercept = np.polyfit(years, df["water_level_m"], 1)
    trend = slope * years + intercept
    slope_mm = slope * 1000  # mm/year

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    ax.plot(df["date"], df["water_level_m"], color=OBS_COLOR, lw=1.0, alpha=0.85,
            label="DAHITI water level")
    ax.plot(df["date"], trend, color=TREND_COLOR, lw=2.4,
            label=f"Linear trend (+{slope_mm:.1f} mm/yr)")

    span_years = years.iloc[-1]
    total_rise = slope * span_years
    ax.set_title("Lake Tanganyika water level (DAHITI satellite altimetry)", fontsize=13)
    ax.set_ylabel("Water level (m)")
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    ax.annotate(
        f"+{slope_mm:.1f} mm/yr  (≈ {total_rise:.2f} m over "
        f"{df['date'].iloc[0].year}–{df['date'].iloc[-1].year})",
        xy=(0.99, 0.04), xycoords="axes fraction", ha="right", va="bottom",
        fontsize=9.5, color=TREND_COLOR,
    )
    fig.tight_layout()
    out = OUT / "dahiti_lake_level_trend.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.relative_to(REPO)}")
    print(f"  trend = {slope_mm:.2f} mm/yr,  total rise ~ {total_rise:.2f} m over {span_years:.1f} yr")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    prediction_figures()
    dahiti_trend_figure()
