import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import ChartCard from "../components/ChartCard";
import ChartModal from "../components/ChartModal";
import PageHeader from "../components/PageHeader";
import { DATA_PATHS, RIVERS } from "../lib/constants";
import { Figure, figure, lineTrace, multiLineFigure } from "../lib/chartBuilders";
import { assetUrl, CsvRow, loadCsv, monthDate, numberValue } from "../lib/dataLoader";

const plotConfig = { responsive: true, displaylogo: false };

const lakeVariables = [
  { key: "lake_level_m", label: "Lake level" },
  { key: "lake_level_m_roll_mean_12", label: "12-month mean" },
  { key: "lake_level_m_anom", label: "Anomaly" },
  { key: "lake_level_m_zscore", label: "Z-score" },
];

const riverLevelVariables = [
  { key: "water_level", label: "Observed level" },
  { key: "water_level_imputed_v2", label: "Imputed level" },
  { key: "wl_arima_imputed", label: "ARIMA-imputed level" },
];

const basinImages = [
  { path: "/images/maps/full-basin.png", label: "Full basin" },
  { path: "/images/maps/sub-basin.png", label: "Sub-basin" },
  { path: "/images/maps/ee-chart.png", label: "Earth Engine chart" },
];

type GraphData = {
  dahiti: CsvRow[];
  lakeModeling: CsvRow[];
  master: CsvRow[];
  masterImputed: CsvRow[];
  arima: CsvRow[];
  ndvi: CsvRow[];
  jrc: CsvRow[];
};

const emptyGraphData: GraphData = {
  dahiti: [],
  lakeModeling: [],
  master: [],
  masterImputed: [],
  arima: [],
  ndvi: [],
  jrc: [],
};

