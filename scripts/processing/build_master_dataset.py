#!/usr/bin/env python3
from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent.parent  # project root
RAW_DIR = ROOT / "data" / "raw" / "Lake Tanganyika Data"
HYDRO_METEO_DIR = RAW_DIR / "Donnees Hydro et Meteo Mensuelles_IGEBU"
NEW_DATA_DIR = next(RAW_DIR.glob("*nouvelles*"), None) if RAW_DIR.exists() else None
ERA5_DIR = ROOT / "data" / "era5" / "csv"
OUTPUT_DIR = ROOT / "data" / "outputs"
PER_RIVER_DIR = OUTPUT_DIR / "per_river"
SUMMARY_PATH = ROOT / "merge_summary.md"
MANIFEST_PATH = OUTPUT_DIR / "output_manifest.csv"

TARGET_RIVERS = [
    "Buzimba",
    "Mutimbuzi",
    "Jiji",
    "Nyamagana",
    "Mpanda",
    "Nyakagunda",
    "Kaburantwa",
    "Mulembwe",
    "Nyengwe",
    "Rusizi",
]

ERA5_RIVER_GRID = {
    "Nyengwe": "grid_m4.25_29.50",
    "Buzimba": "grid_m4.00_29.50",
    "Jiji": "grid_m4.00_29.75",
    "Mulembwe": "grid_m4.00_29.50",
    "Mutimbuzi": "grid_m3.25_29.25",
    "Rusizi": "grid_m3.25_29.25",
    "Mpanda": "grid_m3.00_29.50",
    "Kaburantwa": "grid_m3.00_29.25",
    "Nyamagana": "grid_m3.00_29.25",
    "Nyakagunda": "grid_m2.75_29.00",
}

WATER_LEVEL_PATTERNS = {
    "Buzimba": "*Buzimba.xlsx",
    "Mutimbuzi": "*Mutimbuzi.xlsx",
    "Jiji": "*Jiji.xlsx",
    "Nyamagana": "*Nyamagana.xlsx",
    "Mpanda": "*Mpanda.xlsx",
    "Nyakagunda": "*Nyakagunda.xlsx",
    "Kaburantwa": "*Kaburantwa.xlsx",
    "Mulembwe": "*Mulembwe.xlsx",
    "Nyengwe": "*Nyengwe.xlsx",
    "Rusizi": "*RUSIZI.xlsx",
}

CLIMATE_STATION_GRID = {
    "bujumbura aeroport": "grid_m3.25_29.25",
    "imbo sems": "grid_m3.25_29.25",
    "mparambo": "grid_m2.75_29.00",
    "mpota tora": "grid_m3.75_29.50",
    "nyanza lac irat": "grid_m4.25_29.50",
    "rwegura": "grid_m3.00_29.50",
}

RIVER_ALIASES = {
    "buzimba": "Buzimba",
    "buzimba gatete": "Buzimba",
    "jiji": "Jiji",
    "jiji ndago": "Jiji",
    "kaburantwa": "Kaburantwa",
    "kaburantwa mission": "Kaburantwa",
    "mpanda": "Mpanda",
    "mpanda gatura": "Mpanda",
    "mulembwe": "Mulembwe",
    "mulembwe mutambara": "Mulembwe",
    "basse mulembwe": "Mulembwe",
    "basse mulembwe mutambara": "Mulembwe",
    "murembwe": "Mulembwe",
    "mutimbuzi": "Mutimbuzi",
    "mutimbuzi pont aeroport": "Mutimbuzi",
    "nyakagunda": "Nyakagunda",
    "nyakagunda musenyi": "Nyakagunda",
    "nyamagana": "Nyamagana",
    "nyamagana murambi": "Nyamagana",
    "nyengwe": "Nyengwe",
    "nyengwe rimbo": "Nyengwe",
    "rusizi": "Rusizi",
    "rusizi gatumba": "Rusizi",
}


def log(message: str) -> None:
    print(message, flush=True)


