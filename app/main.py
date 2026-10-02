from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from domain.claim_analysis import AnalyzeRequest, AnalyzeResponse
from engines.errors import ExternalProviderError
from services.fact_check import FactCheckService


app = FastAPI(title="P105 Fact Check", version="0.1.0")
service = FactCheckService()
FRONTEND_PATH = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
app.mount("/frontend", StaticFiles(directory=FRONTEND_PATH.parent), name="frontend")


@app.exception_handler(ExternalProviderError)
async def external_provider_error_handler(request, exc: ExternalProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
        headers={"Retry-After": "30"},
    )


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_PATH)


@app.get("/healthz", include_in_schema=False)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    return service.analyze(request.text)
