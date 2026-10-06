from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse


app = FastAPI(title="MPA Data Explorer")
mpa_geojson_path = Path(__file__).resolve().parent / "data" / "mpas.geojson"


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/mpas")
def mpas() -> FileResponse:
    return FileResponse(mpa_geojson_path, media_type="application/geo+json")
