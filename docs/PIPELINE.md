# Lake Tanganyika water-level forecasting — pipeline

## 1. Data
The repo only had river-gauge data, no actual lake-wide measurements. We downloaded **Lake Tanganyika satellite altimetry from DAHITI** (TU Munich) — 817 observations from 1992 to 2026 — and aggregated to monthly means. We joined this with **ERA5 reanalysis weather** (precipitation, temperature, wind) over the catchment and **12 river-station water levels**. Then we engineered features — lags (1, 2, 3, 6, 12 months) and rolling averages (3, 6, 12, 24, 36 months) of every variable — so models have a memory of the past. Final modeling table: **403 monthly rows × 134 columns**.

## 2. Baselines
Two trivial forecasters to set a floor that any real model has to beat:

- **Persistence:** next month = this month
- **Seasonal-naïve:** next month = same month last year

These give MAE of 13–37 cm depending on horizon. Any model that can't beat them is using no real information.

## 3. SARIMAX — classical statistics
A linear time-series model that predicts each value from past values, past errors, and external inputs. We used `SARIMAX(1,1,1)×(1,1,1,12)` with ERA5 precipitation and temperature as exogenous inputs. The differencing handles the strong 2020–2024 lake rise; the seasonal terms capture the annual cycle. **Result: best model at every horizon (MAE 0.10–0.18 m).**

## 4. XGBoost — machine learning
An ensemble of 500 gradient-boosted decision trees using all 125+ engineered features. Two variants:

- **Predicting the absolute level:** failed — trees can't extrapolate, so during the 2020+ rise it under-predicted by up to 28 cm.
- **Predicting the change** ΔL = L[t+h] − L[t]: fixed the bias because changes are stationary. Came close to SARIMAX but didn't beat it.

## Validation
Forward-chaining rolling forecast on the last 5 years (April 2021 → April 2026). At each test month, train on all earlier data and predict 1, 3, 6 months ahead. All models tested on the same dates.

## Final ranking (MAE in meters)

| Horizon | Persistence | Seasonal-naïve | SARIMAX | XGBoost (level) | XGBoost (diff) |
|---:|---:|---:|---:|---:|---:|
| 1 mo | 0.126 | 0.279 | **0.101** | 0.152 | 0.103 |
| 3 mo | 0.278 | 0.279 | **0.153** | 0.272 | 0.168 |
| 6 mo | 0.370 | 0.279 | **0.179** | 0.327 | 0.217 |

## Takeaway
The lake's monthly dynamics are mostly **linear**, so the simple classical model wins. Adding ML complexity didn't help once the right structural pieces (autoregression + trend handling + seasonality + weather) were in place.

## Repository navigation

| What you want to do | Command |
|---|---|
| Re-download the lake data | `python scripts/download/download_dahiti_lake_level.py` |
| Monthly target | pre-built and committed: `data/processed/lake_tanganyika_monthly.csv` |
| Re-build the modeling table | `python scripts/forecasting/01_build_lake_level_table.py` |
| Run any model | `python scripts/forecasting/0{2,3,4,5}_*.py` |
| Re-compute all metrics | `python scripts/forecasting/06_metrics_extended.py` |
