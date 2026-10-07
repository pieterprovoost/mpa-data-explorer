import asyncio
import csv
import io
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
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


@app.get("/api/institutes")
async def institutes(
    geometry: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    """Contributing institutes for a geometry with occurrence counts."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{OBIS_API}/institute",
            params={"geometry": geometry, "skip": skip, "size": size},
        )

    data = resp.json()
    return {
        "total": data.get("total", 0),
        "results": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "records": item.get("records", 0),
            }
            for item in data.get("results", [])
        ],
    }


@app.get("/api/years")
async def years(
    geometry: str = Query(..., min_length=1),
) -> dict:
    """Presence records per year for a geometry."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{OBIS_API}/statistics/years",
            params={"geometry": geometry},
        )

    results = [
        {"year": item["year"], "records": item.get("records", 0)}
        for item in resp.json()
        if item.get("year") is not None
    ]
    return {"total": len(results), "results": results}


@app.get("/api/taxonomy")
async def taxonomy(
    geometry: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=100),
) -> dict:
    """Top-level taxonomic groups for a geometry with occurrence counts."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{OBIS_API}/statistics/taxonomy",
            params={"geometry": geometry},
        )

    children = resp.json().get("children") or []
    results = [
        {
            "name": item.get("name"),
            "records": item.get("value", 0),
        }
        for item in children
        if item.get("name")
    ]
    results.sort(key=lambda row: row["records"], reverse=True)
    return {
        "total": len(results),
        "results": results[skip : skip + size],
    }


@app.get("/api/occurrences.csv")
async def occurrences_csv(
    geometry: str = Query(..., min_length=1),
) -> Response:
    """All OBIS occurrences for a geometry as CSV."""
    page_size = 10000
    results = []
    after = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            params = {"geometry": geometry, "size": page_size}
            if after is not None:
                params["after"] = after

            resp = await client.get(f"{OBIS_API}/occurrence", params=params)
            page = resp.json().get("results") or []
            if not page:
                break

            for row in page:
                results.append(
                    {
                        key: value
                        for key, value in row.items()
                        if not isinstance(value, (dict, list))
                    }
                )

            # Use the last id for pagination
            after = page[-1].get("id")
            if after is None or len(page) < page_size:
                break

    fieldnames = sorted({key for row in results for key in row})
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(results)

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"occurrences.csv\""},
    )


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
