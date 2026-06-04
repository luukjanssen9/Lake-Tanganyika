import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import { DATA_PATHS } from "../lib/constants";
import { loadJson } from "../lib/dataLoader";

type FeatureCollection = {
  type: "FeatureCollection";
  features: Array<Record<string, any>>;
};

const emptyCollection: FeatureCollection = { type: "FeatureCollection", features: [] };

function safe(value: unknown) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const escaped: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return escaped[char];
  });
}

function popupTable(rows: Array<[string, unknown]>) {
  return `<div class="map-popup">${rows
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .map(([label, value]) => `<div><strong>${safe(label)}</strong><span>${safe(value)}</span></div>`)
    .join("")}</div>`;
}

function boundsFor(features: Array<Record<string, any>>) {
  if (!features.length) return null;
  const layer = L.geoJSON({ type: "FeatureCollection", features } as any);
  const bounds = layer.getBounds();
  return bounds.isValid() ? bounds : null;
}

function MapController({
  basins,
  rivers,
  stations,
  selectedRiver,
  selectedStation,
}: {
  basins: FeatureCollection;
  rivers: FeatureCollection;
  stations: FeatureCollection;
  selectedRiver: string;
  selectedStation: string;
}) {
  const map = useMap();
  const fitted = useRef(false);

  useEffect(() => {
    if (fitted.current) return;
    const bounds = boundsFor([...basins.features, ...rivers.features, ...stations.features]);
    if (bounds) {
      map.fitBounds(bounds.pad(0.08), { animate: false });
      fitted.current = true;
    }
  }, [basins, rivers, stations, map]);

  useEffect(() => {
    if (!selectedRiver) return;
    const features = [...basins.features, ...rivers.features].filter((feature) => feature.properties?.river === selectedRiver);
    const bounds = boundsFor(features);
    if (bounds) map.fitBounds(bounds.pad(0.12), { animate: true });
  }, [basins, rivers, selectedRiver, map]);

  useEffect(() => {
    if (!selectedStation) return;
    const station = stations.features.find((feature) => feature.properties?.station_name === selectedStation);
    const coords = station?.geometry?.coordinates;
    if (Array.isArray(coords) && coords.length >= 2) {
      map.setView([coords[1], coords[0]], 11, { animate: true });
    }
  }, [stations, selectedStation, map]);

  return null;
}

