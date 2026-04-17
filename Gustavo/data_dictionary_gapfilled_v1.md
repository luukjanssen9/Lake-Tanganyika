# data_dictionary_gapfilled_v1

## Dataset overview

`river_month_model_table_gapfilled_v1.csv` is the current historical river-month working table for the Burundi rivers draining into Lake Tanganyika. Each row represents one river in one month. The release is intended for historical reconstruction and downstream modeling experiments on river water level; it is not a future forecasting dataset.

This table combines:

- observed river and local hydro-meteorological variables
- basin-based CHIRPS and ERA5-Land features
- static basin and SoilGrids features
- earlier legacy proxy topography/landcover features
- reconstruction metadata for the conservative `gapfilled_v1` water-level release

## File summary

- File path: `data/processed/imputation/river_month_model_table_gapfilled_v1.csv`
- Current shape: `4664` rows x `121` columns
- Grain: one row per `river`-`date` month
- Key index columns: `river`, `date`
- Time coverage: `1981-01-01` to `2024-12-01`
- Rivers in scope: `Buzimba`, `Jiji`, `Kaburantwa`, `Mpanda`, `Mulembwe`, `Mutimbuzi`, `Nyakagunda`, `Nyamagana`, `Nyengwe`, `Rusizi`

## Identifiers and time columns

| Column | Meaning | Source / origin | Important caution |
| --- | --- | --- | --- |
| `river` | River name / panel entity identifier. | Project river panel. | Use with `date` as the row key. |
| `date` | Monthly timestamp for the row. | Project panel time index. | Monthly data only; not daily. |
| `year` | Calendar year extracted from `date`. | Derived from `date`. | Convenience field only. |
| `month` | Calendar month number extracted from `date`. | Derived from `date`. | Convenience field only. |

## Water-level target and reconstruction columns

| Column | Meaning | Source / origin | Important caution |
| --- | --- | --- | --- |
| `water_level` | Legacy carried-through water-level column from the merged panel. | Upstream processing before `gapfilled_v1`. | Do not use as the final working target for this release. Prefer `water_level_final`. |
| `water_level_observed` | Originally observed monthly river water level. | Source hydro observations. | This is the evaluation truth column; previously imputed values are not treated as truth here. |
| `water_level_final` | Current working water-level series for this release. Observed values are preserved; selected missing rows are reconstructed. | `gapfilled_v1` release application step. | May still be missing where the policy left rows unresolved. |
| `water_level_filled_flag` | Whether the row was reconstructed in `gapfilled_v1`. | `gapfilled_v1` release application step. | `False` includes both observed rows and unresolved missing rows. |
| `water_level_fill_method` | Method used for a reconstructed row. Examples include `linear_interpolation`, `hybrid_lag_climate_donor`, `own_river_lag_regression`, `seasonal_local_level_smoother`. | Gap-fill policy application. | Blank on observed rows; `manual_review_pending` marks unresolved missing rows. |
| `water_level_fill_source` | Final target provenance: `observed`, `reconstructed`, or `unresolved_missing`. | Gap-fill policy application. | Use this column for filtering observed-only vs reconstructed analyses. |
| `water_level_fill_confidence` | Confidence class attached to the applied or proposed fill decision. Present values include `benchmark_supported`, `low_confidence_long_gap`, `benchmark_adjacent`, and `manual_review_pending`. | Policy tables used in `gapfilled_v1`. | `low_confidence_long_gap` should be treated cautiously; `manual_review_pending` rows remain missing. |

## Gap metadata and fill-policy metadata

