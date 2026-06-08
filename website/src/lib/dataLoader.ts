import Papa from "papaparse";

export type CsvRow = Record<string, string>;

export type ManifestFile = {
  path: string;
  type: string;
  sourcePath: string;
  modifiedTime: string;
  sizeBytes: number;
  rowCount?: number;
  columns?: string[];
};

export type Manifest = {
  generatedAt: string;
  repositoryRoot: string;
  files: ManifestFile[];
  warnings: string[];
};

export type LoadResult<T> = {
  data: T;
  warning?: string;
};

const textCache = new Map<string, Promise<LoadResult<string>>>();
const csvCache = new Map<string, Promise<LoadResult<CsvRow[]>>>();
const jsonCache = new Map<string, Promise<LoadResult<unknown>>>();

export function assetUrl(path: string) {
  const base = import.meta.env.BASE_URL || "/";
  return `${base}${path.replace(/^\//, "")}`;
}

async function fetchText(path: string): Promise<LoadResult<string>> {
  if (!textCache.has(path)) {
    textCache.set(
      path,
      fetch(assetUrl(path))
        .then(async (response) => {
          if (!response.ok) {
            return { data: "", warning: `${path} is unavailable (${response.status})` };
          }
          return { data: await response.text() };
        })
        .catch((error) => ({ data: "", warning: `${path} could not be loaded: ${error.message}` })),
    );
  }
  return textCache.get(path)!;
}

export async function loadText(path: string) {
  return fetchText(path);
}

export async function loadCsv(path: string): Promise<LoadResult<CsvRow[]>> {
  if (!csvCache.has(path)) {
    csvCache.set(
      path,
      fetchText(path).then((result) => {
        if (result.warning) return { data: [], warning: result.warning };

        const parsed = Papa.parse<CsvRow>(result.data, {
          header: true,
          skipEmptyLines: true,
          transformHeader: (header) => header.trim(),
        });

        const warning = parsed.errors.length ? parsed.errors[0].message : undefined;
        return { data: parsed.data, warning };
      }),
    );
  }
  return csvCache.get(path)!;
}

export async function loadJson<T>(path: string, fallback: T): Promise<LoadResult<T>> {
  if (!jsonCache.has(path)) {
    jsonCache.set(
      path,
      fetchText(path).then((result) => {
        if (result.warning) return { data: fallback, warning: result.warning };
        try {
          return { data: JSON.parse(result.data) as T };
        } catch (error) {
          return { data: fallback, warning: `${path} contains invalid JSON: ${(error as Error).message}` };
        }
      }),
    );
  }
  return jsonCache.get(path)! as Promise<LoadResult<T>>;
}

export function numberValue(row: CsvRow, candidates: string | string[]) {
  const keys = Array.isArray(candidates) ? candidates : [candidates];
  for (const key of keys) {
    const value = row[key];
    if (value === undefined || value === null || value === "") continue;
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

export function textValue(row: CsvRow, candidates: string | string[]) {
  const keys = Array.isArray(candidates) ? candidates : [candidates];
  for (const key of keys) {
    const value = row[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return "";
}

export function monthDate(row: CsvRow) {
  if (row.date) return row.date.slice(0, 10);
  if (row.year && row.month) {
    return `${row.year}-${String(row.month).padStart(2, "0")}-01`;
  }
  return "";
}

export function uniqueValues(rows: CsvRow[], key: string) {
  return Array.from(new Set(rows.map((row) => row[key]).filter(Boolean))).sort((a, b) => a.localeCompare(b));
}

export function sortByDate<T extends CsvRow>(rows: T[]) {
  return [...rows].sort((a, b) => monthDate(a).localeCompare(monthDate(b)));
}

export function normalizeName(value: unknown) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/[^\p{L}\p{N}\s]/gu, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function namesMatch(left: unknown, right: unknown) {
  const a = normalizeName(left);
  const b = normalizeName(right);
  if (!a || !b) return false;
  return a === b || a.includes(b) || b.includes(a);
}

export function formatNumber(value: number | null | undefined, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return new Intl.NumberFormat("en", { maximumFractionDigits: digits }).format(value);
}

export function fileSizeLabel(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
