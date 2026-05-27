from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": settings.app_name,
        "docs": "/docs",
        "telemetry_endpoint": "/api/v1/telemetry",
    }
