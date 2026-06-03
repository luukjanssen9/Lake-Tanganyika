from __future__ import annotations

import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiLineString
from shapely.ops import unary_union

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

FINAL_BASINS_PATH = DATA_DIR / "basins" / "basins.gpkg"
HYDRORIVERS_PATH = DATA_DIR / "hydrorivers" / "hydrorivers_africa.shp"
REACH_REVIEW_PATH = DATA_DIR / "reach_review.csv"
RAW_WATER_LEVEL_DIR = DATA_DIR / "water_levels"

GPKG_OUTPUT_PATH = OUTPUT_DIR / "static_map_layers.gpkg"
BASINS_GEOJSON_PATH = OUTPUT_DIR / "basins.geojson"
RIVERS_GEOJSON_PATH = OUTPUT_DIR / "rivers.geojson"
STATIONS_GEOJSON_PATH = OUTPUT_DIR / "stations.geojson"
HTML_MAP_OUTPUT_PATH = OUTPUT_DIR / "static_map.html"

GEOGRAPHIC_CRS = "EPSG:4326"
METRIC_CRS = "EPSG:32735"
XML_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

FILE_RIVER_MAP = {
    "BUZIMBA": "Buzimba",
    "JIJI": "Jiji",
    "KABURANTWA": "Kaburantwa",
    "MPANDA": "Mpanda",
    "MULEMBWE": "Mulembwe",
    "MUTIMBUZI": "Mutimbuzi",
    "NYAKAGUNDA": "Nyakagunda",
    "NYAMAGANA": "Nyamagana",
    "NYENGWE": "Nyengwe",
    "RUSIZI": "Rusizi",
}

RIVER_DISPLAY_ORDER = [
    "Buzimba",
    "Jiji",
    "Kaburantwa",
    "Mpanda",
    "Mulembwe",
    "Mutimbuzi",
    "Nyakagunda",
    "Nyamagana",
    "Nyengwe",
    "Rusizi",
]

REACH_CONFIDENCE_MAP = {
    "clean": "high",
    "acceptable": "medium",
    "provisional": "medium",
    "unresolved": "low",
}

# More saturated than v2, while preserving enough transparency for overlap reading.
BASIN_COLORS = {
    "Buzimba": "#2fbf71",
    "Jiji": "#24a6d8",
    "Kaburantwa": "#f28e2b",
    "Mpanda": "#8f63d8",
    "Mulembwe": "#7bc043",
    "Mutimbuzi": "#e45756",
    "Nyakagunda": "#b8de29",
    "Nyamagana": "#00a6a6",
    "Nyengwe": "#f2c94c",
    "Rusizi": "#4e79d9",
}


@dataclass
class WaterLevelWorkbook:
    river: str
    file_path: Path
    station_name: str | None
    station_id: str | None
    latitude: float | None
    longitude: float | None
    elevation_m: float | None


def relpath(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def ensure_output_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def check_required_inputs() -> None:
    required_files = [
        FINAL_BASINS_PATH,
        HYDRORIVERS_PATH,
        REACH_REVIEW_PATH,
    ]
    missing = [relpath(path) for path in required_files if not path.exists()]
    water_level_files = sorted(RAW_WATER_LEVEL_DIR.glob("water_level_*.xlsx"))
    if not water_level_files:
        missing.append("data/water_levels/water_level_*.xlsx")
    if missing:
        message = "Missing required input file(s):\n" + "\n".join(f"- {item}" for item in missing)
        raise FileNotFoundError(message)


def excel_col_from_ref(cell_ref: str) -> str:
    match = re.match(r"([A-Z]+)(\d+)", cell_ref)
    if not match:
        raise ValueError(f"Unexpected Excel cell reference: {cell_ref}")
    return match.group(1)


def excel_row_from_ref(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)(\d+)", cell_ref)
    if not match:
        raise ValueError(f"Unexpected Excel cell reference: {cell_ref}")
    return int(match.group(2))


def read_xlsx_rows(path: Path) -> dict[int, dict[str, str | None]]:
    with ZipFile(path) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for item in shared_root.findall("x:si", XML_NS):
                texts = [t.text or "" for t in item.findall(".//x:t", XML_NS)]
                shared_strings.append("".join(texts))

        sheet_root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))

        rows: dict[int, dict[str, str | None]] = {}
        for cell in sheet_root.findall(".//x:sheetData/x:row/x:c", XML_NS):
            cell_ref = cell.attrib["r"]
            row_idx = excel_row_from_ref(cell_ref)
            col_idx = excel_col_from_ref(cell_ref)
            cell_type = cell.attrib.get("t")

            value_node = cell.find("x:v", XML_NS)
            inline_node = cell.find("x:is", XML_NS)

            if cell_type == "inlineStr" and inline_node is not None:
                value = "".join(t.text or "" for t in inline_node.findall(".//x:t", XML_NS))
            elif value_node is None:
                value = None
            else:
                value = value_node.text
                if cell_type == "s" and value is not None:
                    value = shared_strings[int(value)]

            rows.setdefault(row_idx, {})[col_idx] = value
    return rows