def strip_accents(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = strip_accents(str(value)).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_column_name(value: object) -> str:
    text = normalize_text(value)
    return text.replace(" ", "_")


def first_non_null(series: pd.Series) -> object:
    non_null = series.dropna()
    return non_null.iloc[0] if not non_null.empty else pd.NA


def find_one(base_dir: Path, pattern: str) -> Path:
    matches = sorted(base_dir.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected exactly one match for {pattern!r}, found {len(matches)}")
    return matches[0]


def detect_header_row(path: Path, sheet_name: str | int = 0, max_rows: int = 8) -> int:
    sample = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=max_rows)
    best_row = 0
    best_score = -1
    keyword_groups = [
        {"year", "yy", "annee"},
        {"month", "mm", "mois"},
        {"station", "station name", "name"},
        {"haut", "temp", "precip", "total"},
    ]

    for row_index, row in sample.iterrows():
        cells = [normalize_text(cell) for cell in row.tolist() if pd.notna(cell)]
        score = 0
        for keywords in keyword_groups:
            if any(any(keyword in cell for keyword in keywords) for cell in cells):
                score += 1
        if score > best_score:
            best_row = int(row_index)
            best_score = score

    return best_row


def read_excel_detected(path: Path) -> tuple[pd.DataFrame, int, str]:
    workbook = pd.ExcelFile(path)
    sheet_name = workbook.sheet_names[0]
    header_row = detect_header_row(path, sheet_name=sheet_name)
    dataframe = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    dataframe = dataframe.dropna(how="all").copy()
    dataframe.columns = [normalize_column_name(column) for column in dataframe.columns]
    return dataframe, header_row, str(sheet_name)


def locate_column(
    dataframe: pd.DataFrame,
    *,
    exact: set[str] | None = None,
    contains: list[str] | None = None,
) -> str:
    exact = exact or set()
    contains = contains or []
    for column in dataframe.columns:
        if column in exact:
            return column
    for column in dataframe.columns:
        if all(token in column for token in contains):
            return column
    raise KeyError(f"Could not locate a column with exact={exact} contains={contains}")


def build_monthly_date(dataframe: pd.DataFrame, year_column: str, month_column: str) -> pd.DataFrame:
    working = dataframe.copy()
    working["year"] = pd.to_numeric(working[year_column], errors="coerce")
    working["month"] = pd.to_numeric(working[month_column], errors="coerce")
    working = working[working["year"].notna() & working["month"].notna()].copy()
    working["year"] = working["year"].astype(int)
    working["month"] = working["month"].astype(int)
    working = working[working["month"].between(1, 12)].copy()
    working["date"] = pd.to_datetime(
        {"year": working["year"], "month": working["month"], "day": 1},
        errors="coerce",
    )
    working = working[working["date"].notna()].copy()
    return working


def canonicalize_river_name(value: object) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    if normalized in RIVER_ALIASES:
        return RIVER_ALIASES[normalized]
    for alias, river in RIVER_ALIASES.items():
        if normalized == alias or normalized.endswith(f" {alias}") or alias in normalized:
            return river
    return None


def write_dataframe(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def load_water_levels() -> tuple[pd.DataFrame, dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    panels: list[pd.DataFrame] = []
    river_meta: dict[str, dict[str, object]] = {}
    summary_meta: dict[str, dict[str, object]] = {}

    for river in TARGET_RIVERS:
        path = find_one(HYDRO_METEO_DIR, WATER_LEVEL_PATTERNS[river])
        raw, header_row, sheet_name = read_excel_detected(path)
        year_column = locate_column(raw, exact={"year", "yy"})
        month_column = locate_column(raw, exact={"month", "mm"})
        value_column = next(column for column in raw.columns if "haut" in column)
        station_column = locate_column(raw, exact={"station_name", "name"})
        lat_column = locate_column(raw, exact={"lat"})
        lon_column = locate_column(raw, exact={"lon"})

        cleaned = build_monthly_date(raw, year_column, month_column)
        cleaned["station_name_raw"] = cleaned[station_column].astype(str).str.strip()
        cleaned["river_from_station"] = cleaned["station_name_raw"].map(canonicalize_river_name)
        cleaned["water_level_observed"] = pd.to_numeric(cleaned[value_column], errors="coerce")

        unmatched_names = sorted(
            {
                name
                for name, mapped in cleaned[["station_name_raw", "river_from_station"]]
                .drop_duplicates()
                .itertuples(index=False)
                if mapped is None
            }
        )
        if unmatched_names:
            log(f"[WARN] {river}: unmatched water-level station names -> {unmatched_names}")

        mapped_rivers = sorted(set(cleaned["river_from_station"].dropna()))
        if mapped_rivers and mapped_rivers != [river]:
            log(f"[WARN] {river}: station names map to {mapped_rivers}, expected {river}")

        deduped = (
            cleaned.sort_values(["date", "station_name_raw"])
            .groupby("date", as_index=False)
            .agg(
                water_level_observed=("water_level_observed", first_non_null),
            )
        )

        min_date = deduped["date"].min()
        max_date = deduped["date"].max()
        panel = pd.DataFrame({"date": pd.date_range(min_date, max_date, freq="MS")})
        panel["river"] = river
        panel = panel.merge(deduped, on="date", how="left")
        panel["water_level"] = panel["water_level_observed"]
        panel["year"] = panel["date"].dt.year
        panel["month"] = panel["date"].dt.month
        panel = panel[["river", "date", "year", "month", "water_level", "water_level_observed"]]
        panels.append(panel)

        latitude = pd.to_numeric(cleaned[lat_column], errors="coerce").dropna()
        longitude = pd.to_numeric(cleaned[lon_column], errors="coerce").dropna()
        river_meta[river] = {
            "lat": float(latitude.iloc[0]),
            "lon": float(longitude.iloc[0]),
        }
        summary_meta[river] = {
            "water_level_file": path,
            "water_level_rows_raw": int(len(raw)),
            "water_level_rows_clean": int(len(deduped)),
            "water_level_date_min": min_date.date().isoformat(),
            "water_level_date_max": max_date.date().isoformat(),
            "water_level_missing_values": int(panel["water_level_observed"].isna().sum()),
            "water_level_header_row": header_row,
            "water_level_sheet": sheet_name,
        }

        log(
            f"[INFO] Water level {river}: rows_raw={len(raw)} rows_clean={len(deduped)} "
            f"header_row={header_row} sheet={sheet_name!r} range={min_date.date()} to {max_date.date()} "
            f"missing_values={panel['water_level_observed'].isna().sum()}"
        )

    water = pd.concat(panels, ignore_index=True).sort_values(["river", "date"]).reset_index(drop=True)
    return water, river_meta, summary_meta


def load_runoff() -> tuple[pd.DataFrame, dict[str, object]]:
    runoff_path = find_one(NEW_DATA_DIR, "Ruissellement.csv")
    raw = pd.read_csv(runoff_path)
    raw.columns = [normalize_column_name(column) for column in raw.columns]
    year_column = locate_column(raw, exact={"annee", "year"})
    month_column = locate_column(raw, exact={"mois", "month"})
    cleaned = build_monthly_date(raw, year_column, month_column)

    value_columns = [column for column in cleaned.columns if column not in {"date", "year", "month", year_column, month_column}]
    long = cleaned.melt(
        id_vars=["date", "year", "month"],
        value_vars=value_columns,
        var_name="source_name",
        value_name="runoff_observed",
    )
    long["source_name_raw"] = long["source_name"].map(lambda value: value.replace("_", " ").title())
    long["river"] = long["source_name"].map(canonicalize_river_name)
    long["runoff_observed"] = pd.to_numeric(long["runoff_observed"], errors="coerce")

    unmatched_sources = sorted(long.loc[long["river"].isna(), "source_name"].dropna().unique().tolist())
    if unmatched_sources:
        log(f"[INFO] Runoff columns not mapped to target rivers -> {unmatched_sources}")

    runoff = (
        long[long["river"].isin(TARGET_RIVERS)]
        .groupby(["river", "date"], as_index=False)
        .agg(runoff_observed=("runoff_observed", first_non_null))
        .sort_values(["river", "date"])
        .reset_index(drop=True)
    )
    runoff["runoff"] = runoff["runoff_observed"]

    mapped_rivers = sorted(runoff["river"].unique().tolist())
    missing_target_rivers = sorted(set(TARGET_RIVERS) - set(mapped_rivers))
    log(
        f"[INFO] Runoff: rows_raw={len(raw)} rows_clean={len(cleaned)} rows_long={len(runoff)} "
        f"range={cleaned['date'].min().date()} to {cleaned['date'].max().date()} "
        f"missing_target_rivers={missing_target_rivers}"
    )

    summary = {
        "runoff_file": runoff_path,
        "runoff_rows_raw": int(len(raw)),
        "runoff_rows_clean": int(len(cleaned)),
        "runoff_date_min": cleaned["date"].min().date().isoformat(),
        "runoff_date_max": cleaned["date"].max().date().isoformat(),
        "runoff_unmatched_columns": unmatched_sources,
        "runoff_missing_target_rivers": missing_target_rivers,
    }
    return runoff, summary


def load_temperature_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    station_rows: list[dict[str, object]] = []
    for path in sorted({*HYDRO_METEO_DIR.glob("*Temp*.xlsx")}):
        raw, header_row, sheet_name = read_excel_detected(path)
        year_column = locate_column(raw, exact={"year", "yy"})
        month_column = locate_column(raw, exact={"month", "mm"})
        station_column = locate_column(raw, exact={"station_name", "name"})
        lat_column = locate_column(raw, exact={"lat"})
        lon_column = locate_column(raw, exact={"lon"})
        temp_max_column = locate_column(raw, contains=["temp", "max"])
        temp_min_column = locate_column(raw, contains=["temp", "min"])

        cleaned = build_monthly_date(raw, year_column, month_column)
        cleaned["station_name_raw"] = cleaned[station_column].astype(str).str.strip()
        cleaned["station_key"] = cleaned["station_name_raw"].map(normalize_text)
        cleaned["temp_max_observed"] = pd.to_numeric(cleaned[temp_max_column], errors="coerce")
        cleaned["temp_min_observed"] = pd.to_numeric(cleaned[temp_min_column], errors="coerce")
        cleaned["temp_mean_observed"] = cleaned.apply(
            lambda row: (row["temp_max_observed"] + row["temp_min_observed"]) / 2
            if pd.notna(row["temp_max_observed"]) and pd.notna(row["temp_min_observed"])
            else pd.NA,
            axis=1,
        )
        deduped = (
            cleaned.groupby(["station_key", "date"], as_index=False)
            .agg(
                station_name_raw=("station_name_raw", first_non_null),
                temp_max_observed=("temp_max_observed", first_non_null),
                temp_min_observed=("temp_min_observed", first_non_null),
                temp_mean_observed=("temp_mean_observed", first_non_null),
                lat=(lat_column, first_non_null),
                lon=(lon_column, first_non_null),
            )
            .sort_values(["station_key", "date"])
            .reset_index(drop=True)
        )
        frames.append(deduped)

        station_meta = (
            deduped.groupby("station_key", as_index=False)
            .agg(
                station_name_raw=("station_name_raw", first_non_null),
                lat=("lat", first_non_null),
                lon=("lon", first_non_null),
            )
        )
        for row in station_meta.itertuples(index=False):
            station_rows.append(
                {
                    "station_key": row.station_key,
                    "station_name_raw": row.station_name_raw,
                    "lat": float(row.lat),
                    "lon": float(row.lon),
                    "grid": CLIMATE_STATION_GRID.get(row.station_key),
                    "header_row": header_row,
                    "sheet_name": sheet_name,
                    "path": path,
                }
            )

        log(
            f"[INFO] Temperature {path.name}: rows_raw={len(raw)} rows_clean={len(deduped)} "
            f"header_row={header_row} sheet={sheet_name!r} range={deduped['date'].min().date()} to {deduped['date'].max().date()}"
        )

    temperature = pd.concat(frames, ignore_index=True).sort_values(["station_key", "date"]).reset_index(drop=True)
    stations = (
        pd.DataFrame(station_rows)
        .drop_duplicates(subset=["station_key"])
        .sort_values("station_name_raw")
        .reset_index(drop=True)
    )
    return temperature, stations


def load_precipitation_data() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    precip_path = find_one(HYDRO_METEO_DIR, "*precipitations*mensuelles.xlsx")
    raw, header_row, sheet_name = read_excel_detected(precip_path)
    year_column = locate_column(raw, exact={"year", "yy"})
    month_column = locate_column(raw, exact={"month", "mm"})
    station_column = locate_column(raw, exact={"station_name", "name"})
    lat_column = locate_column(raw, exact={"lat"})
    lon_column = locate_column(raw, exact={"lon"})
    precip_column = locate_column(raw, contains=["total", "mensuel"])

    cleaned = build_monthly_date(raw, year_column, month_column)
    cleaned["station_name_raw"] = cleaned[station_column].astype(str).str.strip()
    cleaned["station_key"] = cleaned["station_name_raw"].map(normalize_text)
    cleaned["precip_observed"] = pd.to_numeric(cleaned[precip_column], errors="coerce")

    precipitation = (
        cleaned.groupby(["station_key", "date"], as_index=False)
        .agg(
            station_name_raw=("station_name_raw", first_non_null),
            precip_observed=("precip_observed", first_non_null),
            lat=(lat_column, first_non_null),
            lon=(lon_column, first_non_null),
        )
        .sort_values(["station_key", "date"])
        .reset_index(drop=True)
    )
    stations = (
        precipitation.groupby("station_key", as_index=False)
        .agg(
            station_name_raw=("station_name_raw", first_non_null),
            lat=("lat", first_non_null),
            lon=("lon", first_non_null),
        )
        .assign(grid=lambda dataframe: dataframe["station_key"].map(CLIMATE_STATION_GRID))
        .sort_values("station_name_raw")
        .reset_index(drop=True)
    )

    log(
        f"[INFO] Precipitation: rows_raw={len(raw)} rows_clean={len(precipitation)} "
        f"header_row={header_row} sheet={sheet_name!r} range={precipitation['date'].min().date()} to {precipitation['date'].max().date()}"
    )

    summary = {
        "precip_file": precip_path,
        "precip_rows_raw": int(len(raw)),
        "precip_rows_clean": int(len(precipitation)),
        "precip_date_min": precipitation["date"].min().date().isoformat(),
        "precip_date_max": precipitation["date"].max().date().isoformat(),
        "precip_header_row": header_row,
        "precip_sheet": sheet_name,
    }
    return precipitation, stations, summary


def choose_climate_station(
    *,
    river: str,
    river_meta: dict[str, dict[str, object]],
    stations: pd.DataFrame,
) -> dict[str, object]:
    preferred_grid = ERA5_RIVER_GRID[river]
    river_lat = float(river_meta[river]["lat"])
    river_lon = float(river_meta[river]["lon"])
    candidates = stations.copy()
    same_grid = candidates[candidates["grid"] == preferred_grid].copy()
    pool = same_grid if not same_grid.empty else candidates
    pool["distance_deg"] = pool.apply(
        lambda row: math.hypot(river_lat - float(row["lat"]), river_lon - float(row["lon"])),
        axis=1,
    )
    selected = pool.sort_values(["distance_deg", "station_name_raw"]).iloc[0]
    return {
        "station_key": selected["station_key"],
        "station_name_raw": selected["station_name_raw"],
        "distance_deg": float(selected["distance_deg"]),
        "selection_mode": "same_era5_grid" if not same_grid.empty else "nearest_fallback",
    }


def attach_observed_climate(
    base: pd.DataFrame,
    *,
    river_meta: dict[str, dict[str, object]],
    temperature: pd.DataFrame,
    temperature_stations: pd.DataFrame,
    precipitation: pd.DataFrame,
    precipitation_stations: pd.DataFrame,
    summary_meta: dict[str, dict[str, object]],
) -> pd.DataFrame:
    working = base.copy()

    temp_choices = {
        river: choose_climate_station(river=river, river_meta=river_meta, stations=temperature_stations)
        for river in TARGET_RIVERS
    }
    precip_choices = {
        river: choose_climate_station(river=river, river_meta=river_meta, stations=precipitation_stations)
        for river in TARGET_RIVERS
    }

    temperature_join = []
    for river, choice in temp_choices.items():
        subset = temperature[temperature["station_key"] == choice["station_key"]].copy()
        subset["river"] = river
        subset["temp_source"] = choice["station_name_raw"]
        temperature_join.append(
            subset[
                [
                    "river",
                    "date",
                    "temp_max_observed",
                    "temp_min_observed",
                    "temp_mean_observed",
                    "temp_source",
                ]
            ]
        )
        summary_meta[river].update(
            {
                "temp_source": choice["station_name_raw"],
                "temp_source_distance_deg": round(choice["distance_deg"], 6),
                "temp_source_selection_mode": choice["selection_mode"],
            }
        )
        log(
            f"[INFO] Temp source {river}: {choice['station_name_raw']} "
            f"mode={choice['selection_mode']} distance_deg={choice['distance_deg']:.4f}"
        )

    precipitation_join = []
    for river, choice in precip_choices.items():
        subset = precipitation[precipitation["station_key"] == choice["station_key"]].copy()
        subset["river"] = river
        subset["precip_source"] = choice["station_name_raw"]
        precipitation_join.append(
            subset[
                [
                    "river",
                    "date",
                    "precip_observed",
                    "precip_source",
                ]
            ]
        )
        summary_meta[river].update(
            {
                "precip_source": choice["station_name_raw"],
                "precip_source_distance_deg": round(choice["distance_deg"], 6),
                "precip_source_selection_mode": choice["selection_mode"],
            }
        )
        log(
            f"[INFO] Precip source {river}: {choice['station_name_raw']} "
            f"mode={choice['selection_mode']} distance_deg={choice['distance_deg']:.4f}"
        )

    temp_source_map = {river: choice["station_name_raw"] for river, choice in temp_choices.items()}
    precip_source_map = {river: choice["station_name_raw"] for river, choice in precip_choices.items()}

    working = working.merge(pd.concat(temperature_join, ignore_index=True), on=["river", "date"], how="left")
    working = working.merge(pd.concat(precipitation_join, ignore_index=True), on=["river", "date"], how="left")
    working["temp_source"] = working["river"].map(temp_source_map)
    working["precip_source"] = working["river"].map(precip_source_map)
    return working


def era5_aggregate_frame(grouped: pd.core.groupby.DataFrameGroupBy) -> pd.DataFrame:
    aggregated = grouped.agg(
        era5_t2m_mean=("t2m", "mean"),
        era5_t2m_min=("t2m", "min"),
        era5_t2m_max=("t2m", "max"),
        era5_u10_mean=("u10", "mean"),
        era5_v10_mean=("v10", "mean"),
        era5_d2m_mean=("d2m", "mean"),
        era5_msl_mean=("msl", "mean"),
    )
    aggregated["era5_tp_sum"] = grouped["tp"].sum(min_count=1)
    aggregated = aggregated.reset_index()
    aggregated["era5_t2m_mean"] = aggregated["era5_t2m_mean"] - 273.15
    aggregated["era5_t2m_min"] = aggregated["era5_t2m_min"] - 273.15
    aggregated["era5_t2m_max"] = aggregated["era5_t2m_max"] - 273.15
    aggregated["era5_d2m_mean"] = aggregated["era5_d2m_mean"] - 273.15
    aggregated["era5_tp_sum"] = aggregated["era5_tp_sum"] * 1000.0
    return aggregated


def load_monthly_era5(summary_meta: dict[str, dict[str, object]]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for grid in sorted(set(ERA5_RIVER_GRID.values())):
        path = find_one(ERA5_DIR, f"era5_{grid}_*.csv")
        raw = pd.read_csv(
            path,
            usecols=["timestamp", "u10", "v10", "t2m", "tp", "d2m", "msl"],
            parse_dates=["timestamp"],
        )
        raw["date"] = raw["timestamp"].dt.to_period("M").dt.to_timestamp()
        monthly = era5_aggregate_frame(raw.groupby("date"))
        monthly["era5_grid"] = grid
        frames.append(monthly)
        log(
            f"[INFO] ERA5 {grid}: hourly_rows={len(raw)} monthly_rows={len(monthly)} "
            f"range={monthly['date'].min().date()} to {monthly['date'].max().date()}"
        )
        for river, river_grid in ERA5_RIVER_GRID.items():
            if river_grid == grid:
                summary_meta[river]["era5_file"] = path
                summary_meta[river]["era5_grid"] = grid

    era5 = pd.concat(frames, ignore_index=True).sort_values(["era5_grid", "date"]).reset_index(drop=True)
    return era5


def attach_era5(base: pd.DataFrame, era5: pd.DataFrame) -> pd.DataFrame:
    working = base.copy()
    working["era5_grid"] = working["river"].map(ERA5_RIVER_GRID)
    working = working.merge(era5, on=["era5_grid", "date"], how="left")
    return working


def validate_dataset(combined: pd.DataFrame, per_river_frames: dict[str, pd.DataFrame]) -> None:
    duplicate_count = int(combined.duplicated(subset=["river", "date"]).sum())
    if duplicate_count:
        raise ValueError(f"Combined dataset has {duplicate_count} duplicate river-month rows")

    for river, dataframe in per_river_frames.items():
        duplicate_count = int(dataframe.duplicated(subset=["river", "date"]).sum())
        if duplicate_count:
            raise ValueError(f"{river} per-river dataset has {duplicate_count} duplicate rows")
        expected_dates = pd.date_range(dataframe["date"].min(), dataframe["date"].max(), freq="MS")
        if len(expected_dates) != len(dataframe) or not dataframe["date"].reset_index(drop=True).equals(
            pd.Series(expected_dates)
        ):
            raise ValueError(f"{river} per-river dataset is not a complete monthly sequence")
        filtered = combined[combined["river"] == river].reset_index(drop=True)
        if not filtered.equals(dataframe.reset_index(drop=True)):
            raise ValueError(f"{river} per-river dataset is not an exact filtered subset of the combined dataset")

    log(
        f"[INFO] Validation passed: combined_rows={len(combined)} unique_river_months={combined[['river', 'date']].drop_duplicates().shape[0]}"
    )


def build_summary_markdown(
    *,
    combined: pd.DataFrame,
    per_river_frames: dict[str, pd.DataFrame],
    summary_meta: dict[str, dict[str, object]],
    runoff_summary: dict[str, object],
    precip_summary: dict[str, object],
) -> str:
    lines: list[str] = []
    lines.append("# Merge Summary")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append(f"- Combined monthly master dataset: `outputs/master_dataset_monthly.csv` ({len(combined)} rows)")
    lines.append(f"- Per-river monthly datasets: `outputs/per_river/*.csv` ({len(per_river_frames)} files)")
    lines.append(f"- Manifest: `outputs/output_manifest.csv`")
    lines.append("")
    lines.append("## Merge Rules")
    lines.append("")
    lines.append("- Water level panels were built from each river's minimum to maximum observed water-level month; no imputation was applied.")
    lines.append("- `water_level` equals `water_level_observed`, and `runoff` equals `runoff_observed` because this build does not create filled or modeled series.")
    lines.append("- River and station names were standardized by removing accents, normalizing case, collapsing spacing and punctuation, and applying explicit aliases such as `BASSE-MULEMBWE` -> `Mulembwe` and `MUREMBWE` -> `Mulembwe`.")
    lines.append("- Observed climate sources were chosen per river by preferring stations that share the river's ERA5 grid from `era5_download/README.md`; if none existed on that grid, the nearest observed station by coordinates was used.")
    lines.append("- ERA5 hourly temperature and dewpoint were converted from Kelvin to degrees Celsius, and ERA5 precipitation totals were converted from meters to millimeters after monthly aggregation.")
    lines.append("")
    lines.append("## Assumptions And Gaps")
    lines.append("")
    lines.append(
        f"- Runoff is only available in `Ruissellement.csv` for a subset of target rivers. Rivers without a mapped runoff column remain missing: {', '.join(runoff_summary['runoff_missing_target_rivers'])}."
    )
    lines.append(
        f"- Unmatched runoff columns that were left unused because they do not map confidently to the target river list: {', '.join(runoff_summary['runoff_unmatched_columns'])}."
    )
    lines.append(
        "- The extra workbook `Data_RainfallBDI_Corrige_1981_2023.xlsx` was not needed because `les precipitations mensuelles.xlsx` already supplied the observed local monthly precipitation series used here."
    )
    lines.append("")
    lines.append("## River Details")
    lines.append("")
    lines.append("| River | Water-level range | Water-level rows | Temp source | Temp mode | Precip source | Precip mode | ERA5 grid | Missing water level months |")
    lines.append("|---|---:|---:|---|---|---|---|---|---:|")
    for river in TARGET_RIVERS:
        meta = summary_meta[river]
        lines.append(
            f"| {river} | {meta['water_level_date_min']} to {meta['water_level_date_max']} | {meta['water_level_rows_clean']} | "
            f"{meta['temp_source']} | {meta['temp_source_selection_mode']} | {meta['precip_source']} | {meta['precip_source_selection_mode']} | "
            f"{meta['era5_grid']} | {meta['water_level_missing_values']} |"
        )
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append(f"- Combined dataset contains {len(combined)} rows and one unique row per river-month.")
    lines.append("- Each per-river dataset is a complete monthly sequence from that river's min to max observed water-level date.")
    lines.append("- Each per-river dataset was validated as an exact filtered subset of the combined dataset.")
    lines.append(
        f"- Observed precipitation source file: `{Path(precip_summary['precip_file']).relative_to(ROOT)}` with {precip_summary['precip_rows_clean']} station-month rows after cleaning."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    if NEW_DATA_DIR is None:
        raise FileNotFoundError("Could not locate the '*nouvelles*' data directory")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PER_RIVER_DIR.mkdir(parents=True, exist_ok=True)

    water_levels, river_meta, summary_meta = load_water_levels()
    runoff, runoff_summary = load_runoff()
    temperature, temperature_stations = load_temperature_data()
    precipitation, precipitation_stations, precip_summary = load_precipitation_data()

    combined = water_levels.merge(runoff[["river", "date", "runoff", "runoff_observed"]], on=["river", "date"], how="left")
    combined = attach_observed_climate(
        combined,
        river_meta=river_meta,
        temperature=temperature,
        temperature_stations=temperature_stations,
        precipitation=precipitation,
        precipitation_stations=precipitation_stations,
        summary_meta=summary_meta,
    )

    era5 = load_monthly_era5(summary_meta)
    combined = attach_era5(combined, era5)

    ordered_columns = [
        "river",
        "date",
        "year",
        "month",
        "water_level",
        "water_level_observed",
        "runoff",
        "runoff_observed",
        "temp_max_observed",
        "temp_min_observed",
        "temp_mean_observed",
        "precip_observed",
        "temp_source",
        "precip_source",
        "era5_grid",
        "era5_t2m_mean",
        "era5_t2m_min",
        "era5_t2m_max",
        "era5_tp_sum",
        "era5_u10_mean",
        "era5_v10_mean",
        "era5_d2m_mean",
        "era5_msl_mean",
    ]
    combined = combined[ordered_columns].sort_values(["river", "date"]).reset_index(drop=True)
    combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

    per_river_frames: dict[str, pd.DataFrame] = {}
    write_dataframe(combined, OUTPUT_DIR / "master_dataset_monthly.csv")
    log(f"[INFO] Wrote outputs/master_dataset_monthly.csv rows={len(combined)}")

    for river in TARGET_RIVERS:
        subset = combined[combined["river"] == river].reset_index(drop=True)
        per_river_frames[river] = subset
        river_slug = normalize_text(river).replace(" ", "_")
        output_path = PER_RIVER_DIR / f"{river_slug}_monthly.csv"
        write_dataframe(subset, output_path)
        log(f"[INFO] Wrote {output_path.relative_to(ROOT)} rows={len(subset)}")

    validate_dataset(
        combined.assign(date=pd.to_datetime(combined["date"])),
        {river: frame.assign(date=pd.to_datetime(frame["date"])) for river, frame in per_river_frames.items()},
    )

    manifest_rows = [
        {"file": str((OUTPUT_DIR / "master_dataset_monthly.csv").relative_to(ROOT)), "row_count": len(combined)}
    ]
    for river in TARGET_RIVERS:
        river_slug = normalize_text(river).replace(" ", "_")
        manifest_rows.append(
            {
                "file": str((PER_RIVER_DIR / f"{river_slug}_monthly.csv").relative_to(ROOT)),
                "row_count": len(per_river_frames[river]),
            }
        )
    manifest_rows.append({"file": str(SUMMARY_PATH.relative_to(ROOT)), "row_count": pd.NA})
    manifest = pd.DataFrame(manifest_rows)
    write_dataframe(manifest, MANIFEST_PATH)
    log(f"[INFO] Wrote {MANIFEST_PATH.relative_to(ROOT)} rows={len(manifest)}")

    summary_markdown = build_summary_markdown(
        combined=combined,
        per_river_frames=per_river_frames,
        summary_meta=summary_meta,
        runoff_summary=runoff_summary,
        precip_summary=precip_summary,
    )
    SUMMARY_PATH.write_text(summary_markdown, encoding="utf-8")
    log(f"[INFO] Wrote {SUMMARY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
