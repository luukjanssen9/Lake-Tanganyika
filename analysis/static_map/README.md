# Static Map Package

This folder is a portable static map package for the Lake Tanganyika rivers map.
It contains the required source data, one standalone build script, and generated outputs.

## Run

From this folder:

```bash
python build_static_map.py
```

The script writes all generated files to `outputs/`.

## Inputs

- `data/basins/basins.gpkg`: basin polygons, layer `river_basins`.
- `data/hydrorivers/hydrorivers_africa.*`: HydroRIVERS shapefile bundle used for contextual river lines.
- `data/reach_review.csv`: reviewed HydroRIVERS reach choices and confidence labels.
- `data/water_levels/water_level_*.xlsx`: raw gauge workbooks used for station labels and coordinates.

## Outputs

- `outputs/static_map_layers.gpkg`: master GeoPackage with `basins`, `rivers`, and `stations`.
- `outputs/basins.geojson`: web-ready basin layer.
- `outputs/rivers.geojson`: web-ready river layer.
- `outputs/stations.geojson`: web-ready station layer.
- `outputs/static_map.html`: standalone Leaflet map.