| Column | Meaning | Source / origin | Important caution |
| --- | --- | --- | --- |
| `gap_id` | Identifier for the real missing water-level block associated with the row. | Real-gap inventory and fill-policy join. | Usually blank for rows that were never missing. |
| `gap_length_months` | Length of the corresponding real missing block in months. | Real-gap inventory. | Repeated across all rows inside the same missing block. |
| `gap_position_type` | Position of the missing block relative to observed data (`internal` in this release). | Real-gap inventory. | All gaps in this release were internal; no edge-gap fills were attempted. |
| `gap_start_date` | First month of the real missing block. | Real-gap inventory. | Blank for non-gap rows. |
| `gap_end_date` | Last month of the real missing block. | Real-gap inventory. | Blank for non-gap rows. |
| `policy_basis` | Short code describing why the current fill rule was chosen. | Approved fill-policy tables. | Useful for auditability, not usually as a model input. |
| `policy_note` | Human-readable explanation of the rule. | Approved fill-policy tables. | Documentation field; not a numeric feature. |
| `policy_table_source` | Policy table that supplied the rule for the row. | Approved fill-policy tables. | Helps distinguish short/medium-gap and long-gap policy provenance. |

## Observed and local hydro-meteorological variables

### Core hydro variables

- `runoff`
- `runoff_observed`

These are runoff fields carried into the merged panel from the observed hydrology workflow. They are not water-level reconstructions.

### Local observed temperature and precipitation

- `temp_max_observed`
- `temp_min_observed`
- `temp_mean_observed`
- `precip_observed`
- `temp_source`
- `precip_source`

These columns store the local observed or source-linked monthly weather variables used in earlier panel building. `temp_source` and `precip_source` document source provenance and should be treated as metadata rather than model targets.

### Earlier ERA5-based weather covariates already present in the merged panel

- `era5_grid`
- `era5_t2m_mean`
- `era5_t2m_min`
- `era5_t2m_max`
- `era5_tp_sum`
- `era5_u10_mean`
- `era5_v10_mean`
- `era5_d2m_mean`
- `era5_msl_mean`

These are legacy monthly ERA5 covariates from the earlier combined dataset. They are different from the newer basin-aggregated `era5_land_*` features below.

### Imputed weather helper columns

- `temp_max_imputed`
- `temp_min_imputed`
- `temp_mean_imputed`
- `precip_bias_factor`
- `precip_imputed`

These helper columns relate to earlier weather harmonization or imputation steps. They are retained for traceability and possible modeling use, but they are not part of the `gapfilled_v1` water-level reconstruction decision itself.

## Basin and HydroSHEDS-derived static columns

Columns:

- `basin_method`
- `basin_status`
- `basin_snap_rule`
- `basin_search_radius_m`
- `basin_local_max_fraction`
- `basin_snap_distance_m`
- `basin_pour_lon`
- `basin_pour_lat`
- `basin_pour_acc_cells`
- `basin_pour_upstream_area_km2`
- `basin_delineated_cell_count`
- `basin_touches_clip_edge`
- `basin_area_km2`
- `basin_area_vs_pour_area_gap_km2`
- `basin_review_source`

These columns describe the approved HydroSHEDS delineated basin attached to each river. They are static by river and therefore repeat across months. The most important practical fields are:

- `basin_area_km2`: delineated basin area used for basin-based aggregation
- `basin_pour_upstream_area_km2`: upstream area implied by the snapped pour point
- `basin_touches_clip_edge`: whether the delineated basin hit the raster clip edge
- `basin_review_source`: review file used to approve the basin geometry

Use caution with highly technical snap metadata such as `basin_snap_rule`, `basin_search_radius_m`, and `basin_local_max_fraction`: these are provenance fields rather than substantive hydrologic predictors.

## CHIRPS basin-month variables

| Column | Meaning | Source / origin | Important caution |
| --- | --- | --- | --- |
| `chirps_precip_mean_mm` | Basin-mean monthly CHIRPS precipitation in millimeters. | Basin aggregation of CHIRPS monthly rasters. | This is the primary basin rainfall feature. |
| `chirps_precip_volume_proxy_m3` | Area-scaled precipitation volume proxy derived from basin rainfall and basin area. | Basin aggregation of CHIRPS monthly rasters. | Proxy only; do not interpret as direct measured discharge. |
| `chirps_valid_area_fraction` | Fraction of basin area covered by valid CHIRPS raster intersection. | CHIRPS aggregation QA. | Check if using strict spatial-coverage filters. |
| `source_file` | CHIRPS monthly raster file used for the row. | CHIRPS aggregation provenance. | File-level provenance field, not a predictor by default. |

