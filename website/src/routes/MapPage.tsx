import { useEffect, useMemo, useState } from "react";
import ChartCard from "../components/ChartCard";
import ChartModal from "../components/ChartModal";
import FigureView from "../components/FigureView";
import LakeMap from "../components/LakeMap";
import PageHeader from "../components/PageHeader";
import RiverOutputView from "../components/RiverOutputView";
import { DATA_PATHS } from "../lib/constants";
import { CsvRow, loadCsv } from "../lib/dataLoader";
import { buildRelatedFeatureCharts } from "../lib/featureCharts";
import type { FeatureSelection } from "../lib/featureCharts";
import { buildRiverOutputChartsForRiver, emptyRiverOutputData, hasRiverOutputData } from "../lib/riverAnalysis";
import type { RiverOutputChart, RiverOutputData } from "../lib/riverAnalysis";

const emptyRelatedData = {
  master: [] as CsvRow[],
  masterImputed: [] as CsvRow[],
  jrc: [] as CsvRow[],
  riverOutputs: emptyRiverOutputData as RiverOutputData,
};

export default function MapPage() {
  const [selection, setSelection] = useState<FeatureSelection | null>(null);
  const [data, setData] = useState(emptyRelatedData);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const [riverForecastHorizon, setRiverForecastHorizon] = useState(1);

  useEffect(() => {
    let active = true;
    Promise.all([
      loadCsv(DATA_PATHS.master),
      loadCsv(DATA_PATHS.masterImputed),
      loadCsv(DATA_PATHS.jrc),
      loadCsv(DATA_PATHS.riverOutputs.raw),
      loadCsv(DATA_PATHS.riverOutputs.imputation),
      loadCsv(DATA_PATHS.riverOutputs.forecasts),
    ]).then(
      ([master, masterImputed, jrc, riverRaw, riverImputation, riverForecasts]) => {
        if (!active) return;
        setData({
          master: master.data,
          masterImputed: masterImputed.data,
          jrc: jrc.data,
          riverOutputs: {
            raw: riverRaw.data,
            imputation: riverImputation.data,
            forecasts: riverForecasts.data,
          },
        });
        setWarnings(
          [
            master.warning,
            masterImputed.warning,
            jrc.warning,
            riverRaw.warning,
            riverImputation.warning,
            riverForecasts.warning,
          ].filter(Boolean) as string[],
        );
      },
    );
    return () => {
      active = false;
    };
  }, []);

  const relatedCharts = useMemo(() => {
    if (selection?.type === "river") return buildRiverOutputChartsForRiver(selection.name, data.riverOutputs, riverForecastHorizon);
    return buildRelatedFeatureCharts(selection, data);
  }, [selection, data, riverForecastHorizon]);
  const active = relatedCharts.find((card) => card.id === activeCard);
  const selectedRiverHasData = selection?.type === "river" ? hasRiverOutputData(selection.name, data.riverOutputs) : true;
  const emptyMessage =
    selection?.type === "river"
      ? "No river graph data is currently available for this selected river."
      : "No graph data is currently available for this selected feature.";

  return (
    <>
      <PageHeader
        eyebrow="GeoJSON layers"
        title="Lake Tanganyika basin and gauge map"
        subtitle="Basin polygons, river paths, and monitoring station points are loaded from the repository GeoJSON outputs."
      />

      <section className="map-page-grid">
        <div className="card map-card">
          <LakeMap selection={selection} onSelectionChange={setSelection} />
        </div>
        <aside className="card explanation-card">
          {selection ? (
            <>
              <p className="eyebrow">{selection.type === "basin" ? "Selected basin" : "Selected river"}</p>
              <h2>{selection.displayName}</h2>
              <p>
                Related graphs are shown below the map using the available project data matched by feature name.
              </p>
            </>
          ) : (
            <>
              <h2>Study area</h2>
              <p>
                This map shows the Lake Tanganyika study area, including contributing river basins, river paths, and available
                monitoring stations or gauges used in the analysis.
              </p>
              <p>Select a basin or river on the map to view related graphs.</p>
            </>
          )}
        </aside>
      </section>

      {warnings.length ? (
        <div className="warning-list">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}

      {selection ? (
        <section className="related-graphs-section">
          <div className="inline-head">
            <div>
              <h2>Related graphs</h2>
              <p className="muted">{selection.displayName}</p>
            </div>
            {selection.type === "river" ? (
              <div className="segmented compact" role="group" aria-label="River forecast horizon">
                {[1, 3, 6].map((item) => (
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
            ) : null}
          </div>
          {relatedCharts.length && selectedRiverHasData ? (
            <div className="chart-grid related-chart-grid">
              {relatedCharts.map((card) => (
                <ChartCard
                  key={card.id}
                  title={card.title}
                  subtitle={card.subtitle}
                  onOpen={() => setActiveCard(card.id)}
                >
                  {"description" in card ? (
                    <RiverOutputView chart={card as RiverOutputChart} />
                  ) : (
                    <FigureView fig={card.figure} />
                  )}
                </ChartCard>
              ))}
            </div>
          ) : (
            <p className="empty-state">{emptyMessage}</p>
          )}
        </section>
      ) : null}

      {active ? (
        <ChartModal title={active.title} onClose={() => setActiveCard(null)}>
          {"description" in active ? <RiverOutputView chart={active as RiverOutputChart} large /> : <FigureView fig={active.figure} large />}
        </ChartModal>
      ) : null}
    </>
  );
}
