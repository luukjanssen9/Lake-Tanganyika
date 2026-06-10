import FigureView from "./FigureView";
import type { RiverOutputChart } from "../lib/riverAnalysis";
import { assetUrl } from "../lib/dataLoader";

export default function RiverOutputView({ chart, large = false, height }: { chart: RiverOutputChart; large?: boolean; height?: number }) {
  return (
    <div className="river-output-view">
      {chart.hasData ? (
        <FigureView fig={chart.figure} large={large} height={height} />
      ) : chart.fallbackImage ? (
        <img className={large ? "modal-image" : "chart-image"} src={assetUrl(chart.fallbackImage)} alt={chart.title} />
      ) : (
        <p className="empty-state">No river graph data is currently available for this selected river.</p>
      )}
      <p className="chart-caption">{chart.description}</p>
    </div>
  );
}
