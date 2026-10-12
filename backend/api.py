from fastapi import FastAPI
from pydantic import BaseModel

from backend.database import (
    get_emergencies,
    update_emergency_status,
)

app = FastAPI(
    title="Disaster Relief Coordination API",
    version="1.0.0",
)


class StatusUpdate(BaseModel):
    status: str


@app.get("/")
def root():
    return {
        "service": "Disaster Relief Coordination API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/emergencies")
def list_emergencies():
    return {
        "emergencies": get_emergencies(),
    }


@app.patch("/emergencies/{emergency_id}/status")
def change_status(
    emergency_id: str,
    update: StatusUpdate,
):
    update_emergency_status(
        emergency_id,
        update.status,
    )

    return {
        "emergency_id": emergency_id,
        "status": update.status,
    }