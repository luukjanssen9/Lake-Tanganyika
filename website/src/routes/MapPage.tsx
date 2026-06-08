import { useEffect, useMemo, useState } from "react";
import ChartCard from "../components/ChartCard";
import ChartModal from "../components/ChartModal";
import FigureView from "../components/FigureView";
import LakeMap from "../components/LakeMap";
import PageHeader from "../components/PageHeader";
import { DATA_PATHS } from "../lib/constants";
import { CsvRow, loadCsv } from "../lib/dataLoader";
import { buildRelatedFeatureCharts } from "../lib/featureCharts";
import type { FeatureSelection } from "../lib/featureCharts";

const emptyRelatedData = {
  master: [] as CsvRow[],
  masterImputed: [] as CsvRow[],
  jrc: [] as CsvRow[],
};

export default function MapPage() {
  const [selection, setSelection] = useState<FeatureSelection | null>(null);
  const [data, setData] = useState(emptyRelatedData);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [activeCard, setActiveCard] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([loadCsv(DATA_PATHS.master), loadCsv(DATA_PATHS.masterImputed), loadCsv(DATA_PATHS.jrc)]).then(
      ([master, masterImputed, jrc]) => {
        if (!active) return;
        setData({
          master: master.data,
          masterImputed: masterImputed.data,
          jrc: jrc.data,
        });
        setWarnings([master.warning, masterImputed.warning, jrc.warning].filter(Boolean) as string[]);
      },
    );
    return () => {
      active = false;
    };
  }, []);

  const relatedCharts = useMemo(() => buildRelatedFeatureCharts(selection, data), [selection, data]);
  const active = relatedCharts.find((card) => card.id === activeCard);

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
                Related graphs are shown below the map using the available monthly project data matched by feature name.
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
          </div>
          {relatedCharts.length ? (
            <div className="chart-grid related-chart-grid">
              {relatedCharts.map((card) => (
                <ChartCard
                  key={card.id}
                  title={card.title}
                  subtitle={card.subtitle}
                  onOpen={() => setActiveCard(card.id)}
                >
                  <FigureView fig={card.figure} />
                </ChartCard>
              ))}
            </div>
          ) : (
            <p className="empty-state">No graph data is currently available for this selected feature.</p>
          )}
        </section>
      ) : null}

      {active ? (
        <ChartModal title={active.title} onClose={() => setActiveCard(null)}>
          <FigureView fig={active.figure} large />
        </ChartModal>
      ) : null}
    </>
  );
}
