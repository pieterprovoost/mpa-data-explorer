import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


OBIS_API = "https://api.obis.org"

app = FastAPI(title="MPA Data Explorer")

data_path = Path(__file__).resolve().parent / "data"
static_path = Path(__file__).resolve().parent.parent / "static"
mpa_geojson_path = data_path / "mpas.geojson"


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/mpas")
def mpas() -> FileResponse:
    return FileResponse(mpa_geojson_path, media_type="application/geo+json")


@app.get("/api/nodes")
async def nodes(
    geometry: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    """Contributing OBIS nodes for a geometry with occurrence counts."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        facet_resp, nodes_resp = await asyncio.gather(
            # Facets endpoint for record counts
            client.get(
                f"{OBIS_API}/facet",
                params={
                    "facets": "node_id",
                    "geometry": geometry,
                    "skip": 0,
                    "size": 1000,
                },
            ),
            # Node endpoint for node details
            client.get(f"{OBIS_API}/node", params={"geometry": geometry}),
        )

    facet_items = facet_resp.json().get("results", {}).get("node_id", [])
    nodes_by_id = {
        node["id"]: node for node in nodes_resp.json().get("results", [])
    }

    combined = []
    for item in facet_items:
        node = nodes_by_id.get(item["key"])
        if node is None:
            continue
        combined.append(
            {
                "id": item["key"],
                "name": node.get("name"),
                "records": item.get("records", 0),
            }
        )

    return {
        "total": len(combined),
        "results": combined[skip : skip + size],
    }


if static_path.is_dir():
    assets = static_path / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static_path / "index.html")

    @app.get("/{full_path:path}")
    def app_files(full_path: str) -> FileResponse:
        """Serve a built frontend file, or index.html if the path is unknown."""
        candidate = static_path / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_path / "index.html")