## ERA5-Land basin-month variables

| Column | Meaning | Source / origin | Important caution |
| --- | --- | --- | --- |
| `era5_valid_area_fraction` | Fraction of basin area covered by valid ERA5-Land aggregation cells. | ERA5-Land basin aggregation QA. | Important for `Rusizi`, where basin coverage is partial. |
| `era5_land_sp_mean_pa` | Basin-mean surface pressure. | ERA5-Land monthly basin aggregation. | Units are Pascals. |
| `era5_land_swvl1_mean_m3_m3` | Basin-mean volumetric soil water layer 1. | ERA5-Land monthly basin aggregation. | Static model users should keep units consistent across `swvl1-4`. |
| `era5_land_swvl2_mean_m3_m3` | Basin-mean volumetric soil water layer 2. | ERA5-Land monthly basin aggregation. | Same family as above. |
| `era5_land_swvl3_mean_m3_m3` | Basin-mean volumetric soil water layer 3. | ERA5-Land monthly basin aggregation. | Same family as above. |
| `era5_land_swvl4_mean_m3_m3` | Basin-mean volumetric soil water layer 4. | ERA5-Land monthly basin aggregation. | Same family as above. |
| `era5_land_ro_mean_m` | Basin-mean total runoff. | ERA5-Land monthly basin aggregation. | Stored in ERA5-Land runoff units, not observed streamflow. |
| `era5_land_ssro_mean_m` | Basin-mean sub-surface runoff. | ERA5-Land monthly basin aggregation. | Hydrologic predictor, not a measured river variable. |
| `era5_land_e_mean_m` | Basin-mean evaporation. | ERA5-Land monthly basin aggregation. | Keep sign convention consistent with ERA5-Land metadata. |
| `era5_land_pev_mean_m` | Basin-mean potential evaporation. | ERA5-Land monthly basin aggregation. | Keep sign convention consistent with ERA5-Land metadata. |

## SoilGrids and soil quality columns

### Soil query metadata

- `soilgrids_query_time_s`
- `soilgrids_query_lon`
- `soilgrids_query_lat`

These document the original SoilGrids point-query context for each river.

### Soil property-depth families

The following SoilGrids feature families are present and repeated across months for each river:

- `soilgrids_bdod_0_5cm_kg_per_dm3`, `soilgrids_bdod_5_15cm_kg_per_dm3`, `soilgrids_bdod_15_30cm_kg_per_dm3`, `soilgrids_bdod_30_60cm_kg_per_dm3`
- `soilgrids_cec_0_5cm_cmolc_per_kg`, `soilgrids_cec_5_15cm_cmolc_per_kg`, `soilgrids_cec_15_30cm_cmolc_per_kg`, `soilgrids_cec_30_60cm_cmolc_per_kg`
- `soilgrids_cfvo_0_5cm_cm3_per_100cm3`, `soilgrids_cfvo_5_15cm_cm3_per_100cm3`, `soilgrids_cfvo_15_30cm_cm3_per_100cm3`, `soilgrids_cfvo_30_60cm_cm3_per_100cm3`
- `soilgrids_clay_0_5cm_pct`, `soilgrids_clay_5_15cm_pct`, `soilgrids_clay_15_30cm_pct`, `soilgrids_clay_30_60cm_pct`
- `soilgrids_sand_0_5cm_pct`, `soilgrids_sand_5_15cm_pct`, `soilgrids_sand_15_30cm_pct`, `soilgrids_sand_30_60cm_pct`
- `soilgrids_silt_0_5cm_pct`, `soilgrids_silt_5_15cm_pct`, `soilgrids_silt_15_30cm_pct`, `soilgrids_silt_30_60cm_pct`
- `soilgrids_soc_0_5cm_g_per_kg`, `soilgrids_soc_5_15cm_g_per_kg`, `soilgrids_soc_15_30cm_g_per_kg`, `soilgrids_soc_30_60cm_g_per_kg`

