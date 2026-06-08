import { useEffect, useMemo, useState } from "react";
import { Database, ExternalLink } from "lucide-react";
import PageHeader from "../components/PageHeader";
import { DATA_PATHS } from "../lib/constants";
import { assetUrl, loadJson, Manifest, ManifestFile } from "../lib/dataLoader";

const emptyManifest: Manifest = {
  generatedAt: "",
  repositoryRoot: "",
  files: [],
  warnings: [],
};

const hiddenDatasetPaths = new Set(["data/processed/ndvi/ndvi_monthly.csv"]);

type ResearchDataCard = {
  name: string;
  description: string;
  source: string;
  usedFor: string;
  matchers: string[];
};

const researchDataCards: ResearchDataCard[] = [
  {
    name: "Lake Water Level Data",
    description: "Observed Lake Tanganyika water-level data used as the main target variable for prediction and time-series analysis.",
    source: "DAHITI water level dataset.",
    usedFor: "Model training, evaluation, and lake-level trend analysis.",
    matchers: ["data/processed/dahiti/lake_tanganyika_water_level.csv", "data/processed/lake_tanganyika_modeling_table.csv"],
  },
  {
    name: "River and Basin Data",
    description: "GeoJSON basin and river files used to map the contributing catchments and river network around Lake Tanganyika.",
    source: "Project static map outputs and processed geospatial files.",
    usedFor: "Map visualisation and spatial context.",
    matchers: ["data/map/basins.geojson", "data/map/rivers.geojson"],
  },
  {
    name: "Gauge / Station Data",
    description: "Monitoring station or gauge locations used to connect hydrological observations to the map and basin structure.",
    source: "Processed project station GeoJSON files.",
    usedFor: "Map visualisation and data interpretation.",
    matchers: ["data/map/stations.geojson"],
  },
  {
    name: "Climate Data",
    description:
      "Monthly climate variables such as precipitation, temperature, wind, dewpoint, and pressure used to explain hydrological variation and support prediction models.",
    source: "ERA5 reanalysis and processed project outputs.",
    usedFor: "Exploratory graphs and model features.",
    matchers: ["data/processed/master_dataset_monthly.csv", "data/processed/master_dataset_inputed.csv"],
  },
  {
    name: "Satellite / Remote Sensing Data",
    description: "Satellite-derived surface-water extent used to capture environmental and seasonal patterns.",
    source: "JRC Global Surface Water and processed project outputs.",
    usedFor: "Graphs, environmental analysis, and prediction features.",
    matchers: ["data/processed/jrc/jrc_surface_water_monthly.csv"],
  },
  {
    name: "Model Prediction Data",
    description:
      "Prediction outputs from different models, including baseline models, SARIMAX, XGBoost, and XGBoost-difference models.",
    source: "Project reports and model output CSV files.",
    usedFor: "Predictions page, model comparison, and forecast visualisation.",
    matchers: [
      "data/predictions/baseline_predictions.csv",
      "data/predictions/sarimax_predictions.csv",
      "data/predictions/xgboost_predictions.csv",
      "data/predictions/xgboost_diff_predictions.csv",
      "data/predictions/model_comparison.csv",
      "data/predictions/metrics_extended.csv",
    ],
  },
];

function findFiles(files: ManifestFile[], matchers: string[]) {
  return matchers
    .map((matcher) => files.find((file) => file.path === matcher && !hiddenDatasetPaths.has(file.path)))
    .filter((file): file is ManifestFile => Boolean(file));
}

function shortFileName(path: string) {
  return path.split("/").pop() || path;
}

export default function DataPage() {
  const [manifest, setManifest] = useState<Manifest>(emptyManifest);
  const [warning, setWarning] = useState("");

  useEffect(() => {
    let active = true;
    loadJson<Manifest>(DATA_PATHS.manifest, emptyManifest).then((result) => {
      if (!active) return;
      setManifest(result.data);
      setWarning(result.warning || "");
    });
    return () => {
      active = false;
    };
  }, []);

  const cards = useMemo(() => {
    const visibleFiles = manifest.files.filter((file) => !hiddenDatasetPaths.has(file.path));
    return researchDataCards.map((card) => ({
      ...card,
      files: findFiles(visibleFiles, card.matchers),
    }));
  }, [manifest.files]);

  return (
    <>
      <PageHeader
        eyebrow="Datasets and sources"
        title="Research Data & Datasets"
        subtitle="A simple overview of the project data used for mapping, analysis, graphing, and model prediction."
      />

      {warning ? <p className="warning">{warning}</p> : null}
      {manifest.warnings?.length ? (
        <div className="warning-list">
          {manifest.warnings.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </div>
      ) : null}

      <section className="dataset-card-list">
        {cards.map((card) => (
          <article className="research-data-card" key={card.name}>
            <div className="research-data-card__content">
              <h2>{card.name}</h2>
              <p>{card.description}</p>
              <dl>
                <div>
                  <dt>Source</dt>
                  <dd>{card.source}</dd>
                </div>
                <div>
                  <dt>Used for</dt>
                  <dd>{card.usedFor}</dd>
                </div>
              </dl>
              <div className="file-link-row">
                {card.files.length ? (
                  card.files.map((file) => (
                    <a key={file.path} href={assetUrl(`/${file.path}`)} target="_blank" rel="noreferrer">
                      <ExternalLink size={15} aria-hidden="true" />
                      {shortFileName(file.path)}
                    </a>
                  ))
                ) : (
                  <span className="friendly-note">Synced source file not available.</span>
                )}
              </div>
            </div>
            <span className="research-data-card__icon" aria-hidden="true">
              <Database size={26} />
            </span>
          </article>
        ))}
      </section>
    </>
  );
}
