from fastapi import FastAPI


app = FastAPI(title="MPA Data Explorer")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
