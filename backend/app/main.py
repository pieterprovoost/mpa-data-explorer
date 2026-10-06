from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


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
