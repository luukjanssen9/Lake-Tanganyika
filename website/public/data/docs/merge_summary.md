# Merge Summary

## Outputs

- Combined monthly master dataset: `outputs/master_dataset_monthly.csv` (4664 rows)
- Per-river monthly datasets: `outputs/per_river/*.csv` (10 files)
- Manifest: `outputs/output_manifest.csv`

## Merge Rules

- Water level panels were built from each river's minimum to maximum observed water-level month; no imputation was applied.
- `water_level` equals `water_level_observed`, and `runoff` equals `runoff_observed` because this build does not create filled or modeled series.
- River and station names were standardized by removing accents, normalizing case, collapsing spacing and punctuation, and applying explicit aliases such as `BASSE-MULEMBWE` -> `Mulembwe` and `MUREMBWE` -> `Mulembwe`.
- Observed climate sources were chosen per river by preferring stations that share the river's ERA5 grid from `era5_download/README.md`; if none existed on that grid, the nearest observed station by coordinates was used.
- ERA5 hourly temperature and dewpoint were converted from Kelvin to degrees Celsius, and ERA5 precipitation totals were converted from meters to millimeters after monthly aggregation.

## Assumptions And Gaps

- Runoff is only available in `Ruissellement.csv` for a subset of target rivers. Rivers without a mapped runoff column remain missing: Jiji, Nyakagunda, Nyamagana, Rusizi.
- Unmatched runoff columns that were left unused because they do not map confidently to the target river list: dama, kagunuzi, kanyosha, karonge, kirasa, mugere, mushara, ntahangwa, ruzibazi.
- The extra workbook `Data_RainfallBDI_Corrige_1981_2023.xlsx` was not needed because `les precipitations mensuelles.xlsx` already supplied the observed local monthly precipitation series used here.

## River Details

| River | Water-level range | Water-level rows | Temp source | Temp mode | Precip source | Precip mode | ERA5 grid | Missing water level months |
|---|---:|---:|---|---|---|---|---|---:|
| Buzimba | 1981-01-01 to 2013-12-01 | 344 | NYANZA LAC (IRAT) | nearest_fallback | NYANZA LAC (IRAT) | nearest_fallback | grid_m4.00_29.50 | 52 |
| Mutimbuzi | 1989-01-01 to 2024-11-01 | 130 | BUJUMBURA (Aeroport) | same_era5_grid | BUJUMBURA (Aeroport) | same_era5_grid | grid_m3.25_29.25 | 301 |
| Jiji | 1981-01-01 to 2024-12-01 | 524 | MPOTA (Tora) | nearest_fallback | MPOTA (Tora) | nearest_fallback | grid_m4.00_29.75 | 5 |
| Nyamagana | 1981-01-01 to 2024-12-01 | 336 | MPARAMBO | nearest_fallback | MPARAMBO | nearest_fallback | grid_m3.00_29.25 | 192 |
| Mpanda | 2008-12-01 to 2024-10-01 | 172 | RWEGURA | same_era5_grid | RWEGURA | same_era5_grid | grid_m3.00_29.50 | 20 |
| Nyakagunda | 1981-01-01 to 2024-12-01 | 301 | MPARAMBO | same_era5_grid | MPARAMBO | same_era5_grid | grid_m2.75_29.00 | 228 |
| Kaburantwa | 1982-08-01 to 2024-12-01 | 339 | MPARAMBO | nearest_fallback | MPARAMBO | nearest_fallback | grid_m3.00_29.25 | 170 |
| Mulembwe | 1981-08-01 to 2024-12-01 | 479 | MPOTA (Tora) | nearest_fallback | MPOTA (Tora) | nearest_fallback | grid_m4.00_29.50 | 46 |
| Nyengwe | 1981-01-01 to 2022-12-01 | 259 | NYANZA LAC (IRAT) | same_era5_grid | NYANZA LAC (IRAT) | same_era5_grid | grid_m4.25_29.50 | 252 |
| Rusizi | 1981-01-01 to 2024-12-01 | 361 | BUJUMBURA (Aeroport) | same_era5_grid | BUJUMBURA (Aeroport) | same_era5_grid | grid_m3.25_29.25 | 167 |

## Validation

- Combined dataset contains 4664 rows and one unique row per river-month.
- Each per-river dataset is a complete monthly sequence from that river's min to max observed water-level date.
- Each per-river dataset was validated as an exact filtered subset of the combined dataset.
- Observed precipitation source file: `Lake Tanganyika Data/Donnees Hydro et Meteo Mensuelles_IGEBU/les precipitations mensuelles.xlsx` with 2709 station-month rows after cleaning.
