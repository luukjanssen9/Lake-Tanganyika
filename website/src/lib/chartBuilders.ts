import type { CsvRow } from "./dataLoader";
import { monthDate, numberValue, sortByDate } from "./dataLoader";

type Trace = Record<string, unknown>;
type Layout = Record<string, unknown>;

export type Figure = {
  data: Trace[];
  layout: Layout;
};

const defaultPalette = ["#207c7a", "#2f68b1", "#b24a62", "#897032", "#6e7787", "#2f855a"];

export function lineTrace(
  rows: CsvRow[],
  yKey: string | string[],
  name: string,
  options: { color?: string; xKey?: string; hoverLabel?: string; dash?: string } = {},
): Trace {
  const ordered = sortByDate(rows);
  const yValues = ordered.map((row) => numberValue(row, yKey));
  const xValues = ordered.map((row) => (options.xKey ? row[options.xKey] : monthDate(row)));
  const riverValues = ordered.map((row) => row.river || "");

  return {
    type: "scatter",
    mode: "lines",
    name,
    x: xValues,
    y: yValues,
    customdata: riverValues,
    connectgaps: false,
    line: { color: options.color, width: 2.4, dash: options.dash },
    hovertemplate: `${options.hoverLabel || name}<br>Date: %{x}<br>River: %{customdata}<br>Value: %{y:.3f}<extra></extra>`,
  };
}

export function barTrace(labels: string[], values: Array<number | null>, name: string, color: string): Trace {
  return {
    type: "bar",
    x: labels,
    y: values,
    name,
    marker: { color },
    hovertemplate: "%{x}<br>%{y:.4f}<extra></extra>",
  };
}

export function figure(data: Trace[], title: string, yTitle: string, extraLayout: Layout = {}): Figure {
  return {
    data,
    layout: {
      title: { text: title, font: { size: 16 } },
      autosize: true,
      margin: { t: 44, r: 24, b: 48, l: 58 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#ffffff",
      hovermode: "x unified",
      font: { family: "Inter, ui-sans-serif, system-ui, sans-serif", color: "#172033" },
      legend: { orientation: "h", y: -0.22 },
      xaxis: {
        gridcolor: "#e9eef2",
        zerolinecolor: "#ccd8df",
        title: "",
        rangeslider: { visible: false },
      },
      yaxis: {
        gridcolor: "#e9eef2",
        zerolinecolor: "#ccd8df",
        title: yTitle,
      },
      ...extraLayout,
    },
  };
}

export function multiLineFigure(
  rows: CsvRow[],
  series: Array<{ key: string | string[]; name: string; color?: string; dash?: string }>,
  title: string,
  yTitle: string,
): Figure {
  return figure(
    series.map((item, index) =>
      lineTrace(rows, item.key, item.name, {
        color: item.color || defaultPalette[index % defaultPalette.length],
        dash: item.dash,
      }),
    ),
    title,
    yTitle,
  );
}