### Soil completeness flags

| Column | Meaning | Source / origin | Important caution |
| --- | --- | --- | --- |
| `soil_missing_feature_value_count` | Count of missing SoilGrids feature values for the river. | SoilGrids parsing QA. | Repeated across months because soil is static by river. |
| `soil_all_missing_flag` | Whether all SoilGrids feature values are missing for the river. | SoilGrids parsing QA. | Important for `Rusizi`, where soil features are unavailable and flagged. |

## Legacy proxy topography and landcover columns

Columns:

- `legacy_proxy_lat`
- `legacy_proxy_lon`
- `legacy_proxy_morpho_at_gauge`
- `legacy_proxy_morpho_dominant_5km`
- `legacy_proxy_morpho_share_Imbo plains`
- `legacy_proxy_morpho_share_Mumirwa steep sl`
- `legacy_proxy_landcover_n_gridcodes_5km`
- `legacy_proxy_dominant_gridcode_5km`
- `legacy_proxy_dominant_gridcode_share_5km`
- `legacy_proxy_gridcode_10_share_5km`
- `legacy_proxy_gridcode_20_share_5km`
- `legacy_proxy_gridcode_30_share_5km`
- `legacy_proxy_gridcode_40_share_5km`
- `legacy_proxy_gridcode_50_share_5km`
- `legacy_proxy_gridcode_60_share_5km`
- `legacy_proxy_gridcode_80_share_5km`
- `legacy_proxy_proxy_area_km2`
- `legacy_proxy_topography_feature_method`

These columns come from an earlier approximate enrichment workflow built around gauge-centered proxy buffers rather than final upstream basins. They are kept because they may still be useful as auxiliary static features, but they should be treated as legacy proxy variables rather than basin-pure descriptors.

## Important limitations and usage cautions

- This is a monthly historical reconstruction dataset, not a future forecasting release.
- `water_level_final` is the current working target, but it is not fully complete: `1433` original missing water-level rows existed, `207` were reconstructed in `gapfilled_v1`, and `1226` remain unresolved.
- Some reconstructed rows are tagged `low_confidence_long_gap`; these should be treated more cautiously than `benchmark_supported` rows.
- Many very long internal gaps remain intentionally unresolved because they were outside the benchmark-supported or approved low-confidence policy ranges.
- `gap_position_type` is `internal` for this release; no edge-gap reconstruction was applied.
- `era5_valid_area_fraction` should be checked before strict basin-wide interpretation, especially for `Rusizi`, which has partial ERA5-Land basin coverage.
- `soil_all_missing_flag` should be checked before using soil features, especially for `Rusizi`, where soil attributes are unavailable.
- `legacy_proxy_*` columns are approximate 5 km gauge-buffer features from an older workflow and are not equivalent to HydroSHEDS basin-based attributes.
- `source_file`, `policy_basis`, `policy_note`, and `policy_table_source` are provenance/audit fields rather than substantive hydrologic measurements.

## Recommended usage

- Use `water_level_final` as the current working water-level series for historical reconstruction analyses.
- Use `water_level_observed` when you need observed-only truth for evaluation or sensitivity checks.
- Use `water_level_fill_source` to split analyses into observed-only, reconstructed, and unresolved subsets.
- Use `water_level_fill_confidence` to run sensitivity analyses such as:
  - observed-only
  - observed + `benchmark_supported`
  - observed + all reconstructed rows including `low_confidence_long_gap`
- Treat `manual_review_pending` rows as unresolved missing values; do not silently coerce them into completed targets.
- Consider filtering or sensitivity-checking rows with low `era5_valid_area_fraction`.
- Consider excluding or separately handling rows where `soil_all_missing_flag = True`.
- Treat `legacy_proxy_*` columns as optional auxiliary features rather than core basin descriptors.
