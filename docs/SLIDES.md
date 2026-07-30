# Slide Deck — Lake Tanganyika Water-Level Forecasting

Five-slide deck for a progress update with the professor.
Copy each slide block into PowerPoint / Google Slides / Keynote.

---

## Slide 1 — Title & overview

# Lake Tanganyika water-level forecasting
### Monthly forecasts at 1, 3, 6-month horizons

**What I've built so far:**

- First lake-wide water-level dataset for this project (DAHITI satellite altimetry)
- Unified monthly modeling table merging altimetry, ERA5 weather, and 12 river gauges
- Four forecasting approaches spanning naïve baselines, classical time-series, and machine learning
- Validation framework with rolling-window cross-validation on the last 5 years
- Quantified skill at 1, 3, 6-month horizons against multiple reference forecasts

> **Headline result:** SARIMAX with ERA5 weather wins at every horizon, MAE 0.10–0.18 m

---

## Slide 2 — Data

# Data: three sources, unified to monthly

| Source | What | Resolution | Span | Role |
|---|---|---|---|---|
| **DAHITI** (TU Munich) | Lake surface elevation, satellite altimetry | ~10-day | 1992 → 2026 (817 obs) | **Target** |
| **ERA5** (Copernicus) | Catchment weather (precip, temp, wind, humidity, MSLP) | Hourly → monthly mean | 1940 → 2026 | Drivers |
| **IGEBU** (Burundi) | 12 river-station water levels | Monthly | 1981 → 2024 | Inflow proxies |

**→ `lake_tanganyika_modeling_table.csv`: 403 rows × 134 columns**

Engineered features:
- **Lags** at 1, 2, 3, 6, 12 months
- **Rolling means** at 3, 6, 12, **24, 36** months (long windows for the lake's multi-year storage memory)
- **Cyclical time encoding** (month_sin, month_cos)
- Anomaly / z-score features against monthly climatology

---

## Slide 3 — Methods

# Four forecasters, one validation framework

**Baselines** (no training, set the floor):
- **Persistence:** L̂[t+h] = L[t]
- **Seasonal-naïve:** L̂[t+h] = L[t+h−12]

**Classical statistics:**
- **SARIMAX(1,1,1) × (1,1,1,12)** with ERA5 precipitation + temperature as exogenous inputs
- Linear, 8 parameters, prediction intervals built in

**Machine learning:**
- **XGBoost** — 500 gradient-boosted trees, depth 4, on ~125 engineered features
- Predicts the **change** ΔL = L[t+h] − L[t] (rather than the absolute level) → reconstructs L̂[t+h] = L[t] + ΔL̂
- The differences-target ensures the model stays inside its training distribution, since lake *changes* are stationary even while lake *levels* are trending

**Validation: forward-chaining rolling forecast**
- Test window: April 2021 → April 2026 (last 5 years, 61 months)
- At each test month → train on all prior data → predict 1, 3, 6 months ahead
- All models evaluated on **identical dates** for fair comparison

---

## Slide 4 — Results

# SARIMAX wins at every horizon

**MAE (meters) — lower is better:**

| Horizon | Persistence | Seasonal-naïve | **SARIMAX** | XGBoost |
|---:|---:|---:|---:|---:|
| 1 mo | 0.126 | 0.279 | **0.101** | 0.103 |
| 3 mo | 0.278 | 0.279 | **0.153** | 0.168 |
| 6 mo | 0.370 | 0.279 | **0.179** | 0.217 |

**Skill score vs seasonal-naïve (1 = perfect, 0 = no better than naïve, < 0 = worse):**

| Horizon | SARIMAX | XGBoost |
|---:|---:|---:|
| 1 mo | **+0.89** | +0.86 |
| 3 mo | **+0.71** | +0.67 |
| 6 mo | **+0.60** | +0.38 |

- SARIMAX has **positive skill at every horizon** against both references — it adds real value over naïve forecasts
- XGBoost is close at h=1 but loses ground at longer horizons — its non-linear flexibility doesn't earn its keep
- Bias is essentially zero for both real models (≤ 0.014 m) → no systematic over- or under-prediction

---

## Slide 5 — Findings, caveats, next steps

# What we learned + what's next

**Findings:**
- The lake's monthly dynamics are mostly **linear** — SARIMAX's structural assumptions (autoregression + differencing + seasonality + weather) match the underlying process
- More ML complexity doesn't help when the relationship is already linear
- Best operational number: **0.18 m MAE at 6 months ahead (~5% of the historical lake range)**

**Caveats (honest about):**
- **Perfect-foresight weather** — SARIMAX gets real ERA5 precip/temp for the forecast period; operational use would need a seasonal weather forecast (NMME / SEAS5)
- Single 5-year test window — no robustness check across different climate periods yet
- 8 ERA5 cells are in northern Burundi, not over the lake itself or the wider catchment (Tanzania, Zambia)

**Next steps (in priority order):**
1. Add **ENSO + IOD climate indices** as exogenous inputs (free from NOAA) → expected to improve 3-6 month skill
2. **ARIMA / SARIMA ablation** to quantify the contribution of each component (autoregression vs seasonality vs weather)
3. **Lagged-exog SARIMAX** to give an honest operational lower bound
4. **Multiple test windows** (e.g., 2011–2015 as a "normal" period vs 2021–2026 with the rise) for robustness
5. Download lake-surface ERA5 cells for better evaporation drivers
