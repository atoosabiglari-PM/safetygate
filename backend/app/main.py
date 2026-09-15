from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.agents import router as agents_router
from app.api.operator import router as operator_router
from app.api.passports import router as passports_router
from app.api.router import router as api_router
from app.api.runtime import router as runtime_router

app = FastAPI(
    title="SafetyGate",
    description="Independent governance and runtime authorization layer for AI agents",
    version="0.1.0",
)

app.include_router(api_router)
app.include_router(agents_router)
app.include_router(passports_router)
app.include_router(runtime_router)
app.include_router(operator_router)

app.mount(
    "/static",
    StaticFiles(directory="backend/app/static"),
    name="static",
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/portal", status_code=307)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "safetygate",
        "version": "0.1.0",
    }


@app.get("/portal", include_in_schema=False)
def client_portal() -> FileResponse:
    return FileResponse("backend/app/static/index.html")


@app.get("/operator", include_in_schema=False)
def operator_console() -> FileResponse:
    return FileResponse("backend/app/static/operator.html")
