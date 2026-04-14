# Data Directory

## Overview

This folder contains all data used in the Lake Tanganyika flood research project.
Raw input data lives in `raw/` and `era5/`. Processed outputs ready for analysis are in `outputs/`.

---

## raw/Lake Tanganyika Data/Donnees Hydro et Meteo Mensuelles_IGEBU/

**Source:** IGEBU (Institut Géographique du Burundi)
**Type:** In-situ measurements, monthly resolution
**Coverage:** Varies per station, roughly 1980s–2020s

Contains two types of files:

- **River water level files** (`Niveaux d'eau de la Riviere *.xlsx`)
  Monthly gauge height (metres) at the river mouth for 11 rivers:
  Buzimba, Dama, Jiji, Kaburantwa, Mpanda, Mulembwe, Mutimbuzi,
  Nyakagunda, Nyamagana, Nyengwe, RUSIZI

- **Temperature files** (`Temperatures mensuelles de *.xlsx`)
  Monthly min/max air temperature (°C) at 6 climate stations:
  Bujumbura Aéroport, IMBO-SEMS, Mparambo, Mpota (Tora), Nyanza-Lac, Rwegura

- **Precipitation file** (`les precipitations mensuelles.xlsx`)
  Monthly precipitation totals (mm) covering multiple stations across Burundi

---

## raw/Lake Tanganyika Data/Données nouvelles/

**Source:** Various (provided by project collaborators)
**Type:** Spatial / supplementary data

| File / Folder | Description |
|---|---|
| `Ruissellement.csv` | Observed monthly runoff (m³/s) per river |
| `ImboAndMirwa_UTM35S_Shapefile/` | Shapefile of the Imbo and Mirwa regions (UTM 35S projection) |
| `Landcover/landshp_value.*` | Land cover classification shapefile |
| `landcover.asc` / `Landcover.prj` | Land cover raster (ASCII grid) with projection |
| `Donnees Topo CSV/` | Topographic indices per catchment: slope, wetness index, stream power index, sediment transport index, downslope flowpath length |
| `Donnees_Projet_AI_Athanase/Data_RainfallBDI_Corrige_1981_2023.xlsx` | Bias-corrected rainfall dataset for Burundi (1981–2023), from a separate AI project |
| `Explication des codes pour le gravier.docx` | Legend/codebook for gravel/sediment codes |

---

## era5/

**Source:** Copernicus Climate Data Store (CDS)
**Dataset:** `reanalysis-era5-single-levels-timeseries`
**Reference:** Hersbach et al. (2020), doi:10.1002/qj.3803
**Download script:** `scripts/download/era5/download_era5.py`

ERA5 reanalysis data at 0.25° grid resolution, downloaded for 8 grid points
snapped to the nearest ERA5 grid node for each river/station location.
Full hourly time series from 1940 to present.

**Variables downloaded:**
| Variable | Description | Unit |
|---|---|---|
| `t2m` | 2m air temperature | K |
| `tp` | Total precipitation | m (per hour) |
| `u10` | 10m U-component of wind | m/s |
| `v10` | 10m V-component of wind | m/s |
| `d2m` | 2m dewpoint temperature | K |
| `msl` | Mean sea level pressure | Pa |
| `sro` | Surface runoff | m |
| `pet` | Potential evapotranspiration | m |

**Grid points and stations covered:**
| Folder | Lat | Lon | Stations |
|---|---|---|---|
| `grid_m4.25_29.50` | -4.25 | 29.50 | Nyanza-Lac, Nyengwe |
| `grid_m4.00_29.50` | -4.00 | 29.50 | Buzimba, Mulembwe |
| `grid_m4.00_29.75` | -4.00 | 29.75 | Jiji |
| `grid_m3.75_29.50` | -3.75 | 29.50 | Mpota (Tora) |
| `grid_m3.25_29.25` | -3.25 | 29.25 | Bujumbura, Mutimbuzi, Rusizi |
| `grid_m3.00_29.25` | -3.00 | 29.25 | Kaburantwa, Nyamagana |
| `grid_m3.00_29.50` | -3.00 | 29.50 | Mpanda |
| `grid_m2.75_29.00` | -2.75 | 29.00 | Nyakagunda |

**Subfolders:**
- `csv/` — Hourly ERA5 data as CSV, one file per grid point (1940–2026, ~gitignored)
- `csv_monthly/` — Monthly aggregated ERA5 (mean/sum, unit-converted). Produced by `scripts/download/era5/aggregate_monthly.py`

---

## outputs/

Processed outputs ready for analysis. Produced by `scripts/processing/build_master_dataset.py` and `scripts/processing/impute_missing_climate.py`.

| File / Folder | Description |
|---|---|
| `master_dataset_monthly.csv` | All 10 rivers combined, monthly resolution. Merges IGEBU river levels, runoff, climate station observations, and ERA5 reanalysis. |
| `master_dataset_inputed.csv` | Same as above but with missing temperature and precipitation filled using ERA5 (bias-corrected for precipitation). |
| `per_river/*_monthly.csv` | Per-river version of the master dataset (one file per river). |
| `per_river/*_imputed_monthly.csv` | Per-river imputed version. |
| `output_manifest.csv` | Summary table of data availability per river (date range, row counts, missing values). |
| `imputed_output_from_mean/` | Earlier imputation outputs (Ezgi's method, mean-based). Provided by project collaborators. |
| `dahiti/lake_tanganyika_water_level.csv` | Lake Tanganyika surface water elevation from satellite altimetry (~10-day intervals, 1992–present). See below. |

### outputs/dahiti/

**Source:** DAHITI — Database for Hydrological Time Series of Inland Waters
**Institution:** DGFI-TUM (Deutsches Geodätisches Forschungsinstitut, TU München)
**Reference:** https://dahiti.dgfi.tum.de
**DAHITI ID:** 25 (Lake Tanganyika)
**Download script:** `scripts/download/download_dahiti_lake_level.py`

Satellite altimetry-derived lake surface elevation measured at a single
satellite ground track crossing point (lon 29.718, lat -6.054), in the
southern-central part of the lake. Since Lake Tanganyika is large and
well-mixed, this is representative of the whole lake's water level.

**Columns:**
| Column | Description | Unit |
|---|---|---|
| `date` | Observation datetime | UTC |
| `water_level_m` | Water surface elevation (WSE) above geoid | metres (~774 m) |
| `uncertainty_m` | Estimated measurement uncertainty | metres |
