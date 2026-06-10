import { useEffect, useMemo, useState } from "react";
import ChartCard from "../components/ChartCard";
import PageHeader from "../components/PageHeader";
import PredictionComparison from "../components/PredictionComparison";
import RiverOutputView from "../components/RiverOutputView";
import StatCard from "../components/StatCard";
import { DATA_PATHS, HORIZONS, MODEL_LABELS } from "../lib/constants";
import { CsvRow, formatNumber, loadCsv, numberValue } from "../lib/dataLoader";
import {
  buildRiverOutputChart,
  emptyRiverOutputData,
  forecastMetrics,
  forecastRowsForRiver,
  riverOptionsFromOutputData,
} from "../lib/riverAnalysis";

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
  riverForecasts: CsvRow[];
};

const emptyData: PredictionData = {
  metrics: [],
  predictions: [],
  riverForecasts: [],
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
  const [showUncertainty, setShowUncertainty] = useState(true);
  const [riverForecastRiver, setRiverForecastRiver] = useState("Buzimba");
  const [riverForecastHorizon, setRiverForecastHorizon] = useState(1);

  useEffect(() => {
    let active = true;
    Promise.all([
      loadCsv(DATA_PATHS.predictions.metricsExtended),
      loadCsv(DATA_PATHS.predictions.modelComparison),
      loadCsv(DATA_PATHS.predictions.baseline),
      loadCsv(DATA_PATHS.predictions.sarimax),
      loadCsv(DATA_PATHS.predictions.xgboost),
      loadCsv(DATA_PATHS.predictions.xgboostDiff),
      loadCsv(DATA_PATHS.riverOutputs.forecasts),
    ]).then(([metrics, comparison, baseline, sarimax, xgboost, xgboostDiff, riverForecasts]) => {
      if (!active) return;
      setData({
        metrics: metrics.data.length ? metrics.data : comparison.data,
        predictions: [...baseline.data, ...sarimax.data, ...xgboost.data, ...xgboostDiff.data],
        riverForecasts: riverForecasts.data,
      });
      setWarnings(
        [
          metrics.warning,
          comparison.warning,
          baseline.warning,
          sarimax.warning,
          xgboost.warning,
          xgboostDiff.warning,
          riverForecasts.warning,
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
  const riverOutputData = useMemo(
    () => ({
      ...emptyRiverOutputData,
      forecasts: data.riverForecasts,
    }),
    [data.riverForecasts],
  );
  const riverOptions = useMemo(() => riverOptionsFromOutputData(riverOutputData), [riverOutputData]);
  const riverForecastRows = useMemo(
    () => forecastRowsForRiver(riverOutputData, riverForecastRiver, riverForecastHorizon),
    [riverOutputData, riverForecastRiver, riverForecastHorizon],
  );
  const riverMetrics = useMemo(() => forecastMetrics(riverForecastRows), [riverForecastRows]);
  const riverForecastChart = useMemo(
    () => buildRiverOutputChart("forecast", riverForecastRiver, riverOutputData, riverForecastHorizon),
    [riverOutputData, riverForecastRiver, riverForecastHorizon],
  );

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
          <label className="check-pill">
            <input type="checkbox" checked={showUncertainty} onChange={() => setShowUncertainty((value) => !value)} />
            Uncertainty band
          </label>
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

      <PredictionComparison predictions={data.predictions} metrics={data.metrics} selectedModels={selectedModels} horizon={horizon} showUncertainty={showUncertainty} />

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

      <section className="river-forecast-section">
        <div className="card-head">
          <div>
            <p className="eyebrow">River forecasts</p>
            <h2>River forecasts</h2>
            <p>River-level prediction forecasts are kept separate from the lake-level model comparison.</p>
          </div>
        </div>

        <section className="toolbar card">
          <label className="field">
            <span>River</span>
            <select value={riverForecastRiver} onChange={(event) => setRiverForecastRiver(event.target.value)}>
              {riverOptions.map((river) => (
                <option key={river} value={river}>
                  {river}
                </option>
              ))}
            </select>
          </label>
          <div className="segmented" role="group" aria-label="River forecast horizon">
            {HORIZONS.map((item) => (
              <button
                key={item}
                type="button"
                className={riverForecastHorizon === item ? "active" : ""}
                onClick={() => setRiverForecastHorizon(item)}
              >
                {item} month
              </button>
            ))}
          </div>
        </section>

        <section className="stat-grid river-forecast-stats">
          <StatCard label="MAE" value={formatNumber(riverMetrics.mae)} detail={`${riverMetrics.n} forecast rows`} />
          <StatCard label="RMSE" value={formatNumber(riverMetrics.rmse)} detail={`${riverForecastHorizon}-month horizon`} />
          <StatCard label="Bias" value={formatNumber(riverMetrics.bias)} detail="Mean error" />
        </section>

        <div className="chart-grid">
          <ChartCard
            title={riverForecastChart.title}
            subtitle={riverForecastChart.subtitle}
            className="chart-card--wide"
          >
            <RiverOutputView chart={riverForecastChart} height={430} />
          </ChartCard>
        </div>
      </section>
    </>
  );
}
