import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import PredictionComparison from "../components/PredictionComparison";
import StatCard from "../components/StatCard";
import { DATA_PATHS, HORIZONS, MODEL_LABELS } from "../lib/constants";
import { CsvRow, formatNumber, loadCsv, numberValue } from "../lib/dataLoader";

const modelKeys = ["persistence", "seasonal_naive", "sarimax", "xgboost", "xgboost_diff"];

const metricColumns = [
  { key: "model", label: "Model", kind: "model" },
  { key: "horizon_months", label: "Horizon", kind: "horizon" },
  { key: "n", label: "Test months", kind: "integer" },
  { key: "mae_m", label: "MAE (m)", kind: "meters" },
  { key: "rmse_m", label: "RMSE (m)", kind: "meters" },
  { key: "bias_m", label: "Bias (m)", kind: "meters" },
  { key: "skill_vs_pers", label: "Skill vs persistence", kind: "percent" },
  { key: "skill_vs_seasonal", label: "Skill vs seasonal", kind: "percent" },
];

type PredictionData = {
  metrics: CsvRow[];
  predictions: CsvRow[];
};

const emptyData: PredictionData = {
  metrics: [],
  predictions: [],
};

function bestRow(rows: CsvRow[], column: string, absolute = false) {
  return rows.reduce<CsvRow | null>((best, row) => {
    const current = numberValue(row, column);
    if (current === null) return best;
    const currentScore = absolute ? Math.abs(current) : current;
    const bestValue = best ? numberValue(best, column) : null;
    const bestScore = bestValue === null ? Number.POSITIVE_INFINITY : absolute ? Math.abs(bestValue) : bestValue;
    return currentScore < bestScore ? row : best;
  }, null);
}

function formatFixed(value: number, digits: number) {
  return new Intl.NumberFormat("en", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatMetricCell(row: CsvRow, column: (typeof metricColumns)[number]) {
  if (column.kind === "model") return MODEL_LABELS[row.model] || row.model || "n/a";
  if (column.kind === "horizon") return `${row.horizon_months} month`;

  const value = numberValue(row, column.key);
  if (value === null) return "n/a";
  if (column.kind === "integer") return formatNumber(value, 0);
  if (column.kind === "percent") return `${formatFixed(value * 100, 1)}%`;
  return formatFixed(value, 3);
}

export default function PredictionsPage() {
  const [data, setData] = useState<PredictionData>(emptyData);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [horizon, setHorizon] = useState(1);
  const [selectedModels, setSelectedModels] = useState(modelKeys);

  useEffect(() => {
    let active = true;
    Promise.all([
      loadCsv(DATA_PATHS.predictions.metricsExtended),
      loadCsv(DATA_PATHS.predictions.modelComparison),
      loadCsv(DATA_PATHS.predictions.baseline),
      loadCsv(DATA_PATHS.predictions.sarimax),
      loadCsv(DATA_PATHS.predictions.xgboost),
      loadCsv(DATA_PATHS.predictions.xgboostDiff),
    ]).then(([metrics, comparison, baseline, sarimax, xgboost, xgboostDiff]) => {
      if (!active) return;
      setData({
        metrics: metrics.data.length ? metrics.data : comparison.data,
        predictions: [...baseline.data, ...sarimax.data, ...xgboost.data, ...xgboostDiff.data],
      });
      setWarnings(
        [
          metrics.warning,
          comparison.warning,
          baseline.warning,
          sarimax.warning,
          xgboost.warning,
          xgboostDiff.warning,
        ].filter(Boolean) as string[],
      );
    });
    return () => {
      active = false;
    };
  }, []);

  const selectedMetrics = data.metrics.filter((row) => Number(row.horizon_months) === horizon);
  const bestMae = bestRow(selectedMetrics, "mae_m");
  const bestRmse = bestRow(selectedMetrics, "rmse_m");
  const bestBias = bestRow(selectedMetrics, "bias_m", true);
  const sampleSize = Math.max(...selectedMetrics.map((row) => numberValue(row, "n") || 0), 0);

  const toggleModel = (model: string) => {
    setSelectedModels((current) => (current.includes(model) ? current.filter((item) => item !== model) : [...current, model]));
  };

  return (
    <>
      <PageHeader
        eyebrow="Model prediction results"
        title="Forecast comparison by horizon"
        subtitle="Predictions are aligned by date and horizon as they are drawn, so models with different coverage can still be compared."
      />

      {warnings.length ? (
        <div className="warning-list">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}

      <section className="toolbar card">
        <div className="segmented" role="group" aria-label="Prediction horizon">
          {HORIZONS.map((item) => (
            <button key={item} type="button" className={horizon === item ? "active" : ""} onClick={() => setHorizon(item)}>
              {item} month
            </button>
          ))}
        </div>
        <div className="checkbox-row">
          {modelKeys.map((model) => (
            <label key={model} className="check-pill">
              <input type="checkbox" checked={selectedModels.includes(model)} onChange={() => toggleModel(model)} />
              {MODEL_LABELS[model]}
            </label>
          ))}
        </div>
      </section>

      <section className="stat-grid">
        <StatCard
          label="Best MAE"
          value={`${formatNumber(numberValue(bestMae || {}, "mae_m"))} m`}
          detail={bestMae ? MODEL_LABELS[bestMae.model] || bestMae.model : "No metric rows"}
        />
        <StatCard
          label="Best RMSE"
          value={`${formatNumber(numberValue(bestRmse || {}, "rmse_m"))} m`}
          detail={bestRmse ? MODEL_LABELS[bestRmse.model] || bestRmse.model : "No metric rows"}
        />
        <StatCard
          label="Lowest absolute bias"
          value={`${formatNumber(numberValue(bestBias || {}, "bias_m"))} m`}
          detail={bestBias ? MODEL_LABELS[bestBias.model] || bestBias.model : "No metric rows"}
        />
        <StatCard label="Largest sample size" value={String(sampleSize)} detail={`${horizon}-month horizon`} />
      </section>

      <PredictionComparison predictions={data.predictions} metrics={data.metrics} selectedModels={selectedModels} horizon={horizon} />

      <section className="card table-card">
        <div className="card-head">
          <h2>Metrics table</h2>
          <p>Lower MAE and RMSE are better. Skill values show improvement compared with the baseline models.</p>
        </div>
        <div className="table-scroll">
          <table className="data-table metric-table">
            <thead>
              <tr>
                {metricColumns.map((column) => (
                  <th key={column.key} className={column.kind === "model" ? undefined : "numeric-cell"}>
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {selectedMetrics.map((row) => (
                <tr key={`${row.model}-${row.horizon_months}`}>
                  {metricColumns.map((column) => (
                    <td key={column.key} className={column.kind === "model" ? undefined : "numeric-cell"}>
                      {formatMetricCell(row, column)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
