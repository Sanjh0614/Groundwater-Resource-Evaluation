"""FastAPI backend: ESP32 ingest + dashboard API.  Run: uvicorn main:app --reload"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from analytics import analyse, downsample, parse_ts
from db import fetch_readings, insert_reading, latest_reading, list_devices

app = FastAPI(title="Groundwater Monitoring API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReadingIn(BaseModel):
    device_id: str = Field("node-1", max_length=64)
    water_level_cm: float = Field(..., ge=0, le=100000)
    voltage: float | None = None
    recorded_at: datetime | None = None  # ESP32 usually omits it; server time is used


def require_device_key(x_api_key: str | None = Header(default=None)):
    if not config.DEVICE_API_KEY or not secrets.compare_digest(x_api_key or "", config.DEVICE_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/readings", status_code=201, dependencies=[Depends(require_device_key)])
def post_reading(body: ReadingIn):
    row = {
        "device_id": body.device_id,
        "water_level_cm": body.water_level_cm,
        "voltage": body.voltage,
    }
    if body.recorded_at:
        row["recorded_at"] = body.recorded_at.isoformat()
    return insert_reading(row)


@app.get("/api/devices")
def devices():
    return list_devices()


@app.get("/api/readings")
def readings(device_id: str = "node-1", hours: int = Query(24, ge=1, le=24 * 90), max_points: int = Query(500, ge=10, le=5000)):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return downsample(fetch_readings(device_id, since), max_points)


@app.get("/api/analytics")
def analytics(device_id: str = "node-1", days: int = Query(7, ge=1, le=90)):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = fetch_readings(device_id, since)
    latest = latest_reading(device_id)
    return analyse(rows, parse_ts(latest["recorded_at"]) if latest else None)


@app.get("/api/dashboard")
def dashboard(device_id: str = "node-1", days: int = Query(7, ge=1, le=90)):
    """Everything the dashboard needs in one request."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = fetch_readings(device_id, since)
    latest = latest_reading(device_id)
    last_seen = parse_ts(latest["recorded_at"]) if latest else None
    return {
        "device_id": device_id,
        "days": days,
        "latest": latest,
        "analytics": analyse(rows, last_seen),
        "readings": downsample(rows, 500),
    }