export default function LakeMap({ preview = false }: { preview?: boolean }) {
  const [basins, setBasins] = useState<FeatureCollection>(emptyCollection);
  const [rivers, setRivers] = useState<FeatureCollection>(emptyCollection);
  const [stations, setStations] = useState<FeatureCollection>(emptyCollection);
  const [warning, setWarning] = useState("");
  const [selectedRiver, setSelectedRiver] = useState("");
  const [selectedStation, setSelectedStation] = useState("");
  const [layers, setLayers] = useState({ basins: true, rivers: true, stations: true });

  useEffect(() => {
    let active = true;
    Promise.all([
      loadJson<FeatureCollection>(DATA_PATHS.map.basins, emptyCollection),
      loadJson<FeatureCollection>(DATA_PATHS.map.rivers, emptyCollection),
      loadJson<FeatureCollection>(DATA_PATHS.map.stations, emptyCollection),
    ]).then(([basinResult, riverResult, stationResult]) => {
      if (!active) return;
      setBasins(basinResult.data);
      setRivers(riverResult.data);
      setStations(stationResult.data);
      setWarning([basinResult.warning, riverResult.warning, stationResult.warning].filter(Boolean).join(" "));
    });
    return () => {
      active = false;
    };
  }, []);

  const riverOptions = useMemo(() => {
    return Array.from(
      new Set(
        [...basins.features, ...rivers.features, ...stations.features]
          .map((feature) => feature.properties?.river)
          .filter(Boolean),
      ),
    ).sort((a, b) => a.localeCompare(b));
  }, [basins, rivers, stations]);

  const stationOptions = useMemo(() => {
    return stations.features
      .map((feature) => feature.properties?.station_name)
      .filter(Boolean)
      .sort((a, b) => a.localeCompare(b));
  }, [stations]);

  const basinStyle = (feature?: any) => {
    const selected = selectedRiver && feature?.properties?.river === selectedRiver;
    return {
      color: selected ? "#0b3d91" : "#2f68b1",
      weight: selected ? 3 : 1.5,
      fillColor: "#8ecae6",
      fillOpacity: selected ? 0.42 : 0.26,
    };
  };

  const riverStyle = (feature?: any) => {
    const selected = selectedRiver && feature?.properties?.river === selectedRiver;
    return {
      color: selected ? "#003f88" : "#006dba",
      weight: selected ? 4.5 : 2.8,
      opacity: selected ? 1 : 0.9,
    };
  };

  const layerLabels = {
    basins: "Basins",
    rivers: "Rivers",
    stations: "Gauges",
  };

  return (
    <div className={preview ? "map-preview" : "map-module"}>
      {!preview ? (
        <div className="map-controls">
          <label>
            River
            <select value={selectedRiver} onChange={(event) => setSelectedRiver(event.target.value)}>
              <option value="">All rivers</option>
              {riverOptions.map((river) => (
                <option key={river} value={river}>
                  {river}
                </option>
              ))}
            </select>
          </label>
          <label>
            Station
            <select value={selectedStation} onChange={(event) => setSelectedStation(event.target.value)}>
              <option value="">All stations</option>
              {stationOptions.map((station) => (
                <option key={station} value={station}>
                  {station}
                </option>
              ))}
            </select>
          </label>
          <div className="toggle-group" aria-label="Map layer toggles">
            {(["basins", "rivers", "stations"] as const).map((layer) => (
              <label key={layer} className="toggle-pill">
                <input
                  type="checkbox"
                  checked={layers[layer]}
                  onChange={(event) => setLayers((current) => ({ ...current, [layer]: event.target.checked }))}
                />
                {layerLabels[layer]}
              </label>
            ))}
          </div>
        </div>
      ) : null}

      {warning ? <p className="warning">{warning}</p> : null}
      <div className="map-frame">
        <MapContainer center={[-3.7, 29.45]} zoom={7} scrollWheelZoom={!preview} dragging={!preview} zoomControl={!preview}>
          <TileLayer
            attribution="&copy; OpenStreetMap contributors &copy; CARTO"
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <MapController
            basins={basins}
            rivers={rivers}
            stations={stations}
            selectedRiver={selectedRiver}
            selectedStation={selectedStation}
          />
          {layers.basins ? (
            <GeoJSON
              key={`basins-${selectedRiver}-${basins.features.length}`}
              data={basins as any}
              style={basinStyle}
              onEachFeature={(feature, layer) => {
                const p = feature.properties || {};
                layer.bindPopup(
                  popupTable([
                    ["Basin", p.display_name],
                    ["River", p.river],
                    ["Area km2", p.area_km2],
                  ]),
                );
              }}
            />
          ) : null}
          {layers.rivers ? (
            <GeoJSON
              key={`rivers-${selectedRiver}-${rivers.features.length}`}
              data={rivers as any}
              style={riverStyle}
              onEachFeature={(feature, layer) => {
                const p = feature.properties || {};
                layer.bindPopup(
                  popupTable([
                    ["River", p.display_name],
                    ["Name", p.river],
                    ["Geometry source", p.geometry_source],
                  ]),
                );
              }}
            />
          ) : null}
          {layers.stations ? (
            <GeoJSON
              key={`stations-${selectedStation}-${stations.features.length}`}
              data={stations as any}
              pointToLayer={(feature, latlng) => {
                const selected = selectedStation && feature.properties?.station_name === selectedStation;
                return L.circleMarker(latlng, {
                  radius: selected ? 8.5 : 6.5,
                  fillColor: selected ? "#c02626" : "#f97316",
                  color: "#ffffff",
                  weight: 2,
                  fillOpacity: 0.95,
                });
              }}
              onEachFeature={(feature, layer) => {
                const p = feature.properties || {};
                layer.bindPopup(
                  popupTable([
                    ["Station", p.station_name],
                    ["River", p.river],
                    ["Latitude", p.latitude],
                    ["Longitude", p.longitude],
                  ]),
                );
              }}
            />
          ) : null}
        </MapContainer>
      </div>
    </div>
  );
}
