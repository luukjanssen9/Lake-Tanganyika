import Plot from "react-plotly.js";
import { MODEL_COLORS, MODEL_LABELS } from "../lib/constants";
import type { CsvRow } from "../lib/dataLoader";
import { monthDate, numberValue, sortByDate } from "../lib/dataLoader";
import { barTrace, figure } from "../lib/chartBuilders";

const plotConfig = { responsive: true, displaylogo: false };

type PredictionComparisonProps = {
  predictions: CsvRow[];
  metrics: CsvRow[];
  selectedModels: string[];
  horizon: number;
};

export default function PredictionComparison({ predictions, metrics, selectedModels, horizon }: PredictionComparisonProps) {
  const rows = sortByDate(
    predictions.filter((row) => Number(row.horizon_months) === horizon && selectedModels.includes(row.model)),
  );
  const observedByDate = new Map<string, number>();
  rows.forEach((row) => {
    const yTrue = numberValue(row, "y_true");
    if (yTrue !== null) observedByDate.set(monthDate(row), yTrue);
  });

  const observedDates = Array.from(observedByDate.keys()).sort();
  const comparisonFigure = figure(
    [
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

  return (
    <div className="prediction-grid">
      <section className="card chart-panel wide">
        <Plot data={comparisonFigure.data} layout={comparisonFigure.layout} config={plotConfig} useResizeHandler style={{ width: "100%", height: "440px" }} />
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
