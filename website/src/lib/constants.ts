export const RIVERS = [
  "Buzimba",
  "Jiji",
  "Kaburantwa",
  "Mpanda",
  "Mulembwe",
  "Mutimbuzi",
  "Nyakagunda",
  "Nyamagana",
  "Nyengwe",
  "Rusizi",
];

export const HORIZONS = [1, 3, 6];

export const MODEL_LABELS: Record<string, string> = {
  persistence: "Persistence",
  seasonal_naive: "Seasonal naive",
  sarimax: "SARIMAX",
  xgboost: "XGBoost",
  xgboost_diff: "XGBoost-diff",
};

export const MODEL_COLORS: Record<string, string> = {
  observed: "#172033",
  persistence: "#6e7787",
  seasonal_naive: "#9b6a25",
  sarimax: "#207c7a",
  xgboost: "#2f68b1",
  xgboost_diff: "#b24a62",
};

export const DATA_PATHS = {
  dahiti: "/data/processed/dahiti/lake_tanganyika_water_level.csv",
  lakeModeling: "/data/processed/lake_tanganyika_modeling_table.csv",
  master: "/data/processed/master_dataset_monthly.csv",
  masterImputed: "/data/processed/master_dataset_inputed.csv",
  jrc: "/data/processed/jrc/jrc_surface_water_monthly.csv",
  riverOutputs: {
    raw: "/data/river_graph_outputs/ALL_raw_no_imputation.csv",
    imputation: "/data/river_graph_outputs/ALL_imputation_uncertainty.csv",
    forecasts: "/data/river_graph_outputs/ALL_prediction_forecasts.csv",
  },
  manifest: "/data/manifest.json",
  predictions: {
    modelComparison: "/data/predictions/model_comparison.csv",
    metricsExtended: "/data/predictions/metrics_extended.csv",
    baseline: "/data/predictions/baseline_predictions.csv",
    sarimax: "/data/predictions/sarimax_predictions.csv",
    xgboost: "/data/predictions/xgboost_predictions.csv",
    xgboostDiff: "/data/predictions/xgboost_diff_predictions.csv",
    xgboostImportance: "/data/predictions/xgboost_feature_importance.csv",
    xgboostDiffImportance: "/data/predictions/xgboost_diff_feature_importance.csv",
  },
  map: {
    basins: "/data/map/basins.geojson",
    rivers: "/data/map/rivers.geojson",
    stations: "/data/map/stations.geojson",
  },
  docs: {
    dataReadme: "/data/docs/data_README.md",
    mergeSummary: "/data/docs/merge_summary.md",
    dataCatalog: "/data/docs/data_catalog.md",
    lineage: "/data/docs/data_lineage_and_dictionary.md",
    missing: "/data/docs/missing_data_report.md",
  },
};
