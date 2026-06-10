import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import ChartCard from "../components/ChartCard";
import FigureView from "../components/FigureView";
import ChartModal from "../components/ChartModal";
import PageHeader from "../components/PageHeader";
import RiverOutputView from "../components/RiverOutputView";
import { DATA_PATHS, RIVERS } from "../lib/constants";
import { figure, lineTrace, multiLineFigure } from "../lib/chartBuilders";
import { assetUrl, CsvRow, loadCsv, monthDate } from "../lib/dataLoader";
import { buildRiverOutputChart, emptyRiverOutputData, riverOutputTypes } from "../lib/riverAnalysis";
import type { RiverOutputData, RiverOutputType } from "../lib/riverAnalysis";

const lakeVariables = [
  { key: "lake_level_m", label: "Lake level" },
  { key: "lake_level_m_roll_mean_12", label: "12-month mean" },
  { key: "lake_level_m_anom", label: "Anomaly" },
  { key: "lake_level_m_zscore", label: "Z-score" },
];

const basinImages = [
  { path: "/images/maps/full-basin.png", label: "Full basin" },
  { path: "/images/maps/sub-basin.png", label: "Sub-basin" },
];

const graphCategories = [
  { id: "lake", label: "Lake-level graphs" },
  { id: "climate", label: "Climate and hydrology graphs" },
  { id: "remote", label: "Remote sensing graphs" },
  { id: "river", label: "River analysis" },
  { id: "quality", label: "Data quality / processing graphs" },
] as const;

type GraphCategory = (typeof graphCategories)[number]["id"];

type GraphData = {
  dahiti: CsvRow[];
  lakeModeling: CsvRow[];
  master: CsvRow[];
  masterImputed: CsvRow[];
  jrc: CsvRow[];
  riverOutputs: RiverOutputData;
};

const emptyGraphData: GraphData = {
  dahiti: [],
  lakeModeling: [],
  master: [],
  masterImputed: [],
  jrc: [],
  riverOutputs: emptyRiverOutputData,
};

