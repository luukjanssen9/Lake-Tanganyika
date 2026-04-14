# Data Directory

## Overview

This folder contains all data used in the Lake Tanganyika flood research project.
Raw input data lives in `raw/` and `era5/`. Processed outputs ready for analysis are in `outputs/`.

---

## raw/Lake Tanganyika Data/Donnees Hydro et Meteo Mensuelles_IGEBU/

**Source:** IGEBU (Institut Géographique du Burundi)
**Website:** https://www.igebu.bi
**Type:** In-situ measurements, monthly resolution
**Coverage:** Varies per station, roughly 1980s–2020s
**Access:** Data provided directly by IGEBU upon request. Not publicly available online.

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

**Citation:** IGEBU (Institut Géographique du Burundi). Hydrometeorological monthly data for the Lake Tanganyika catchment. Bujumbura, Burundi. Data obtained upon request.

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

**Source:** Copernicus Climate Data Store (CDS), European Centre for Medium-Range Weather Forecasts (ECMWF)
**Dataset:** ERA5 hourly data on single levels
**Website:** https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-timeseries
**Download script:** `scripts/download/era5/download_era5.py`

ERA5 reanalysis data at 0.25° grid resolution (~28 km), downloaded for 8 grid points
snapped to the nearest ERA5 grid node for each river/station location.
Full hourly time series from 1940 to present.

**Citation:**
> Hersbach, H., Bell, B., Berrisford, P., et al. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999–2049. https://doi.org/10.1002/qj.3803

**Variables downloaded:**
| Variable | Description | Unit |
|---|---|---|
| `t2m` | 2m air temperature | K |
| `tp` | Total precipitation | m (per hour) |
| `u10` | 10m U-component of wind | m/s |
| `v10` | 10m V-component of wind | m/s |
| `d2m` | 2m dewpoint temperature | K |
| `msl` | Mean sea level pressure | Pa |

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
- `csv/` — Hourly ERA5 data as CSV, one file per grid point (1940–2026, excluded from git)
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
| `imputed_output_from_mean/` | Earlier imputation outputs (mean-based method). Provided by project collaborators. |
| `dahiti/` | Lake Tanganyika satellite altimetry water level. See below. |
| `jrc/` | JRC Global Surface Water monthly water fraction per river. See below. |
| `ndvi/` | MODIS NDVI monthly vegetation index per river. See below. |

---

### outputs/dahiti/

**Source:** DAHITI — Database for Hydrological Time Series of Inland Waters
**Institution:** DGFI-TUM (Deutsches Geodätisches Forschungsinstitut, Technische Universität München)
**Website:** https://dahiti.dgfi.tum.de
**DAHITI ID:** 25 (Lake Tanganyika)
**Download script:** `scripts/download/download_dahiti_lake_level.py`

Satellite altimetry-derived lake surface elevation (~10-day intervals, 1992–present), measured at
a single satellite ground track crossing point (lon 29.718, lat -6.054) in the southern-central
part of the lake. Since Lake Tanganyika is large and well-mixed, this is representative of the
whole lake's water level.

**Citation:**
> Schwatke, C., Dettmering, D., Bosch, W., & Seitz, F. (2015). DAHITI – an innovative approach for estimating water level time series over inland waters using multi-mission satellite altimetry. *Hydrology and Earth System Sciences*, 19(10), 4345–4364. https://doi.org/10.5194/hess-19-4345-2015

**Columns:**
| Column | Description | Unit |
|---|---|---|
| `date` | Observation datetime | UTC |
| `water_level_m` | Water surface elevation (WSE) above geoid | metres (~774 m) |
| `uncertainty_m` | Estimated measurement uncertainty | metres |

---

### outputs/jrc/

**Source:** JRC Global Surface Water (GSW), European Commission Joint Research Centre
**Dataset:** JRC/GSW1_4/MonthlyHistory via Google Earth Engine
**Website:** https://global-surface-water.appspot.com/
**GEE catalogue:** https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_MonthlyHistory
**Download script:** `scripts/download/download_jrc_surface_water.py`

Monthly fraction of 30m Landsat pixels classified as water within a 2 km radius buffer
around each river mouth (1984–present). See `outputs/jrc/README.md` for a full assessment
of data quality and usefulness per river.

**Citation:**
> Pekel, J.-F., Cottam, A., Gorelick, N., & Belward, A. S. (2016). High-resolution mapping of global surface water and its long-term changes. *Nature*, 540, 418–422. https://doi.org/10.1038/nature20584

**Columns:**
| Column | Description | Unit |
|---|---|---|
| `river` | River name | — |
| `year` / `month` | Time period | — |
| `water_fraction` | Fraction of valid pixels classified as water | 0.0–1.0 |
| `water_pixels` | Number of 30m pixels classified as water | count |
| `total_pixels` | Total valid (non-cloud) pixels in the buffer | count |

---

### outputs/ndvi/

**Source:** NASA MODIS Terra — MOD13A1 Version 6.1
**Dataset:** MODIS/061/MOD13A1 via Google Earth Engine
**Website:** https://lpdaac.usgs.gov/products/mod13a1v061/
**GEE catalogue:** https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A1
**Download script:** `scripts/download/download_modis_ndvi.py`

Monthly mean NDVI (Normalised Difference Vegetation Index) extracted from 500m 16-day MODIS
composites at each river's ERA5 grid point (2000–present). NDVI ranges from -1 to +1, where
values above 0.6 indicate dense healthy vegetation, 0.3–0.6 moderate vegetation, and below
0.2 bare soil or water. High values indicate dense vegetation cover which affects catchment
runoff and flood risk.

**Note:** Nyengwe has 34 null values and suspect low values, likely because its ERA5 sampling
point falls on or near Lake Tanganyika rather than land. Buzimba and Mulembwe share identical
values as they use the same ERA5 grid point.

**Citation:**
> Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 500m SIN Grid V061. NASA EOSDIS Land Processes Distributed Active Archive Center (LP DAAC). https://doi.org/10.5067/MODIS/MOD13A1.061

**Columns:**
| Column | Description | Unit |
|---|---|---|
| `river` | River name | — |
| `year` / `month` | Time period | — |
| `ndvi` | Monthly mean NDVI | -1.0 to 1.0 |
