from fastapi import FastAPI

app = FastAPI(
    title="SafetyGate",
    description="Independent governance and runtime authorization layer for AI agents",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "safetygate",
        "version": "0.1.0",
    }