def detect_header_row(rows: dict[int, dict[str, str | None]]) -> int:
    required_groups = [
        {"STATION NAME", "NAME"},
        {"LAT"},
        {"LON"},
        {"YEAR", "YY"},
        {"MONTH", "MM"},
    ]
    for row_idx in sorted(rows):
        values = {normalize_text(v) for v in rows[row_idx].values() if v not in (None, "")}
        if not values:
            continue
        has_required = all(any(option in values for option in group) for group in required_groups)
        if has_required and any(value.startswith("HAUT") for value in values):
            return row_idx
    raise ValueError("Could not detect a water-level header row in workbook.")


def build_header_map(header_row: dict[str, str | None]) -> dict[str, str]:
    field_map: dict[str, str] = {}
    for col, raw_value in header_row.items():
        norm = normalize_text(raw_value)
        if norm in {"STATIONID"}:
            field_map[col] = "station_id"
        elif norm in {"STATION NAME", "NAME"}:
            field_map[col] = "station_name"
        elif norm == "LAT":
            field_map[col] = "lat"
        elif norm == "LON":
            field_map[col] = "lon"
        elif norm in {"ELEV", "ALT"}:
            field_map[col] = "elev"
        elif norm in {"YEAR", "YY"}:
            field_map[col] = "year"
        elif norm in {"MONTH", "MM"}:
            field_map[col] = "month"
        elif norm.startswith("HAUT"):
            field_map[col] = "water_level_m"
    return field_map


