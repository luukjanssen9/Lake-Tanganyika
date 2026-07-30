"""Slide-ready validation comparison chart for the water level prediction models.

Reads reports/metrics_extended.csv and plots RMSE (m) by forecast
horizon, grouped by model.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPORTS = Path(__file__).resolve().parents[2] / "reports"
OUT = REPORTS / "validation_rmse_by_horizon.png"

# Models to show, in a sensible order, with friendly labels.
MODEL_ORDER = {
    "persistence": "Persistence",
    "seasonal_naive": "Seasonal naive",
    "sarimax": "SARIMAX",
    "xgboost_diff": "XGBoost (diff)",
}
COLORS = ["#9aa5b1", "#c0c5cc", "#2c7fb8", "#d7642c"]

df = pd.read_csv(REPORTS / "metrics_extended.csv")
horizons = sorted(df["horizon_months"].unique())

fig, ax = plt.subplots(figsize=(8.5, 4.8))
n_models = len(MODEL_ORDER)
group_w = 0.8
bar_w = group_w / n_models
x = np.arange(len(horizons))

for i, (key, label) in enumerate(MODEL_ORDER.items()):
    vals = [
        df[(df.model == key) & (df.horizon_months == h)]["rmse_m"].squeeze()
        for h in horizons
    ]
    offset = (i - (n_models - 1) / 2) * bar_w
    bars = ax.bar(x + offset, vals, bar_w, label=label, color=COLORS[i],
                  edgecolor="white", linewidth=0.6)
    ax.bar_label(bars, fmt="%.2f", padding=2, fontsize=7, color="#333")

ax.set_xticks(x)
ax.set_xticklabels([f"{h} month{'s' if h > 1 else ''}" for h in horizons])
ax.set_xlabel("Forecast horizon")
ax.set_ylabel("RMSE (m)")
ax.set_title("Water level forecast accuracy by model and horizon\n"
             "(validation on recent 5 years)",
             fontsize=11)
ax.legend(ncol=n_models, fontsize=8, loc="upper center",
          bbox_to_anchor=(0.5, -0.15), frameon=False)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.3)
ax.margins(y=0.12)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight")
print(f"Saved {OUT}")
