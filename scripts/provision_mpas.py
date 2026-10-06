#!/usr/bin/env python3
"""Export selected Colombian MPAs from WDPA polygons to GeoJSON.

Requires geopandas.
"""

from pathlib import Path
import geopandas as gpd
from shapely import set_precision


SIMPLIFY_DEGREES = 0.001
COORD_PRECISION = 0.00001

root_path = Path(__file__).resolve().parents[1]
shapefile_path = root_path / "data/raw/WDPA_WDOECM_Oct2026_Public_SA_shp/WDPA_WDOECM_Oct2026_Public_SA_shp_0/WDPA_WDOECM_Oct2026_Public_SA_shp-polygons.shp"
output_path = root_path / "backend/app/data/mpas.geojson"

mpa_names = {
    "Los Corales del Rosario y de San Bernardo",
    "Tayrona",
    "Gorgona",
    "Malpelo",
    "Old Providence Mc Bean Lagoon",
}


def main():
    if not shapefile_path.exists():
        raise SystemExit(f"Shapefile not found: {shapefile_path}")

    gdf = gpd.read_file(shapefile_path, where="ISO3 = 'COL'")
    gdf = gdf[gdf["NAME"].isin(mpa_names)].copy()

    # Check for missing names
    if len(gdf) != len(mpa_names):
        found = set(gdf["NAME"])
        missing = mpa_names - found
        raise SystemExit(f"Missing names: {sorted(missing)}")

    gdf["name"] = gdf["NAME"]
    gdf["designation"] = gdf["DESIG_ENG"]
    gdf["wdpa_id"] = gdf["SITE_ID"]
    gdf = gdf.to_crs(4326)
    gdf["geometry"] = (
        gdf.geometry.simplify(SIMPLIFY_DEGREES, preserve_topology=True).map(
            lambda g: set_precision(g, grid_size=COORD_PRECISION)
        )
    )

    out = gdf[["name", "designation", "wdpa_id", "geometry"]].sort_values("name")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_file(output_path, driver="GeoJSON")
    print(f"Wrote {len(out)} features to {output_path}")


if __name__ == "__main__":
    main()