type GraphCardConfig = {
  id: string;
  title: string;
  subtitle: string;
  category: GraphCategory;
  className?: string;
  controls?: ReactNode;
  content: (large?: boolean) => ReactNode;
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

function ImageView({ path, alt, large = false }: { path: string; alt: string; large?: boolean }) {
  return <img className={large ? "modal-image" : "chart-image"} src={assetUrl(path)} alt={alt} />;
}

export default function GraphsPage() {
  const [data, setData] = useState<GraphData>(emptyGraphData);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<GraphCategory>("lake");
  const [lakeVariable, setLakeVariable] = useState("lake_level_m");
  const [river, setRiver] = useState("Buzimba");
  const [precipRiver, setPrecipRiver] = useState("Buzimba");
  const [tempRiver, setTempRiver] = useState("Buzimba");
  const [jrcRiver, setJrcRiver] = useState("Buzimba");
  const [riverAnalysisRiver, setRiverAnalysisRiver] = useState("Buzimba");
  const [riverOutputType, setRiverOutputType] = useState<RiverOutputType>("raw");
  const [riverForecastHorizon, setRiverForecastHorizon] = useState(1);
  const [basinImage, setBasinImage] = useState(basinImages[0].path);

  useEffect(() => {
    let active = true;
    Promise.all([
      loadCsv(DATA_PATHS.dahiti),
      loadCsv(DATA_PATHS.lakeModeling),
      loadCsv(DATA_PATHS.master),
      loadCsv(DATA_PATHS.masterImputed),
      loadCsv(DATA_PATHS.jrc),
      loadCsv(DATA_PATHS.riverOutputs.raw),
      loadCsv(DATA_PATHS.riverOutputs.imputation),
      loadCsv(DATA_PATHS.riverOutputs.forecasts),
    ]).then(([dahiti, lakeModeling, master, masterImputed, jrc, riverRaw, riverImputation, riverForecasts]) => {
      if (!active) return;
      setData({
        dahiti: dahiti.data,
        lakeModeling: lakeModeling.data,
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
          dahiti.warning,
          lakeModeling.warning,
          master.warning,
          masterImputed.warning,
          jrc.warning,
          riverRaw.warning,
          riverImputation.warning,
          riverForecasts.warning,
        ].filter(Boolean) as string[],
      );
    });
    return () => {
      active = false;
    };
  }, []);

  const riverOptions = RIVERS.map((item) => ({ value: item, label: item }));

  const figures = useMemo(() => {
    const selectedLakeVariable = lakeVariables.find((item) => item.key === lakeVariable)!;
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
      "Imputed master rows": data.masterImputed.length,
      "Modeling rows": data.lakeModeling.length,
      "JRC rows": data.jrc.length,
    });
    const overview = figure(
      [
        {
          type: "bar",
          x: rowCounts.map(([label]) => label),
          y: rowCounts.map(([, count]) => count),
          marker: { color: ["#207c7a", "#2f68b1", "#897032", "#b24a62", "#6e7787"] },
          hovertemplate: "%{x}<br>%{y} rows<extra></extra>",
        },
      ],
      "Copied dataset row counts",
      "Rows",
    );
    const riverAnalysis = buildRiverOutputChart(riverOutputType, riverAnalysisRiver, data.riverOutputs, riverForecastHorizon);

    return { dahiti, lakeModeling, runoff, precipitation, temperature, jrc, overview, riverAnalysis };
  }, [data, lakeVariable, river, precipRiver, tempRiver, jrcRiver, riverAnalysisRiver, riverOutputType, riverForecastHorizon]);

  const cards: GraphCardConfig[] = [
    {
      id: "dahiti",
      title: "DAHITI lake level",
      subtitle: "Satellite altimetry series",
      category: "lake",
      content: (large = false) => <FigureView fig={figures.dahiti} large={large} />,
    },
    {
      id: "lake-modeling",
      title: "Lake modeling series",
      subtitle: "Level, rolling mean, anomaly, or z-score",
      category: "lake",
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
      id: "runoff",
      title: "Runoff by river",
      subtitle: "Monthly runoff from the master dataset",
      category: "climate",
      controls: <SelectControl label="River" value={river} options={riverOptions} onChange={setRiver} />,
      content: (large = false) => <FigureView fig={figures.runoff} large={large} />,
    },
    {
      id: "precip",
      title: "Observed vs ERA5 precipitation",
      subtitle: "Monthly totals by river",
      category: "climate",
      controls: <SelectControl label="River" value={precipRiver} options={riverOptions} onChange={setPrecipRiver} />,
      content: (large = false) => <FigureView fig={figures.precipitation} large={large} />,
    },
    {
      id: "temperature",
      title: "Observed vs ERA5 temperature",
      subtitle: "Tmax and Tmin by river",
      category: "climate",
      controls: <SelectControl label="River" value={tempRiver} options={riverOptions} onChange={setTempRiver} />,
      content: (large = false) => <FigureView fig={figures.temperature} large={large} />,
    },
    {
      id: "jrc",
      title: "JRC surface water",
      subtitle: "Monthly water fraction near river mouths",
      category: "remote",
      controls: <SelectControl label="River" value={jrcRiver} options={riverOptions} onChange={setJrcRiver} />,
      content: (large = false) => <FigureView fig={figures.jrc} large={large} />,
    },
    {
      id: "basin-images",
      title: "Basin overview images",
      subtitle: "Static map outputs",
      category: "remote",
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
      id: "river-analysis",
      title: figures.riverAnalysis.title,
      subtitle: figures.riverAnalysis.subtitle,
      category: "river",
      className: "chart-card--wide",
      controls: (
        <>
          <SelectControl label="River" value={riverAnalysisRiver} options={riverOptions} onChange={setRiverAnalysisRiver} />
          <SelectControl
            label="Output type"
            value={riverOutputType}
            options={riverOutputTypes.map((item) => ({ value: item.value, label: item.label }))}
            onChange={(value) => setRiverOutputType(value as RiverOutputType)}
          />
          {riverOutputType === "forecast" ? (
            <SelectControl
              label="Horizon"
              value={String(riverForecastHorizon)}
              options={[1, 3, 6].map((item) => ({ value: String(item), label: `${item} month` }))}
              onChange={(value) => setRiverForecastHorizon(Number(value))}
            />
          ) : null}
        </>
      ),
      content: (large = false) => <RiverOutputView chart={figures.riverAnalysis} large={large} height={large ? 610 : 430} />,
    },
    {
      id: "overview",
      title: "Website data sync overview",
      subtitle: "Row counts from key copied CSV files",
      category: "quality",
      content: (large = false) => <FigureView fig={figures.overview} large={large} />,
    },
  ];

  const availableCategories = graphCategories.filter((category) => cards.some((card) => card.category === category.id));
  const visibleCards = cards.filter((card) => card.category === activeCategory);
  const active = cards.find((card) => card.id === activeCard);

  return (
    <>
      <PageHeader
        eyebrow="Interactive graphs"
        title="Lake, climate, remote-sensing, and processing views"
        subtitle="Choose a category to browse focused groups of Plotly graphs and supporting images. Each card opens into a larger detail view."
      />
      {warnings.length ? (
        <div className="warning-list">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
      <div className="graph-category-tabs segmented" aria-label="Graph categories">
        {availableCategories.map((category) => (
          <button
            key={category.id}
            type="button"
            className={activeCategory === category.id ? "active" : undefined}
            onClick={() => setActiveCategory(category.id)}
          >
            {category.label}
          </button>
        ))}
      </div>
      <section className="chart-grid">
        {visibleCards.map((card) => (
          <ChartCard
            key={card.id}
            title={card.title}
            subtitle={card.subtitle}
            className={card.className}
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
