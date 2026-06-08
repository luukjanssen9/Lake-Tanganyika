import { Figure, figure, lineTrace, multiLineFigure } from "./chartBuilders";
import { CsvRow, monthDate, namesMatch, numberValue } from "./dataLoader";

export type FeatureSelection = {
  type: "basin" | "river";
  name: string;
  displayName: string;
};

export type FeatureChartData = {
  master: CsvRow[];
  masterImputed: CsvRow[];
  jrc: CsvRow[];
};

export type RelatedFeatureChart = {
  id: string;
  title: string;
  subtitle: string;
  figure: Figure;
};

function rowsForFeature(rows: CsvRow[], featureName: string) {
  return rows.filter((row) => namesMatch(row.river, featureName));
}

function hasNumeric(rows: CsvRow[], keys: Array<string | string[]>) {
  return rows.some((row) => keys.some((key) => numberValue(row, key) !== null));
}

function addIfAvailable(cards: RelatedFeatureChart[], card: RelatedFeatureChart, rows: CsvRow[], keys: Array<string | string[]>) {
  if (rows.length && hasNumeric(rows, keys)) cards.push(card);
}

export function buildRelatedFeatureCharts(selection: FeatureSelection | null, data: FeatureChartData) {
  if (!selection) return [];

  const cards: RelatedFeatureChart[] = [];
  const masterRows = rowsForFeature(data.master, selection.name);
  const imputedRows = rowsForFeature(data.masterImputed, selection.name);
  const jrcRows = rowsForFeature(data.jrc, selection.name).map((row) => ({ ...row, date: monthDate(row) }));
  const label = selection.displayName || selection.name;

  if (selection.type === "basin") {
    addIfAvailable(
      cards,
      {
        id: "basin-precipitation",
        title: `${label} precipitation`,
        subtitle: "Observed and ERA5 monthly totals",
        figure: multiLineFigure(
          imputedRows,
          [
            { key: "precip_observed", name: "Observed precipitation", color: "#207c7a" },
            { key: "era5_tp_sum", name: "ERA5 precipitation", color: "#2f68b1" },
          ],
          `${label} precipitation`,
          "Monthly total (mm)",
        ),
      },
      imputedRows,
      ["precip_observed", "era5_tp_sum"],
    );

    addIfAvailable(
      cards,
      {
        id: "basin-temperature",
        title: `${label} temperature`,
        subtitle: "Observed and ERA5 monthly temperature",
        figure: multiLineFigure(
          imputedRows,
          [
            { key: "temp_max_observed", name: "Observed Tmax", color: "#b24a62" },
            { key: "temp_min_observed", name: "Observed Tmin", color: "#2f68b1" },
            { key: "era5_t2m_max", name: "ERA5 Tmax", color: "#d18b41", dash: "dot" },
            { key: "era5_t2m_min", name: "ERA5 Tmin", color: "#207c7a", dash: "dot" },
          ],
          `${label} temperature`,
          "Temperature (C)",
        ),
      },
      imputedRows,
      ["temp_max_observed", "temp_min_observed", "era5_t2m_max", "era5_t2m_min"],
    );

    addIfAvailable(
      cards,
      {
        id: "basin-surface-water",
        title: `${label} surface water extent`,
        subtitle: "JRC monthly water fraction",
        figure: figure(
          [lineTrace(jrcRows, "water_fraction", `${label} water fraction`, { color: "#207c7a" })],
          `${label} surface water extent`,
          "Water fraction",
        ),
      },
      jrcRows,
      ["water_fraction"],
    );

    return cards;
  }

  addIfAvailable(
    cards,
    {
      id: "river-runoff",
      title: `${label} runoff / discharge`,
      subtitle: "Monthly runoff from the master dataset",
      figure: figure(
        [lineTrace(masterRows, "runoff", `${label} runoff`, { color: "#897032" })],
        `${label} runoff / discharge`,
        "Runoff",
      ),
    },
    masterRows,
    ["runoff"],
  );

  addIfAvailable(
    cards,
    {
      id: "river-gauge-level",
      title: `${label} gauge water-level context`,
      subtitle: "Observed and imputed station series",
      figure: multiLineFigure(
        imputedRows,
        [
          { key: "water_level", name: "Observed level", color: "#172033" },
          { key: "water_level_imputed_v2", name: "Imputed level", color: "#b24a62", dash: "dot" },
        ],
        `${label} gauge water-level context`,
        "Water level (m)",
      ),
    },
    imputedRows,
    ["water_level", "water_level_imputed_v2"],
  );

  addIfAvailable(
    cards,
    {
      id: "river-precipitation",
      title: `${label} precipitation context`,
      subtitle: "Observed and ERA5 monthly totals",
      figure: multiLineFigure(
        imputedRows,
        [
          { key: "precip_observed", name: "Observed precipitation", color: "#207c7a" },
          { key: "era5_tp_sum", name: "ERA5 precipitation", color: "#2f68b1" },
        ],
        `${label} precipitation context`,
        "Monthly total (mm)",
      ),
    },
    imputedRows,
    ["precip_observed", "era5_tp_sum"],
  );

  addIfAvailable(
    cards,
    {
      id: "river-surface-water",
      title: `${label} surface water extent`,
      subtitle: "JRC monthly water fraction",
      figure: figure(
        [lineTrace(jrcRows, "water_fraction", `${label} water fraction`, { color: "#207c7a" })],
        `${label} surface water extent`,
        "Water fraction",
      ),
    },
    jrcRows,
    ["water_fraction"],
  );

  return cards;
}