def river_from_water_level_filename(path: Path) -> str:
    match = re.search(r"water_level_(.+?)\.xlsx$", path.name, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Could not parse river name from {path.name}")
    key = normalize_text(match.group(1))
    if key not in FILE_RIVER_MAP:
        raise ValueError(f"Unknown river key parsed from workbook: {key}")
    return FILE_RIVER_MAP[key]


def parse_numeric(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_water_level_workbooks() -> pd.DataFrame:
    workbooks: list[dict[str, Any]] = []
    for path in sorted(RAW_WATER_LEVEL_DIR.glob("water_level_*.xlsx")):
        river = river_from_water_level_filename(path)
        rows = read_xlsx_rows(path)
        header_row_idx = detect_header_row(rows)
        header_map = build_header_map(rows[header_row_idx])

        records: list[dict[str, Any]] = []
        for row_idx in sorted(rows):
            if row_idx <= header_row_idx:
                continue
            raw_row = rows[row_idx]
            record = {field: raw_row.get(col) for col, field in header_map.items()}
            year = parse_numeric(record.get("year"))
            month = parse_numeric(record.get("month"))
            if year is None or month is None:
                continue
            record["year"] = int(year)
            record["month"] = int(month)
            for field in ["lat", "lon", "elev", "water_level_m"]:
                record[field] = parse_numeric(record.get(field))
            record["station_id"] = None if record.get("station_id") in (None, "") else str(record["station_id"]).strip()
            record["station_name"] = None if record.get("station_name") in (None, "") else str(record["station_name"]).strip()
            record["row_idx"] = row_idx
            records.append(record)

        frame = pd.DataFrame(records)
        if frame.empty:
            raise ValueError(f"No data rows parsed from {relpath(path)}")

        for fill_col in ["station_id", "station_name", "lat", "lon", "elev"]:
            if fill_col in frame.columns:
                frame[fill_col] = frame[fill_col].ffill().bfill()

        first_row = frame.iloc[0]
        workbook = WaterLevelWorkbook(
            river=river,
            file_path=path,
            station_name=first_row.get("station_name") if pd.notna(first_row.get("station_name")) else None,
            station_id=first_row.get("station_id") if pd.notna(first_row.get("station_id")) else None,
            latitude=first_row.get("lat") if pd.notna(first_row.get("lat")) else None,
            longitude=first_row.get("lon") if pd.notna(first_row.get("lon")) else None,
            elevation_m=first_row.get("elev") if pd.notna(first_row.get("elev")) else None,
        )
        workbooks.append(
            {
                "river": workbook.river,
                "station_id": workbook.station_id,
                "station_name": workbook.station_name,
                "latitude": workbook.latitude,
                "longitude": workbook.longitude,
                "elevation_m": workbook.elevation_m,
                "source_file": workbook.file_path.name,
                "source_path": relpath(workbook.file_path),
            }
        )
    out = pd.DataFrame(workbooks)
    return out.sort_values("river").reset_index(drop=True)


def load_basin_inputs() -> gpd.GeoDataFrame:
    basins = gpd.read_file(FINAL_BASINS_PATH, layer="river_basins")
    return basins.sort_values("river").reset_index(drop=True)


def extract_linework(geom) -> MultiLineString | Any | None:
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in {"LineString", "MultiLineString"}:
        return geom
    if geom.geom_type == "GeometryCollection":
        lines = [part for part in geom.geoms if part.geom_type in {"LineString", "MultiLineString"} and not part.is_empty]
        if not lines:
            return None
        return unary_union(lines)
    return None


def load_hydrorivers_subset(basins: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    minx, miny, maxx, maxy = basins.total_bounds
    bbox = (minx - 0.5, miny - 0.5, maxx + 0.5, maxy + 0.5)
    rivers = gpd.read_file(HYDRORIVERS_PATH, bbox=bbox)
    keep = rivers[
        [
            "HYRIV_ID",
            "NEXT_DOWN",
            "MAIN_RIV",
            "LENGTH_KM",
            "UPLAND_SKM",
            "DIS_AV_CMS",
            "ORD_FLOW",
            "HYBAS_L12",
            "geometry",
        ]
    ].copy()
    return keep.to_crs(basins.crs)


def build_rivers_layer(
    basins: gpd.GeoDataFrame,
    hydrorivers: gpd.GeoDataFrame,
    reach_review: pd.DataFrame,
) -> gpd.GeoDataFrame:
    basin_lookup = basins.set_index("river")
    review_lookup = reach_review.set_index("river")
    rows: list[dict[str, Any]] = []

    for river in RIVER_DISPLAY_ORDER:
        basin_geom = basin_lookup.loc[river, "geometry"]
        review = review_lookup.loc[river]

        has_reviewed_id = pd.notna(review["selected_hyriv_id"])
        selected_hyriv_id = int(review["selected_hyriv_id"]) if has_reviewed_id else int(review["diagnostic_chosen_hyriv_id"])
        selection_method = "reach_review_selected_hyriv_id" if has_reviewed_id else "diagnostic_chosen_hyriv_id_fallback"

        selected_reach = hydrorivers[hydrorivers["HYRIV_ID"] == selected_hyriv_id].copy()
        if selected_reach.empty:
            raise ValueError(f"Could not find HYRIV_ID {selected_hyriv_id} in the HydroRIVERS subset for {river}.")

        main_riv = int(selected_reach["MAIN_RIV"].iloc[0])
        clipped = hydrorivers[hydrorivers.intersects(basin_geom)].copy()
        upstream_lookup: dict[int, set[int]] = {}
        for row in clipped.itertuples():
            try:
                next_down = int(row.NEXT_DOWN)
            except (TypeError, ValueError):
                continue
            upstream_lookup.setdefault(next_down, set()).add(int(row.HYRIV_ID))

        traced_ids = {selected_hyriv_id}
        queue = [selected_hyriv_id]
        while queue:
            current = queue.pop()
            for upstream_id in upstream_lookup.get(current, set()):
                if upstream_id not in traced_ids:
                    traced_ids.add(upstream_id)
                    queue.append(upstream_id)

        clipped = clipped[clipped["HYRIV_ID"].isin(traced_ids)].copy()
        clipped["geometry"] = clipped.geometry.intersection(basin_geom)
        clipped["geometry"] = clipped["geometry"].apply(extract_linework)
        clipped = clipped.dropna(subset=["geometry"]).copy()
        clipped = clipped[~clipped.geometry.is_empty].copy()

        if clipped.empty:
            fallback = selected_reach.copy()
            fallback["geometry"] = fallback["geometry"].apply(extract_linework)
            clipped = fallback.dropna(subset=["geometry"]).copy()
            geometry_note = "Fallback to the selected HydroRIVERS reach without basin clipping because no basin-intersecting reviewed reach could be locked."
        else:
            geometry_note = "Derived by tracing the upstream HydroRIVERS network from the selected reach and clipping it to the approved basin polygon."

        merged_geom = unary_union(list(clipped.geometry))
        geom_metric = gpd.GeoSeries([merged_geom], crs=GEOGRAPHIC_CRS).to_crs(METRIC_CRS)
        line_length_km = float(geom_metric.length.iloc[0] / 1000.0)

        rows.append(
            {
                "river": river,
                "river_id": selected_hyriv_id,
                "main_riv": main_riv,
                "geometry_source": f"{HYDRORIVERS_PATH.name} + {REACH_REVIEW_PATH.name}",
                "line_selection_method": selection_method,
                "selected_hyriv_id_is_reviewed": bool(has_reviewed_id),
                "reach_status": review["reach_status"],
                "geometry_confidence": REACH_CONFIDENCE_MAP.get(str(review["reach_status"]), "medium"),
                "line_length_km": round(line_length_km, 3),
                "segment_count": int(len(clipped)),
                "status_flag": None if pd.isna(review["status_flag"]) else str(review["status_flag"]),
                "reach_note": None if pd.isna(review["reach_note"]) else str(review["reach_note"]),
                "geometry_note": geometry_note,
                "geometry": merged_geom,
            }
        )

    return gpd.GeoDataFrame(rows, geometry="geometry", crs=GEOGRAPHIC_CRS).sort_values("river").reset_index(drop=True)


def build_stations_layer(station_sources: pd.DataFrame) -> gpd.GeoDataFrame:
    stations = station_sources.copy()
    missing_coords = stations[stations[["latitude", "longitude"]].isna().any(axis=1)]
    if not missing_coords.empty:
        rivers = ", ".join(missing_coords["river"].astype(str).tolist())
        raise ValueError(f"Missing original station coordinates in water-level workbook(s): {rivers}")

    stations_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations["longitude"], stations["latitude"]),
        crs=GEOGRAPHIC_CRS,
    )
    keep = stations_gdf[
        [
            "station_id",
            "station_name",
            "river",
            "latitude",
            "longitude",
            "geometry",
        ]
    ].copy()
    return keep.sort_values("river").reset_index(drop=True)


def title_case_station(value: object) -> str:
    if value is None or pd.isna(value):
        return "Unnamed Gauge"
    return str(value).strip().title()


def clean_basins_layer(basins: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = basins.copy()
    out["area_km2"] = out["basin_area_km2"].round(2)
    out["display_name"] = out["river"].astype(str) + " Basin"
    out["confidence_level"] = "high"
    out["search_label"] = out["river"].astype(str)
    out["feature_type"] = "basin"

    out = out.sort_values(["area_km2", "river"], ascending=[False, True]).reset_index(drop=True)
    out["draw_order"] = range(1, len(out) + 1)

    keep = [
        "river",
        "display_name",
        "area_km2",
        "confidence_level",
        "search_label",
        "feature_type",
        "draw_order",
        "geometry",
    ]
    return gpd.GeoDataFrame(out[keep], geometry="geometry", crs=basins.crs)


def concise_river_source(row: pd.Series) -> str:
    if row["confidence_level"] == "low":
        return "HydroRIVERS diagnostic fallback"
    return "HydroRIVERS reviewed network"


def clean_rivers_layer(rivers_full: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = rivers_full.copy()
    out["display_name"] = out["river"].astype(str) + " River"
    out["confidence_level"] = out["geometry_confidence"]
    out["geometry_source"] = out.apply(concise_river_source, axis=1)
    out["search_label"] = out["river"].astype(str)
    out["feature_type"] = "river"

    keep = [
        "river",
        "display_name",
        "confidence_level",
        "geometry_source",
        "search_label",
        "feature_type",
        "geometry",
    ]
    return gpd.GeoDataFrame(out[keep], geometry="geometry", crs=rivers_full.crs).sort_values("river").reset_index(drop=True)


def clean_stations_layer(stations_full: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = stations_full.copy()
    out["station_name"] = out["station_name"].apply(title_case_station)
    out["display_name"] = out["station_name"]
    out["latitude"] = out["latitude"].round(5)
    out["longitude"] = out["longitude"].round(5)
    out["search_label"] = out["station_name"]
    out["feature_type"] = "station"

    keep = [
        "station_name",
        "river",
        "display_name",
        "latitude",
        "longitude",
        "search_label",
        "feature_type",
        "geometry",
    ]
    return gpd.GeoDataFrame(out[keep], geometry="geometry", crs=stations_full.crs).sort_values("station_name").reset_index(drop=True)


def build_layers() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    check_required_inputs()
    basins_raw = load_basin_inputs()
    reach_review = pd.read_csv(REACH_REVIEW_PATH)
    hydrorivers = load_hydrorivers_subset(basins_raw)
    rivers_full = build_rivers_layer(basins_raw, hydrorivers, reach_review)

    station_sources = load_water_level_workbooks()
    stations_full = build_stations_layer(station_sources)

    basins = clean_basins_layer(basins_raw)
    rivers = clean_rivers_layer(rivers_full)
    stations = clean_stations_layer(stations_full)
    return basins.to_crs(GEOGRAPHIC_CRS), rivers.to_crs(GEOGRAPHIC_CRS), stations.to_crs(GEOGRAPHIC_CRS)


def write_master_gpkg(
    basins: gpd.GeoDataFrame,
    rivers: gpd.GeoDataFrame,
    stations: gpd.GeoDataFrame,
) -> None:
    if GPKG_OUTPUT_PATH.exists():
        GPKG_OUTPUT_PATH.unlink()
    basins.to_file(GPKG_OUTPUT_PATH, layer="basins", driver="GPKG")
    rivers.to_file(GPKG_OUTPUT_PATH, layer="rivers", driver="GPKG")
    stations.to_file(GPKG_OUTPUT_PATH, layer="stations", driver="GPKG")


def write_geojson(path: Path, gdf: gpd.GeoDataFrame) -> None:
    if path.exists():
        path.unlink()
    gdf.to_file(path, driver="GeoJSON")


def feature_collection(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    return json.loads(gdf.to_json(drop_id=True))


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def build_html_map(
    basins: gpd.GeoDataFrame,
    rivers: gpd.GeoDataFrame,
    stations: gpd.GeoDataFrame,
) -> str:
    basins_fc = feature_collection(basins)
    rivers_fc = feature_collection(rivers)
    stations_fc = feature_collection(stations)
    minx, miny, maxx, maxy = basins.total_bounds

    river_options = sorted(basins["river"].tolist())
    station_options = stations[["station_name", "river"]].sort_values(["river", "station_name"]).to_dict("records")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Lake Tanganyika Static River Context Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
  <style>
    html, body {{
      height: 100%;
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", Arial, sans-serif;
      color: #1f2f3a;
      background: #edf3f5;
    }}
    #map {{
      width: 100%;
      height: 100%;
    }}
    .map-controls {{
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 1000;
      width: min(286px, calc(100vw - 24px));
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(32, 48, 58, 0.12);
      border-radius: 14px;
      box-shadow: 0 14px 32px rgba(32, 48, 58, 0.14);
      backdrop-filter: blur(10px);
      padding: 11px 12px 12px;
    }}
    .map-title {{
      margin: 0 0 8px;
      font-size: 14px;
      font-weight: 750;
      letter-spacing: 0.01em;
    }}
    .control-row {{
      display: grid;
      grid-template-columns: 58px 1fr;
      align-items: center;
      gap: 8px;
      margin: 7px 0;
    }}
    .control-row label {{
      font-size: 12px;
      font-weight: 700;
      color: #51636f;
    }}
    .control-row select {{
      width: 100%;
      appearance: none;
      border: 1px solid #c7d4dc;
      border-radius: 9px;
      background: #ffffff;
      color: #213542;
      font-size: 13px;
      padding: 8px 30px 8px 10px;
      outline: none;
      background-image:
        linear-gradient(45deg, transparent 50%, #557083 50%),
        linear-gradient(135deg, #557083 50%, transparent 50%);
      background-position:
        calc(100% - 17px) 52%,
        calc(100% - 12px) 52%;
      background-size: 5px 5px, 5px 5px;
      background-repeat: no-repeat;
    }}
    .control-row select:focus {{
      border-color: #3b7fb6;
      box-shadow: 0 0 0 3px rgba(59, 127, 182, 0.16);
    }}
    .hint {{
      margin-top: 7px;
      min-height: 15px;
      font-size: 11px;
      color: #667986;
    }}
    .leaflet-popup-content {{
      min-width: 190px;
      line-height: 1.42;
    }}
    .popup-title {{
      margin-bottom: 6px;
      font-size: 14px;
      font-weight: 800;
      color: #17314a;
    }}
    .popup-row {{
      margin: 2px 0;
      font-size: 12px;
    }}
    .popup-label {{
      font-weight: 750;
      color: #3c5667;
    }}
    .legend-card {{
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(32, 48, 58, 0.11);
      border-radius: 13px;
      box-shadow: 0 10px 24px rgba(32, 48, 58, 0.10);
      padding: 9px 11px;
      line-height: 1.35;
    }}
    .legend-title {{
      margin-bottom: 6px;
      font-size: 11px;
      font-weight: 800;
      color: #30495b;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 4px 0;
      font-size: 12px;
      color: #4c5f6c;
    }}
    .legend-swatch {{
      width: 17px;
      height: 10px;
      border: 1px solid rgba(20, 30, 35, 0.18);
      border-radius: 999px;
      flex: 0 0 auto;
    }}
    .legend-point {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      border: 2px solid #ffffff;
      box-shadow: 0 0 0 1px rgba(20, 30, 35, 0.22);
      background: #f0a12c;
      flex: 0 0 auto;
    }}
    .leaflet-control-layers {{
      border: 1px solid rgba(32, 48, 58, 0.12) !important;
      border-radius: 13px !important;
      box-shadow: 0 10px 24px rgba(32, 48, 58, 0.10) !important;
      overflow: hidden;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="map-controls">
    <div class="map-title">Lake Tanganyika Rivers</div>
    <div class="control-row">
      <label for="riverSelect">River</label>
      <select id="riverSelect">
        <option value="">Choose river...</option>
        {''.join(f'<option value="{html_escape(river)}">{html_escape(river)}</option>' for river in river_options)}
      </select>
    </div>
    <div class="control-row">
      <label for="stationSelect">Gauge</label>
      <select id="stationSelect">
        <option value="">Choose gauge...</option>
        {''.join(f'<option value="{html_escape(row["station_name"])}">{html_escape(row["station_name"])} ({html_escape(row["river"])})</option>' for row in station_options)}
      </select>
    </div>
    <div id="controlHint" class="hint">Select a river or gauge to zoom and highlight.</div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <script>
    const BASINS = {json.dumps(basins_fc)};
    const RIVERS = {json.dumps(rivers_fc)};
    const STATIONS = {json.dumps(stations_fc)};
    const BASIN_COLORS = {json.dumps(BASIN_COLORS)};
    const INITIAL_BOUNDS = [[{miny}, {minx}], [{maxy}, {maxx}]];

    const map = L.map('map', {{
      zoomControl: false,
      preferCanvas: false
    }});
    L.control.zoom({{ position: 'topright' }}).addTo(map);
    L.control.scale({{ metric: true, imperial: false, position: 'bottomleft' }}).addTo(map);

    map.createPane('basinPane');
    map.createPane('basinOutlinePane');
    map.createPane('riverPane');
    map.createPane('stationPane');
    map.createPane('highlightPane');
    map.getPane('basinPane').style.zIndex = 410;
    map.getPane('basinOutlinePane').style.zIndex = 425;
    map.getPane('riverPane').style.zIndex = 440;
    map.getPane('stationPane').style.zIndex = 455;
    map.getPane('highlightPane').style.zIndex = 480;
    map.getPane('basinOutlinePane').style.pointerEvents = 'none';

    const carto = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      maxZoom: 19
    }}).addTo(map);
    const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }});
    const esriImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Tiles &copy; Esri',
      maxZoom: 19
    }});

    const orderedBasinFeatures = [...BASINS.features].sort((a, b) => {{
      const byArea = Number(b.properties.area_km2) - Number(a.properties.area_km2);
      if (byArea !== 0) {{
        return byArea;
      }}
      return String(a.properties.river).localeCompare(String(b.properties.river));
    }});
    const ORDERED_BASINS = {{
      type: 'FeatureCollection',
      features: orderedBasinFeatures
    }};

    const riverSelect = document.getElementById('riverSelect');
    const stationSelect = document.getElementById('stationSelect');
    const controlHint = document.getElementById('controlHint');

    const basinByRiver = new Map();
    const riverLineByRiver = new Map();
    const stationByName = new Map();
    let selectedBasin = null;
    let selectedRiver = null;
    let selectedStation = null;

    function escapeHtml(value) {{
      return String(value ?? 'Not available')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    function popupRow(label, value) {{
      return `<div class="popup-row"><span class="popup-label">${{label}}:</span> ${{escapeHtml(value)}}</div>`;
    }}

    function numberText(value, digits = 2) {{
      if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) {{
        return 'Not available';
      }}
      return Number(value).toLocaleString(undefined, {{
        minimumFractionDigits: 0,
        maximumFractionDigits: digits
      }});
    }}

    function basinStyle(feature) {{
      const river = feature.properties.river;
      return {{
        pane: 'basinPane',
        color: '#243746',
        weight: 1.25,
        opacity: 0.72,
        fillColor: BASIN_COLORS[river] || '#6aa9d8',
        fillOpacity: 0.54
      }};
    }}

    function basinSelectedStyle(feature) {{
      const river = feature.properties.river;
      return {{
        pane: 'highlightPane',
        color: '#071f33',
        weight: 3.3,
        opacity: 1,
        fillColor: BASIN_COLORS[river] || '#6aa9d8',
        fillOpacity: 0.68
      }};
    }}

    function basinHoverStyle(feature) {{
      const river = feature.properties.river;
      return {{
        color: '#081d2e',
        weight: 2.6,
        opacity: 1,
        fillColor: BASIN_COLORS[river] || '#6aa9d8',
        fillOpacity: 0.66
      }};
    }}

    function basinOutlineStyle(feature) {{
      return {{
        pane: 'basinOutlinePane',
        color: '#0f2636',
        weight: 1.65,
        opacity: 0.78,
        fillOpacity: 0,
        dashArray: '3 3',
        interactive: false
      }};
    }}

    function riverStyle(feature) {{
      return {{
        pane: 'riverPane',
        color: feature.properties.confidence_level === 'low' ? '#165c9c' : '#005f9e',
        weight: feature.properties.confidence_level === 'low' ? 2.2 : 2.8,
        opacity: 0.95,
        dashArray: feature.properties.confidence_level === 'low' ? '7 5' : null
      }};
    }}

    function riverSelectedStyle(feature) {{
      return {{
        pane: 'highlightPane',
        color: '#002f57',
        weight: feature.properties.confidence_level === 'low' ? 3.4 : 4,
        opacity: 1,
        dashArray: feature.properties.confidence_level === 'low' ? '7 5' : null
      }};
    }}

    function stationStyle() {{
      return {{
        pane: 'stationPane',
        radius: 6.3,
        color: '#ffffff',
        weight: 1.7,
        fillColor: '#ff9f1c',
        fillOpacity: 0.98
      }};
    }}

    function stationSelectedStyle() {{
      return {{
        pane: 'highlightPane',
        radius: 9.5,
        color: '#102f46',
        weight: 2.3,
        fillColor: '#ffd166',
        fillOpacity: 1
      }};
    }}

    function enforceBasinOrder() {{
      const ordered = Array.from(basinByRiver.values()).sort((a, b) =>
        Number(b.feature.properties.area_km2) - Number(a.feature.properties.area_km2)
      );
      ordered.forEach(layer => {{
        if (layer.bringToFront) {{
          layer.bringToFront();
        }}
      }});
    }}

    function clearSelection() {{
      if (selectedBasin) {{
        selectedBasin.setStyle(basinStyle(selectedBasin.feature));
      }}
      if (selectedRiver) {{
        selectedRiver.setStyle(riverStyle(selectedRiver.feature));
      }}
      if (selectedStation) {{
        selectedStation.setStyle(stationStyle(selectedStation.feature));
      }}
      selectedBasin = null;
      selectedRiver = null;
      selectedStation = null;
      enforceBasinOrder();
    }}

    const basinLayer = L.geoJSON(ORDERED_BASINS, {{
      pane: 'basinPane',
      style: basinStyle,
      onEachFeature: (feature, layer) => {{
        const props = feature.properties;
        layer.bindPopup(`
          <div class="popup-title">${{escapeHtml(props.display_name)}}</div>
          ${{popupRow('River', props.river)}}
          ${{popupRow('Basin area (km2)', numberText(props.area_km2, 2))}}
          ${{popupRow('Confidence', props.confidence_level)}}
        `);
        basinByRiver.set(props.river, layer);
        layer.on({{
          mouseover: () => {{
            if (layer !== selectedBasin) {{
              layer.setStyle(basinHoverStyle(feature));
            }}
            layer.bringToFront();
            controlHint.textContent = `Hovering basin: ${{props.river}}`;
          }},
          mouseout: () => {{
            if (layer !== selectedBasin) {{
              layer.setStyle(basinStyle(feature));
              enforceBasinOrder();
            }}
            controlHint.textContent = 'Select a river or gauge to zoom and highlight.';
          }},
          click: () => selectRiver(props.river, true)
        }});
      }}
    }}).addTo(map);
    enforceBasinOrder();

    const basinOutlineLayer = L.geoJSON(ORDERED_BASINS, {{
      pane: 'basinOutlinePane',
      interactive: false,
      style: basinOutlineStyle
    }}).addTo(map);

    const riverLayer = L.geoJSON(RIVERS, {{
      pane: 'riverPane',
      style: riverStyle,
      onEachFeature: (feature, layer) => {{
        const props = feature.properties;
        layer.bindPopup(`
          <div class="popup-title">${{escapeHtml(props.display_name)}}</div>
          ${{popupRow('River', props.river)}}
          ${{popupRow('Confidence', props.confidence_level)}}
          ${{popupRow('Source', props.geometry_source)}}
        `);
        riverLineByRiver.set(props.river, layer);
        layer.on('click', () => selectRiver(props.river, false));
      }}
    }}).addTo(map);

    const stationLayer = L.geoJSON(STATIONS, {{
      pane: 'stationPane',
      pointToLayer: (feature, latlng) => L.circleMarker(latlng, stationStyle(feature)),
      onEachFeature: (feature, layer) => {{
        const props = feature.properties;
        layer.bindPopup(`
          <div class="popup-title">${{escapeHtml(props.display_name)}}</div>
          ${{popupRow('River', props.river)}}
          ${{popupRow('Coordinates', `${{numberText(props.latitude, 5)}}, ${{numberText(props.longitude, 5)}}`)}}
        `);
        stationByName.set(props.station_name, layer);
        layer.on('click', () => selectStation(props.station_name));
      }}
    }}).addTo(map);

    function selectRiver(river, preferBasinPopup = true) {{
      clearSelection();
      riverSelect.value = river;
      stationSelect.value = '';
      selectedBasin = basinByRiver.get(river) || null;
      selectedRiver = riverLineByRiver.get(river) || null;
      if (selectedBasin) {{
        selectedBasin.setStyle(basinSelectedStyle(selectedBasin.feature));
        selectedBasin.bringToFront();
      }}
      if (selectedRiver) {{
        selectedRiver.setStyle(riverSelectedStyle(selectedRiver.feature));
        selectedRiver.bringToFront();
      }}
      const target = selectedBasin || selectedRiver;
      if (target && target.getBounds) {{
        map.fitBounds(target.getBounds(), {{ maxZoom: 11, padding: [28, 28] }});
      }}
      if (preferBasinPopup && selectedBasin) {{
        selectedBasin.openPopup();
      }} else if (selectedRiver) {{
        selectedRiver.openPopup();
      }} else if (selectedBasin) {{
        selectedBasin.openPopup();
      }}
      controlHint.textContent = `Selected river: ${{river}}`;
    }}

    function selectStation(stationName) {{
      clearSelection();
      selectedStation = stationByName.get(stationName) || null;
      riverSelect.value = '';
      stationSelect.value = stationName;
      if (!selectedStation) {{
        controlHint.textContent = 'Gauge not found.';
        return;
      }}
      selectedStation.setStyle(stationSelectedStyle(selectedStation.feature));
      if (selectedStation.bringToFront) {{
        selectedStation.bringToFront();
      }}
      map.setView(selectedStation.getLatLng(), 11);
      selectedStation.openPopup();
      controlHint.textContent = `Selected gauge: ${{stationName}}`;
    }}

    riverSelect.addEventListener('change', event => {{
      if (!event.target.value) {{
        clearSelection();
        controlHint.textContent = 'Select a river or gauge to zoom and highlight.';
        return;
      }}
      selectRiver(event.target.value, true);
    }});

    stationSelect.addEventListener('change', event => {{
      if (!event.target.value) {{
        clearSelection();
        controlHint.textContent = 'Select a river or gauge to zoom and highlight.';
        return;
      }}
      selectStation(event.target.value);
    }});

    L.control.layers(
      {{
        'CARTO Positron': carto,
        'OpenStreetMap': osm,
        'Esri Imagery': esriImagery
      }},
      {{
        'Basins': basinLayer,
        'Basin overlap outlines': basinOutlineLayer,
        'River lines': riverLayer,
        'Stations': stationLayer
      }},
      {{
        collapsed: true,
        position: 'topright'
      }}
    ).addTo(map);

    const legend = L.control({{ position: 'bottomright' }});
    legend.onAdd = function() {{
      const div = L.DomUtil.create('div', 'legend-card');
      div.innerHTML = `
        <div class="legend-title">Layers</div>
        <div class="legend-item"><span class="legend-swatch" style="background:#2fbf71;"></span> Vibrant basins</div>
        <div class="legend-item"><span class="legend-swatch" style="background:#ffffff;border:2px dashed #0f2636;"></span> Overlap outlines</div>
        <div class="legend-item"><span class="legend-swatch" style="background:#005f9e;"></span> River lines</div>
        <div class="legend-item"><span class="legend-point"></span> Gauges</div>
      `;
      return div;
    }};
    legend.addTo(map);

    map.fitBounds(INITIAL_BOUNDS, {{ padding: [20, 20] }});
  </script>
</body>
</html>
"""

def main() -> None:
    ensure_output_dirs()
    basins, rivers, stations = build_layers()

    write_master_gpkg(basins, rivers, stations)
    write_geojson(BASINS_GEOJSON_PATH, basins)
    write_geojson(RIVERS_GEOJSON_PATH, rivers)
    write_geojson(STATIONS_GEOJSON_PATH, stations)

    HTML_MAP_OUTPUT_PATH.write_text(build_html_map(basins, rivers, stations), encoding="utf-8")

    print(f"Wrote {relpath(GPKG_OUTPUT_PATH)} with layers: basins, rivers, stations")
    print(f"Wrote {relpath(BASINS_GEOJSON_PATH)}")
    print(f"Wrote {relpath(RIVERS_GEOJSON_PATH)}")
    print(f"Wrote {relpath(STATIONS_GEOJSON_PATH)}")
    print(f"Wrote {relpath(HTML_MAP_OUTPUT_PATH)}")


if __name__ == "__main__":
    main()
