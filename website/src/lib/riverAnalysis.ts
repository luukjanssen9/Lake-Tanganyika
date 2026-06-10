import { Figure, figure, lineTrace } from "./chartBuilders";
import { RIVERS } from "./constants";
import { CsvRow, namesMatch, normalizeName, numberValue } from "./dataLoader";

export type RiverOutputType = "raw" | "imputation" | "forecast";

export type RiverOutputData = {
  raw: CsvRow[];
  imputation: CsvRow[];
  forecasts: CsvRow[];
};

export type RiverOutputChart = {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  figure: Figure;
  fallbackImage?: string;
  hasData: boolean;
};

export type ForecastMetrics = {
  n: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
};

export const emptyRiverOutputData: RiverOutputData = {
  raw: [],
  imputation: [],
  forecasts: [],
};

export const riverOutputTypes: Array<{ value: RiverOutputType; label: string }> = [
  { value: "raw", label: "Raw water level, no imputation" },
  { value: "imputation", label: "Imputation uncertainty" },
  { value: "forecast", label: "Prediction forecasts" },
];

const descriptions: Record<RiverOutputType, string> = {
  raw: "This graph shows the original river water-level observations before imputation. Gaps indicate missing values in the raw record.",
  imputation: "This graph compares observed values with the model-imputed water-level estimate and its uncertainty interval.",
  forecast: "This graph compares the observed river value with the model prediction for the selected forecast horizon.",
};

function rowsForRiver(rows: CsvRow[], river: string) {
  return rows.filter((row) => namesMatch(row.river, river));
}

function sortByColumn(rows: CsvRow[], column: string) {
  return [...rows].sort((a, b) => String(a[column] || "").localeCompare(String(b[column] || "")));
}

function hasNumeric(rows: CsvRow[], keys: string[]) {
  return rows.some((row) => keys.some((key) => numberValue(row, key) !== null));
}

function canonicalRiver(rows: CsvRow[], river: string) {
  return rows.find((row) => namesMatch(row.river, river))?.river || RIVERS.find((item) => namesMatch(item, river)) || river;
}

function slugRiver(rows: CsvRow[], river: string) {
  const value = canonicalRiver(rows, river);
  return value || normalizeName(river).replace(/\s+/g, "_");
}

function imagePath(type: RiverOutputType, rows: CsvRow[], river: string, horizon = 1) {
  const name = slugRiver(rows, river);
  if (!name) return undefined;
  if (type === "raw") return `/data/river_graph_outputs/raw_no_imputation/${name}_raw_no_imputation.png`;
  if (type === "imputation") return `/data/river_graph_outputs/imputation_uncertainty/${name}_imputation_uncertainty.png`;
  return `/data/river_graph_outputs/prediction_forecasts/${name}_prediction_h${horizon}_months.png`;
}

function emptyFigure(title: string, yTitle: string) {
  return figure([], title, yTitle);
}

function imputationFigure(rows: CsvRow[], label: string) {
  const ordered = sortByColumn(rows, "date");
  const x = ordered.map((row) => row.date);
  const upper = ordered.map((row) => numberValue(row, "water_level_xgb_upper"));
  const lower = ordered.map((row) => numberValue(row, "water_level_xgb_lower"));

  return figure(
    [
      {
        type: "scatter",
        mode: "lines",
        name: "XGBoost upper",
        x,
        y: upper,
        line: { width: 0, color: "rgba(47,104,177,0)" },
        hoverinfo: "skip",
        showlegend: false,
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Uncertainty interval",
        x,
        y: lower,
        fill: "tonexty",
        fillcolor: "rgba(47,104,177,0.18)",
        line: { width: 0, color: "rgba(47,104,177,0)" },
        hovertemplate: "Uncertainty interval<br>Date: %{x}<extra></extra>",
      },
      lineTrace(ordered, "water_level_xgb_mean", "XGBoost imputed mean", { color: "#2f68b1" }),
      lineTrace(ordered, "water_level", "Observed water level", { color: "#172033" }),
    ],
    `Imputation uncertainty - ${label}`,
    "Water level",
  );
}

