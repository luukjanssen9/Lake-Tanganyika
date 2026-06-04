import { createReadStream } from "node:fs";
import { copyFile, mkdir, readdir, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const websiteRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(websiteRoot, "..");
const publicRoot = path.join(websiteRoot, "public");
const dataRoot = path.join(publicRoot, "data");
const imagesRoot = path.join(publicRoot, "images");

const manifest = [];
const warnings = [];

const csvExtensions = new Set([".csv"]);
const imageExtensions = new Set([".png", ".jpg", ".jpeg", ".webp"]);
const geoExtensions = new Set([".geojson", ".json"]);

function toPublicPath(absPath) {
  return path.relative(publicRoot, absPath).split(path.sep).join("/");
}

function toSourcePath(absPath) {
  return path.relative(repoRoot, absPath).split(path.sep).join("/");
}

function typeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (csvExtensions.has(ext)) return "csv";
  if (imageExtensions.has(ext)) return "image";
  if (ext === ".md") return "markdown";
  if (geoExtensions.has(ext)) return "geojson";
  return ext.replace(".", "") || "file";
}

async function ensureCleanPublicData() {
  await rm(dataRoot, { recursive: true, force: true });
  await rm(imagesRoot, { recursive: true, force: true });
  await mkdir(dataRoot, { recursive: true });
  await mkdir(imagesRoot, { recursive: true });
}

async function csvSummary(absPath) {
  const stream = createReadStream(absPath, { encoding: "utf8" });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  let columns = [];
  let rowCount = 0;
  let first = true;

  for await (const line of rl) {
    if (first) {
      columns = line.split(",").map((value) => value.trim());
      first = false;
      continue;
    }
    if (line.trim()) rowCount += 1;
  }

  return { rowCount, columns };
}

async function addManifestEntry(sourceAbs, destAbs) {
  const info = await stat(destAbs);
  const entry = {
    path: toPublicPath(destAbs),
    type: typeFor(destAbs),
    sourcePath: toSourcePath(sourceAbs),
    modifiedTime: info.mtime.toISOString(),
    sizeBytes: info.size,
  };

  if (entry.type === "csv") {
    Object.assign(entry, await csvSummary(destAbs));
  }

  manifest.push(entry);
}

async function copyOne(sourceRel, destRel) {
  const sourceAbs = path.join(repoRoot, sourceRel);
  const destAbs = path.join(publicRoot, destRel);

  try {
    await stat(sourceAbs);
  } catch {
    warnings.push(`Missing source: ${sourceRel}`);
    return;
  }

  await mkdir(path.dirname(destAbs), { recursive: true });
  await copyFile(sourceAbs, destAbs);
  await addManifestEntry(sourceAbs, destAbs);
}

async function copyMatching(sourceDirRel, destDirRel, predicate) {
  const sourceDirAbs = path.join(repoRoot, sourceDirRel);
  let entries = [];

  try {
    entries = await readdir(sourceDirAbs, { withFileTypes: true });
  } catch {
    warnings.push(`Missing directory: ${sourceDirRel}`);
    return;
  }

  await Promise.all(
    entries
      .filter((entry) => entry.isFile() && predicate(entry.name))
      .map((entry) => copyOne(path.join(sourceDirRel, entry.name), path.join(destDirRel, entry.name))),
  );
}

async function main() {
  await ensureCleanPublicData();

  await Promise.all([
    copyOne("data/outputs/master_dataset_monthly.csv", "data/processed/master_dataset_monthly.csv"),
    copyOne("data/outputs/master_dataset_inputed.csv", "data/processed/master_dataset_inputed.csv"),
    copyOne("basins/scripts/arima_imputed_output.csv", "data/processed/arima_imputed_output.csv"),
    copyOne("Luuk/lake_tanganyika_modeling_table.csv", "data/processed/lake_tanganyika_modeling_table.csv"),
    copyOne("data/outputs/output_manifest.csv", "data/processed/output_manifest.csv"),
    copyOne("data/outputs/dahiti/lake_tanganyika_water_level.csv", "data/processed/dahiti/lake_tanganyika_water_level.csv"),
    copyOne("Luuk/reports/model_comparison.csv", "data/predictions/model_comparison.csv"),
    copyOne("Luuk/reports/metrics_extended.csv", "data/predictions/metrics_extended.csv"),
    copyOne("Luuk/reports/baseline_predictions.csv", "data/predictions/baseline_predictions.csv"),
    copyOne("Luuk/reports/sarimax_predictions.csv", "data/predictions/sarimax_predictions.csv"),
    copyOne("Luuk/reports/xgboost_predictions.csv", "data/predictions/xgboost_predictions.csv"),
    copyOne("Luuk/reports/xgboost_diff_predictions.csv", "data/predictions/xgboost_diff_predictions.csv"),
    copyOne("Luuk/reports/xgboost_feature_importance.csv", "data/predictions/xgboost_feature_importance.csv"),
    copyOne("Luuk/reports/xgboost_diff_feature_importance.csv", "data/predictions/xgboost_diff_feature_importance.csv"),
    copyOne("static map/outputs/basins.geojson", "data/map/basins.geojson"),
    copyOne("static map/outputs/rivers.geojson", "data/map/rivers.geojson"),
    copyOne("static map/outputs/stations.geojson", "data/map/stations.geojson"),
    copyOne("data/README.md", "data/docs/data_README.md"),
    copyOne("merge_summary.md", "data/docs/merge_summary.md"),
    copyOne("Luuk/reports/data_catalog.md", "data/docs/data_catalog.md"),
    copyOne("Luuk/reports/data_lineage_and_dictionary.md", "data/docs/data_lineage_and_dictionary.md"),
    copyOne("Luuk/reports/missing_data_report.md", "data/docs/missing_data_report.md"),
  ]);

  await Promise.all([
    copyMatching("data/outputs/jrc", "data/processed/jrc", (name) => name.endsWith(".csv")),
    copyMatching("data/outputs/ndvi", "data/processed/ndvi", (name) => name.endsWith(".csv")),
    copyMatching("data/outputs/per_river", "data/processed/per_river", (name) => name.endsWith(".csv")),
    copyMatching("basins/maps", "images/maps", (name) => name.endsWith(".png")),
    copyMatching("basins/scripts/arima_plots", "images/arima_plots", (name) => name.endsWith(".png")),
  ]);

  manifest.sort((a, b) => a.path.localeCompare(b.path));
  const manifestPath = path.join(dataRoot, "manifest.json");
  await writeFile(
    manifestPath,
    JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        repositoryRoot: repoRoot,
        files: manifest,
        warnings,
      },
      null,
      2,
    ),
  );

  console.log(`Synced ${manifest.length} files into website/public.`);
  if (warnings.length) {
    console.warn(warnings.join("\n"));
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