function SelectControl({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function FigureView({ fig, large = false }: { fig: Figure; large?: boolean }) {
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

function ImageView({ path, alt, large = false }: { path: string; alt: string; large?: boolean }) {
  return <img className={large ? "modal-image" : "chart-image"} src={assetUrl(path)} alt={alt} />;
}

export default function GraphsPage() {
  const [data, setData] = useState<GraphData>(emptyGraphData);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const [river, setRiver] = useState("Buzimba");
  const [riverVariable, setRiverVariable] = useState("water_level");
  const [lakeVariable, setLakeVariable] = useState("lake_level_m");
  const [precipRiver, setPrecipRiver] = useState("Buzimba");
  const [tempRiver, setTempRiver] = useState("Buzimba");
  const [ndviRiver, setNdviRiver] = useState("Buzimba");
  const [jrcRiver, setJrcRiver] = useState("Buzimba");
  const [arimaRiver, setArimaRiver] = useState("Buzimba");
  const [basinImage, setBasinImage] = useState(basinImages[0].path);

  useEffect(() => {
    let active = true;
    Promise.all([
      loadCsv(DATA_PATHS.dahiti),
      loadCsv(DATA_PATHS.lakeModeling),
      loadCsv(DATA_PATHS.master),
      loadCsv(DATA_PATHS.masterImputed),
      loadCsv(DATA_PATHS.arima),
      loadCsv(DATA_PATHS.ndvi),
      loadCsv(DATA_PATHS.jrc),
    ]).then(([dahiti, lakeModeling, master, masterImputed, arima, ndvi, jrc]) => {
      if (!active) return;
      setData({
        dahiti: dahiti.data,
        lakeModeling: lakeModeling.data,
        master: master.data,
        masterImputed: masterImputed.data,
        arima: arima.data,
        ndvi: ndvi.data,
        jrc: jrc.data,
      });
      setWarnings([dahiti.warning, lakeModeling.warning, master.warning, masterImputed.warning, arima.warning, ndvi.warning, jrc.warning].filter(Boolean) as string[]);
    });
    return () => {
      active = false;
    };
  }, []);

  const riverOptions = RIVERS.map((item) => ({ value: item, label: item }));

  const figures = useMemo(() => {
    const selectedLakeVariable = lakeVariables.find((item) => item.key === lakeVariable)!;
    const selectedRiverVariable = riverLevelVariables.find((item) => item.key === riverVariable)!;
    const dahiti = figure(
      [lineTrace(data.dahiti, "water_level_m", "DAHITI lake level", { color: "#207c7a", hoverLabel: "DAHITI" })],
      "Lake Tanganyika water level",
      "Water level (m)",
    );
    const lakeModeling = figure(
      [lineTrace(data.lakeModeling, selectedLakeVariable.key, selectedLakeVariable.label, { color: "#2f68b1" })],
      `Lake modeling table: ${selectedLakeVariable.label}`,
      selectedLakeVariable.key.includes("zscore") ? "Standard deviations" : "Lake level (m)",
    );
    const riverRows = data.arima.filter((row) => row.river === river);
    const riverLevel = figure(
      [lineTrace(riverRows, selectedRiverVariable.key, `${river} ${selectedRiverVariable.label}`, { color: "#b24a62" })],
      `${river} river water level`,
      "Water level (m)",
    );
    const runoff = figure(
      [lineTrace(data.master.filter((row) => row.river === river), "runoff", `${river} runoff`, { color: "#897032" })],
      `${river} runoff`,
      "Runoff",
    );
    const precipRows = data.masterImputed.filter((row) => row.river === precipRiver);
    const precipitation = multiLineFigure(
      precipRows,
      [
        { key: "precip_observed", name: "Observed precipitation", color: "#207c7a" },
        { key: "era5_tp_sum", name: "ERA5 precipitation", color: "#2f68b1" },
      ],
      `${precipRiver} precipitation`,
      "Monthly total (mm)",
    );
    const tempRows = data.masterImputed.filter((row) => row.river === tempRiver);
    const temperature = multiLineFigure(
      tempRows,
      [
        { key: "temp_max_observed", name: "Observed Tmax", color: "#b24a62" },
        { key: "temp_min_observed", name: "Observed Tmin", color: "#2f68b1" },
        { key: "era5_t2m_max", name: "ERA5 Tmax", color: "#d18b41", dash: "dot" },
        { key: "era5_t2m_min", name: "ERA5 Tmin", color: "#207c7a", dash: "dot" },
      ],
      `${tempRiver} temperature`,
      "Temperature (C)",
    );
    const ndviRows = data.ndvi
      .filter((row) => row.river === ndviRiver)
      .map((row) => ({ ...row, date: monthDate(row) }));
    const ndvi = figure([lineTrace(ndviRows, "ndvi", `${ndviRiver} NDVI`, { color: "#2f855a" })], `${ndviRiver} MODIS NDVI`, "NDVI");
    const jrcRows = data.jrc
      .filter((row) => row.river === jrcRiver)
      .map((row) => ({ ...row, date: monthDate(row) }));
    const jrc = figure(
      [lineTrace(jrcRows, "water_fraction", `${jrcRiver} water fraction`, { color: "#207c7a" })],
      `${jrcRiver} JRC surface water fraction`,
      "Water fraction",
    );
    const rowCounts = Object.entries({
      "DAHITI rows": data.dahiti.length,
      "Master rows": data.master.length,
      "Modeling rows": data.lakeModeling.length,
      "ARIMA rows": data.arima.length,
    });
    const overview = figure(
      [
        {
          type: "bar",
          x: rowCounts.map(([label]) => label),
          y: rowCounts.map(([, count]) => count),
          marker: { color: ["#207c7a", "#2f68b1", "#897032", "#b24a62"] },
          hovertemplate: "%{x}<br>%{y} rows<extra></extra>",
        },
      ],
      "Copied dataset row counts",
      "Rows",
    );

    return { dahiti, lakeModeling, riverLevel, runoff, precipitation, temperature, ndvi, jrc, overview };
  }, [data, lakeVariable, river, riverVariable, precipRiver, tempRiver, ndviRiver, jrcRiver]);

  const cards = [
    {
      id: "dahiti",
      title: "DAHITI lake level",
      subtitle: "Satellite altimetry series",
      content: (large = false) => <FigureView fig={figures.dahiti} large={large} />,
    },
    {
      id: "lake-modeling",
      title: "Lake modeling series",
      subtitle: "Level, rolling mean, anomaly, or z-score",
      controls: (
        <SelectControl
          label="Variable"
          value={lakeVariable}
          options={lakeVariables.map((item) => ({ value: item.key, label: item.label }))}
          onChange={setLakeVariable}
        />
      ),
      content: (large = false) => <FigureView fig={figures.lakeModeling} large={large} />,
    },
    {
      id: "river-level",
      title: "River water level",
      subtitle: "Observed, imputed, or ARIMA-imputed",
      controls: (
        <>
          <SelectControl label="River" value={river} options={riverOptions} onChange={setRiver} />
          <SelectControl
            label="Variable"
            value={riverVariable}
            options={riverLevelVariables.map((item) => ({ value: item.key, label: item.label }))}
            onChange={setRiverVariable}
          />
        </>
      ),
      content: (large = false) => <FigureView fig={figures.riverLevel} large={large} />,
    },
    {
      id: "runoff",
      title: "Runoff by river",
      subtitle: "Monthly runoff from the master dataset",
      controls: <SelectControl label="River" value={river} options={riverOptions} onChange={setRiver} />,
      content: (large = false) => <FigureView fig={figures.runoff} large={large} />,
    },
    {
      id: "precip",
      title: "Observed vs ERA5 precipitation",
      subtitle: "Monthly totals by river",
      controls: <SelectControl label="River" value={precipRiver} options={riverOptions} onChange={setPrecipRiver} />,
      content: (large = false) => <FigureView fig={figures.precipitation} large={large} />,
    },
    {
      id: "temperature",
      title: "Observed vs ERA5 temperature",
      subtitle: "Tmax and Tmin by river",
      controls: <SelectControl label="River" value={tempRiver} options={riverOptions} onChange={setTempRiver} />,
      content: (large = false) => <FigureView fig={figures.temperature} large={large} />,
    },
    {
      id: "ndvi",
      title: "MODIS NDVI",
      subtitle: "Monthly vegetation index",
      controls: <SelectControl label="River" value={ndviRiver} options={riverOptions} onChange={setNdviRiver} />,
      content: (large = false) => <FigureView fig={figures.ndvi} large={large} />,
    },
    {
      id: "jrc",
      title: "JRC surface water",
      subtitle: "Monthly water fraction near river mouths",
      controls: <SelectControl label="River" value={jrcRiver} options={riverOptions} onChange={setJrcRiver} />,
      content: (large = false) => <FigureView fig={figures.jrc} large={large} />,
    },
    {
      id: "missing",
      title: "ARIMA missingness overview",
      subtitle: "PNG output from the ARIMA workflow",
      content: (large = false) => <ImageView path="/images/arima_plots/missing_summary.png" alt="Missing data summary" large={large} />,
    },
    {
      id: "rmse",
      title: "ARIMA RMSE comparison",
      subtitle: "PNG output from the ARIMA workflow",
      content: (large = false) => <ImageView path="/images/arima_plots/rmse_comparison.png" alt="ARIMA RMSE comparison" large={large} />,
    },
    {
      id: "arima-river",
      title: "ARIMA per-river plot",
      subtitle: "Imputation chart selected by river",
      controls: <SelectControl label="River" value={arimaRiver} options={riverOptions} onChange={setArimaRiver} />,
      content: (large = false) => <ImageView path={`/images/arima_plots/${arimaRiver}_arima.png`} alt={`${arimaRiver} ARIMA plot`} large={large} />,
    },
    {
      id: "basin-images",
      title: "Basin overview images",
      subtitle: "Static map and Earth Engine outputs",
      controls: (
        <SelectControl
          label="Image"
          value={basinImage}
          options={basinImages.map((image) => ({ value: image.path, label: image.label }))}
          onChange={setBasinImage}
        />
      ),
      content: (large = false) => <ImageView path={basinImage} alt="Basin overview" large={large} />,
    },
    {
      id: "overview",
      title: "Website data sync overview",
      subtitle: "Row counts from key copied CSV files",
      content: (large = false) => <FigureView fig={figures.overview} large={large} />,
    },
  ];

  const active = cards.find((card) => card.id === activeCard);

  return (
    <>
      <PageHeader
        eyebrow="Interactive graphs"
        title="Lake, river, climate, vegetation, and imputation views"
        subtitle="Each card opens into a larger Plotly or image view. Data is read from the synced public CSV and PNG outputs."
      />
      {warnings.length ? (
        <div className="warning-list">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
      <section className="chart-grid">
        {cards.map((card) => (
          <ChartCard
            key={card.id}
            title={card.title}
            subtitle={card.subtitle}
            controls={card.controls}
            onOpen={() => setActiveCard(card.id)}
          >
            {card.content(false)}
          </ChartCard>
        ))}
      </section>
      {active ? (
        <ChartModal title={active.title} controls={active.controls} onClose={() => setActiveCard(null)}>
          {active.content(true)}
        </ChartModal>
      ) : null}
    </>
  );
}
