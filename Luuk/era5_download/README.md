# ERA5 Hourly Download — Lake Tanganyika

Downloads **ERA5 hourly single-level reanalysis** data (1940 – present) for the Lake Tanganyika catchment using the [Copernicus CDS timeseries dataset](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-timeseries).

One request is made per location covering the full date range, producing **one NetCDF and one CSV per location**.

## Downloaded locations

Locations are derived from the actual station coordinates in the project data, snapped to the nearest ERA5 0.25° grid point (~28 km resolution). All stations are in northern Burundi, draining into the northern basin of Lake Tanganyika.

| Folder / file | Lat | Lon | Stations / rivers covered |
|---|---|---|---|
| `grid_m4.25_29.50` | −4.25 | 29.50 | Nyanza Lac (IRAT), Nyengwe (Rimbo) |
| `grid_m4.00_29.50` | −4.00 | 29.50 | Basse-Mulembwe (Mutambara), Buzimba (Gatete), Dama (Mbuga), Mulembwe (Mutambara) |
| `grid_m4.00_29.75` | −4.00 | 29.75 | Jiji (Ndago) |
| `grid_m3.75_29.50` | −3.75 | 29.50 | Mpota (Tora) |
| `grid_m3.25_29.25` | −3.25 | 29.25 | Bujumbura (Aéroport), Imbo (SEMS), Mutimbuzi (Pont Aéroport), Rusizi (Gatumba) |
| `grid_m3.00_29.25` | −3.00 | 29.25 | Kaburantwa (Mission), Nyamagana (Murambi) |
| `grid_m3.00_29.50` | −3.00 | 29.50 | Rwegura, Mpanda (Gatura) |
| `grid_m2.75_29.00` | −2.75 | 29.00 | Mparambo, Nyakagunda (Musenyi) |

## Station coordinates and ERA5 grid mapping

Each station's exact coordinates and the ERA5 grid point it was snapped to (nearest 0.25° cell). Stations sharing a row in the ERA5 column are covered by the same downloaded file.

| Station | Type | Station lat | Station lon | ERA5 lat | ERA5 lon | ERA5 file |
|---|---|---|---|---|---|---|
| Nyanza Lac (IRAT) | temperature, water level | −4.32 | 29.62 | −4.25 | 29.50 | `grid_m4.25_29.50` |
| Nyengwe (Rimbo) | water level | −4.17 | 29.54 | −4.25 | 29.50 | `grid_m4.25_29.50` |
| Basse-Mulembwe (Mutambara) | water level | −4.00 | 29.44 | −4.00 | 29.50 | `grid_m4.00_29.50` |
| Mulembwe (Mutambara) | water level | −4.00 | 29.44 | −4.00 | 29.50 | `grid_m4.00_29.50` |
| Buzimba (Gatete) | water level | −4.05 | 29.48 | −4.00 | 29.50 | `grid_m4.00_29.50` |
| Dama (Mbuga) | water level | −3.95 | 29.42 | −4.00 | 29.50 | `grid_m4.00_29.50` |
| Jiji (Ndago) | water level | −3.92 | 29.64 | −4.00 | 29.75 | `grid_m4.00_29.75` |
| Mpota (Tora) | temperature, water level | −3.73 | 29.57 | −3.75 | 29.50 | `grid_m3.75_29.50` |
| Rusizi (Gatumba) | water level | −3.34 | 29.27 | −3.25 | 29.25 | `grid_m3.25_29.25` |
| Bujumbura (Aéroport) | temperature, water level | −3.32 | 29.32 | −3.25 | 29.25 | `grid_m3.25_29.25` |
| Mutimbuzi (Pont Aéroport) | water level | −3.32 | 29.33 | −3.25 | 29.25 | `grid_m3.25_29.25` |
| Imbo (SEMS) | temperature | −3.18 | 29.35 | −3.25 | 29.25 | `grid_m3.25_29.25` |
| Mpanda (Gatura) | water level | −3.12 | 29.40 | −3.00 | 29.50 | `grid_m3.00_29.50` |
| Kaburantwa (Mission) | water level | −2.99 | 29.22 | −3.00 | 29.25 | `grid_m3.00_29.25` |
| Rwegura | temperature | −2.92 | 29.52 | −3.00 | 29.50 | `grid_m3.00_29.50` |
| Nyamagana (Murambi) | water level | −2.90 | 29.13 | −3.00 | 29.25 | `grid_m3.00_29.25` |
| Mparambo | temperature | −2.83 | 29.08 | −2.75 | 29.00 | `grid_m2.75_29.00` |
| Nyakagunda (Musenyi) | water level | −2.76 | 29.08 | −2.75 | 29.00 | `grid_m2.75_29.00` |

## Variables

### Currently in the CSVs

All 8 CSV files contain the following columns, covering 1940-01-01 to 2026-04-02 at hourly resolution (756,096 rows each):

| CSV column | ERA5 variable | Relevance |
|---|---|---|
| `t2m` | `2m_temperature` | Extends / fills gaps in station temperature files |
| `tp` | `total_precipitation` | Extends / fills gaps in station precipitation files |
| `u10` | `10m_u_component_of_wind` | Wind-driven lake mixing and evaporation |
| `v10` | `10m_v_component_of_wind` | Wind-driven lake mixing and evaporation |
| `d2m` | `2m_dewpoint_temperature` | Humidity driver; with `t2m` gives relative humidity and evaporation rate |
| `msl` | `mean_sea_level_pressure` | Synoptic weather patterns that steer storm systems over the catchment |

### Variables tested but not available in the timeseries dataset

| ERA5 variable | Status | Notes |
|---|---|---|
| `total_column_water_vapour` | Not in timeseries subset | Available in full reanalysis but ~24 h download per variable for 87 years — impractical |
| `volumetric_soil_water_layer_1` | Not in timeseries subset | Same as above; antecedent soil saturation is a strong runoff predictor |
| `evaporation` | Not in timeseries subset | Not tested against full reanalysis |
| `surface_runoff` | Not in timeseries subset | Not tested against full reanalysis |
| `potential_evapotranspiration` | Not in timeseries subset | Not tested against full reanalysis |

## Spatial domain

Northern Burundi catchment, covering all project stations: **lat −2.75° to −4.25°, lon 29.00° to 29.75°**

## Setup

1. Register at <https://cds.climate.copernicus.eu/> and accept the ERA5 licence.

2. Install the CDS API client:
   ```bash
   pip install cdsapi
   ```

3. Create `~/.cdsapirc` with your personal access token (found at your profile page):
   ```
   url: https://cds.climate.copernicus.eu/api
   key: <your-personal-access-token>
   ```

## Usage

```bash
# Download all 8 locations, 1940 – present (one request per location, ~10 min total)
python era5_download/download_era5.py

# Re-download everything from scratch
python era5_download/download_era5.py --overwrite

# Convert NetCDF files to CSV
python era5_download/convert_to_csv.py
```

Output structure:
```
era5_download/
  raw/<location>/era5_<location>_1940_<year>.nc   (~18 MB per location)
  csv/era5_<location>_1940_<year>.csv              (~55 MB per location)
```

## Inspect downloaded files

```bash
python era5_download/inspect_era5.py
```

## Notes

- The `raw/` and `csv/` directories are excluded from git — regenerate them by running the scripts.
- Already-downloaded files are skipped automatically (unless `--overwrite` is passed).
- CDS processes requests asynchronously; each location takes ~1–2 minutes.
