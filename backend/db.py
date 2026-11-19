"""Thin Supabase/PostgreSQL access layer."""
from supabase import create_client, Client

import config

_client: Client | None = None
PAGE = 1000  # Supabase returns max 1000 rows per request by default


def sb() -> Client:
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client


def insert_reading(row: dict) -> dict:
    res = sb().table("readings").insert(row).execute()
    return res.data[0]


def fetch_readings(device_id: str, since_iso: str, max_rows: int = 50000) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while start < max_rows:
        res = (
            sb().table("readings")
            .select("recorded_at,water_level_cm,voltage")
            .eq("device_id", device_id)
            .gte("recorded_at", since_iso)
            .order("recorded_at")
            .range(start, start + PAGE - 1)
            .execute()
        )
        rows += res.data
        if len(res.data) < PAGE:
            break
        start += PAGE
    return rows


def latest_reading(device_id: str) -> dict | None:
    res = (
        sb().table("readings")
        .select("recorded_at,water_level_cm,voltage")
        .eq("device_id", device_id)
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def list_devices() -> list[str]:
    res = sb().table("readings").select("device_id").order("recorded_at", desc=True).limit(1000).execute()
    seen: list[str] = []
    for r in res.data:
        if r["device_id"] not in seen:
            seen.append(r["device_id"])
    return seen