export function buildRiverOutputChart(type: RiverOutputType, river: string, data: RiverOutputData, horizon = 1): RiverOutputChart {
  if (type === "raw") {
    const rows = rowsForRiver(data.raw, river);
    const label = canonicalRiver(rows, river);
    const hasData = hasNumeric(rows, ["raw_water_level"]);
    return {
      id: "river-raw-water-level",
      title: `Raw water level without imputation - ${label}`,
      subtitle: "Original river observations before gap filling",
      description: descriptions.raw,
      figure: hasData
        ? figure(
            [lineTrace(rows, "raw_water_level", `${label} raw water level`, { color: "#207c7a" })],
            `Raw water level without imputation - ${label}`,
            "Water level",
          )
        : emptyFigure(`Raw water level without imputation - ${label}`, "Water level"),
      fallbackImage: imagePath(type, rows, river),
      hasData,
    };
  }

  if (type === "imputation") {
    const rows = rowsForRiver(data.imputation, river);
    const label = canonicalRiver(rows, river);
    const hasData = hasNumeric(rows, ["water_level", "water_level_xgb_mean", "water_level_xgb_lower", "water_level_xgb_upper"]);
    return {
      id: "river-imputation-uncertainty",
      title: `Imputation uncertainty - ${label}`,
      subtitle: "Observed values, XGBoost mean, and uncertainty interval",
      description: descriptions.imputation,
      figure: hasData ? imputationFigure(rows, label) : emptyFigure(`Imputation uncertainty - ${label}`, "Water level"),
      fallbackImage: imagePath(type, rows, river),
      hasData,
    };
  }

  const rows = rowsForRiver(data.forecasts, river).filter((row) => Number(row.horizon_months) === horizon);
  const label = canonicalRiver(rows.length ? rows : data.forecasts, river);
  const hasData = hasNumeric(rows, ["y_true", "y_pred"]);
  return {
    id: "river-prediction-forecast",
    title: `Prediction forecast - ${label}, ${horizon}-month horizon`,
    subtitle: "Observed vs predicted river values",
    description: descriptions.forecast,
    figure: hasData
      ? figure(
          [
            lineTrace(rows, "y_true", "Observed", { color: "#172033", xKey: "target_date" }),
            lineTrace(rows, "y_pred", "Predicted", { color: "#b24a62", xKey: "target_date", dash: "dot" }),
          ],
          `Prediction forecast - ${label}, ${horizon}-month horizon`,
          "Water level",
        )
      : emptyFigure(`Prediction forecast - ${label}, ${horizon}-month horizon`, "Water level"),
    fallbackImage: imagePath(type, rows.length ? rows : data.forecasts, river, horizon),
    hasData,
  };
}

export function buildRiverOutputChartsForRiver(river: string, data: RiverOutputData, horizon = 1) {
  return riverOutputTypes.map((item) => buildRiverOutputChart(item.value, river, data, horizon));
}

export function hasRiverOutputData(river: string, data: RiverOutputData) {
  return (
    hasNumeric(rowsForRiver(data.raw, river), ["raw_water_level"]) ||
    hasNumeric(rowsForRiver(data.imputation, river), ["water_level", "water_level_xgb_mean"]) ||
    hasNumeric(rowsForRiver(data.forecasts, river), ["y_true", "y_pred"])
  );
}

export function riverOptionsFromOutputData(data: RiverOutputData) {
  const values = [...data.raw, ...data.imputation, ...data.forecasts].map((row) => row.river).filter(Boolean);
  const fromData = Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
  return fromData.length ? fromData : RIVERS;
}

export function forecastRowsForRiver(data: RiverOutputData, river: string, horizon: number) {
  return rowsForRiver(data.forecasts, river).filter((row) => Number(row.horizon_months) === horizon);
}

export function forecastMetrics(rows: CsvRow[]): ForecastMetrics {
  const errors = rows
    .map((row) => {
      const explicit = numberValue(row, "error");
      if (explicit !== null) return explicit;
      const predicted = numberValue(row, "y_pred");
      const observed = numberValue(row, "y_true");
      return predicted !== null && observed !== null ? predicted - observed : null;
    })
    .filter((value): value is number => value !== null);

  if (!errors.length) return { n: 0, mae: null, rmse: null, bias: null };

  const mae = errors.reduce((sum, value) => sum + Math.abs(value), 0) / errors.length;
  const rmse = Math.sqrt(errors.reduce((sum, value) => sum + value ** 2, 0) / errors.length);
  const bias = errors.reduce((sum, value) => sum + value, 0) / errors.length;
  return { n: errors.length, mae, rmse, bias };
}
