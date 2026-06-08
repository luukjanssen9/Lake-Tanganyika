import Plot from "react-plotly.js";
import type { Figure } from "../lib/chartBuilders";

const plotConfig = { responsive: true, displaylogo: false };

export default function FigureView({ fig, large = false }: { fig: Figure; large?: boolean }) {
  if (!fig.data.length) return <p className="empty-state">No data available for this chart.</p>;

  return (
    <Plot
      data={fig.data}
      layout={fig.layout}
      config={plotConfig}
      useResizeHandler
      style={{ width: "100%", height: large ? "610px" : "260px" }}
    />
  );
}
