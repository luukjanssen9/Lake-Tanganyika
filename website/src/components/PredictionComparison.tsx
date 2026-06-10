import Plot from "react-plotly.js";
import { MODEL_COLORS, MODEL_LABELS } from "../lib/constants";
import type { CsvRow } from "../lib/dataLoader";
import { monthDate, numberValue, sortByDate } from "../lib/dataLoader";
import { barTrace, figure } from "../lib/chartBuilders";

const plotConfig = { responsive: true, displaylogo: false };

// 95% normal interval multiplier, used for the residual (RMSE) based band.
const Z95 = 1.96;

function hexToRgba(hex: string, alpha: number) {
  const value = hex.replace("#", "");
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Build the two filled traces that draw an uncertainty band for one model.
// Uses the model's native prediction interval (y_lower / y_upper, currently
// SARIMAX only) when present, otherwise a constant +/- 1.96 * RMSE envelope
// derived from metrics_extended.csv.
function bandTraces(
  modelRows: CsvRow[],
  model: string,
  rmse: number | null,
): Trace[] {
  const x = modelRows.map(monthDate);
  const hasNative = modelRows.some((row) => numberValue(row, "y_lower") !== null && numberValue(row, "y_upper") !== null);

  let lower: Array<number | null>;
  let upper: Array<number | null>;
  if (hasNative) {
    lower = modelRows.map((row) => numberValue(row, "y_lower"));
    upper = modelRows.map((row) => numberValue(row, "y_upper"));
  } else if (rmse !== null) {
    lower = modelRows.map((row) => {
      const yPred = numberValue(row, "y_pred");
      return yPred === null ? null : yPred - Z95 * rmse;
    });
    upper = modelRows.map((row) => {
      const yPred = numberValue(row, "y_pred");
      return yPred === null ? null : yPred + Z95 * rmse;
    });
  } else {
    return [];
  }

  const color = MODEL_COLORS[model] || "#6e7787";
  const label = MODEL_LABELS[model] || model;
  const kind = hasNative ? "95% prediction interval" : "±1.96·RMSE band";
  // Upper bound first (invisible), then lower bound filling up to it.
  return [
    {
      type: "scatter",
      mode: "lines",
      name: `${label} band`,
      x,
      y: upper,
      line: { width: 0, color },
      showlegend: false,
      hoverinfo: "skip",
      connectgaps: false,
    },
    {
      type: "scatter",
      mode: "lines",
      name: `${label} (${kind})`,
      x,
      y: lower,
      line: { width: 0, color },
      fill: "tonexty",
      fillcolor: hexToRgba(color, 0.15),
      showlegend: false,
      hoverinfo: "skip",
      connectgaps: false,
    },
  ];
}

type Trace = Record<string, unknown>;

type PredictionComparisonProps = {
  predictions: CsvRow[];
  metrics: CsvRow[];
  selectedModels: string[];
  horizon: number;
  showUncertainty: boolean;
};

export default function PredictionComparison({ predictions, metrics, selectedModels, horizon, showUncertainty }: PredictionComparisonProps) {
  const rows = sortByDate(
    predictions.filter((row) => Number(row.horizon_months) === horizon && selectedModels.includes(row.model)),
  );

  const rmseByModel = new Map<string, number>();
  metrics
    .filter((row) => Number(row.horizon_months) === horizon)
    .forEach((row) => {
      const rmse = numberValue(row, "rmse_m");
      if (rmse !== null) rmseByModel.set(row.model, rmse);
    });
  const observedByDate = new Map<string, number>();
  rows.forEach((row) => {
    const yTrue = numberValue(row, "y_true");
    if (yTrue !== null) observedByDate.set(monthDate(row), yTrue);
  });

  const observedDates = Array.from(observedByDate.keys()).sort();
  // Uncertainty bands are drawn first so the prediction/observed lines sit on top.
  const uncertaintyTraces = showUncertainty
    ? selectedModels.flatMap((model) =>
        bandTraces(rows.filter((row) => row.model === model), model, rmseByModel.get(model) ?? null),
      )
    : [];
  const comparisonFigure = figure(
    [
      ...uncertaintyTraces,
      {
        type: "scatter",
        mode: "lines",
        name: "Observed",
        x: observedDates,
        y: observedDates.map((date) => observedByDate.get(date)),
        line: { color: MODEL_COLORS.observed, width: 3 },
        hovertemplate: "Observed<br>Date: %{x}<br>Water level: %{y:.3f} m<extra></extra>",
      },
      ...selectedModels.map((model) => {
        const modelRows = rows.filter((row) => row.model === model);
        return {
          type: "scatter",
          mode: "lines",
          name: MODEL_LABELS[model] || model,
          x: modelRows.map(monthDate),
          y: modelRows.map((row) => numberValue(row, "y_pred")),
          line: { color: MODEL_COLORS[model], width: 2.2 },
          hovertemplate: `${MODEL_LABELS[model] || model}<br>Date: %{x}<br>Prediction: %{y:.3f} m<extra></extra>`,
        };
      }),
    ],
    `Observed and predicted lake level, ${horizon}-month horizon`,
    "Lake level (m)",
  );

  const selectedMetrics = metrics.filter((row) => Number(row.horizon_months) === horizon);
  const labels = selectedMetrics.map((row) => MODEL_LABELS[row.model] || row.model);
  const metricFigure = figure(
    [
      barTrace(labels, selectedMetrics.map((row) => numberValue(row, "mae_m")), "MAE", "#207c7a"),
      barTrace(labels, selectedMetrics.map((row) => numberValue(row, "rmse_m")), "RMSE", "#b24a62"),
    ],
    `Model error metrics, ${horizon}-month horizon`,
    "Error (m)",
    { barmode: "group" },
  );

  const residualFigure = figure(
    selectedModels.map((model) => {
      const modelRows = rows.filter((row) => row.model === model);
      return {
        type: "scatter",
        mode: "lines",
        name: MODEL_LABELS[model] || model,
        x: modelRows.map(monthDate),
        y: modelRows.map((row) => {
          const yTrue = numberValue(row, "y_true");
          const yPred = numberValue(row, "y_pred");
          return yTrue === null || yPred === null ? null : yTrue - yPred;
        }),
        line: { color: MODEL_COLORS[model], width: 2.1 },
        hovertemplate: `${MODEL_LABELS[model] || model}<br>Date: %{x}<br>Residual: %{y:.3f} m<extra></extra>`,
      };
    }),
    `Residuals, ${horizon}-month horizon`,
    "Observed - predicted (m)",
    { shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: { color: "#8a96a6", width: 1 } }] },
  );

  const nativeModels = selectedModels.filter((model) =>
    rows.some((row) => row.model === model && numberValue(row, "y_lower") !== null && numberValue(row, "y_upper") !== null),
  );
  const bandCaption = nativeModels.length
    ? `Shaded bands show 95% prediction intervals for ${nativeModels
        .map((model) => MODEL_LABELS[model] || model)
        .join(", ")} (native model intervals); other models use a ±1.96·RMSE envelope from the test period.`
    : "Shaded bands show a ±1.96·RMSE envelope (~95%) computed from each model's test-period error.";

  return (
    <div className="prediction-grid">
      <section className="card chart-panel wide">
        <Plot data={comparisonFigure.data} layout={comparisonFigure.layout} config={plotConfig} useResizeHandler style={{ width: "100%", height: "440px" }} />
        {showUncertainty ? <p className="chart-caption">{bandCaption}</p> : null}
      </section>
      <section className="card chart-panel">
        <Plot data={metricFigure.data} layout={metricFigure.layout} config={plotConfig} useResizeHandler style={{ width: "100%", height: "360px" }} />
      </section>
      <section className="card chart-panel">
        <Plot data={residualFigure.data} layout={residualFigure.layout} config={plotConfig} useResizeHandler style={{ width: "100%", height: "360px" }} />
      </section>
    </div>
  );
}
