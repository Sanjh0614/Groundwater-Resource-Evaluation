"""
Time-series analytics for groundwater level.

Level = height of water column in cm (higher = more water).
Pipeline: bucket-average -> linear regression -> trend, depletion rate,
7/30/90-day forecast with an uncertainty band -> alerts.
Needs Python 3.11+.
"""
from datetime import datetime, timezone

import numpy as np

import config

HORIZONS = (7, 30, 90)


def parse_ts(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def downsample(rows: list[dict], max_points: int = 500) -> list[dict]:
    """Average consecutive chunks so charts stay light."""
    n = len(rows)
    if n <= max_points:
        return rows
    size = int(np.ceil(n / max_points))
    out = []
    for i in range(0, n, size):
        chunk = rows[i:i + size]
        out.append({
            "recorded_at": chunk[-1]["recorded_at"],
            "water_level_cm": round(float(np.mean([c["water_level_cm"] for c in chunk])), 2),
        })
    return out


def _bucketed(rows: list[dict]):
    """Average readings into 5-min buckets (short spans) or 1-h buckets (>= 6 h)."""
    stamps = [parse_ts(r["recorded_at"]).timestamp() for r in rows]
    span = stamps[-1] - stamps[0]
    bucket = 300 if span < 6 * 3600 else 3600
    groups: dict[int, list[float]] = {}
    for ts, r in zip(stamps, rows):
        groups.setdefault(int(ts // bucket) * bucket, []).append(r["water_level_cm"])
    keys = sorted(groups)
    t = np.array([(k - keys[0]) / 86400 for k in keys])  # days since first bucket
    y = np.array([np.mean(groups[k]) for k in keys])
    return t, y


def _level_status(level: float) -> str:
    if level <= config.CRITICAL_LEVEL_CM:
        return "critical"
    if level <= config.WARNING_LEVEL_CM:
        return "warning"
    return "normal"


def _alert(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def analyse(rows: list[dict], last_seen: datetime | None = None) -> dict:
    now = datetime.now(timezone.utc)
    out = {
        "status": "no_data",
        "current_level_cm": None,
        "trend": "unknown",
        "slope_cm_per_day": None,
        "depletion_rate_cm_per_day": None,
        "days_to_critical": None,
        "confidence": "none",
        "window_span_days": 0,
        "points_used": len(rows),
        "predictions": [],
        "alerts": [],
        "thresholds": {
            "warning_cm": config.WARNING_LEVEL_CM,
            "critical_cm": config.CRITICAL_LEVEL_CM,
        },
    }
    alerts = out["alerts"]

    if last_seen is not None:
        idle_min = (now - last_seen).total_seconds() / 60
        if idle_min > config.OFFLINE_MINUTES:
            alerts.append(_alert("warning", "offline", f"No data received for {int(idle_min)} min. Check the sensor node."))

    if not rows:
        return out

    current = float(rows[-1]["water_level_cm"])
    out["current_level_cm"] = round(current, 2)

    level_state = _level_status(current)
    if level_state == "critical":
        alerts.append(_alert("critical", "level", f"Water level {current:.1f} cm is at or below the critical limit ({config.CRITICAL_LEVEL_CM:g} cm)."))
    elif level_state == "warning":
        alerts.append(_alert("warning", "level", f"Water level {current:.1f} cm is at or below the warning limit ({config.WARNING_LEVEL_CM:g} cm)."))

    t, y = _bucketed(rows)
    span = float(t[-1] - t[0]) if len(t) else 0.0
    out["window_span_days"] = round(span, 2)

    if len(t) >= 3 and span > 0:
        slope, intercept = np.polyfit(t, y, 1)
        slope = float(slope)
        resid_std = float(np.std(y - (slope * t + intercept)))

        out["slope_cm_per_day"] = round(slope, 3)
        out["depletion_rate_cm_per_day"] = round(max(0.0, -slope), 3)
        out["confidence"] = "high" if span >= 7 else "medium" if span >= 1 else "low"

        if abs(slope) < config.STABLE_SLOPE_CM_PER_DAY:
            out["trend"] = "stable"
        else:
            out["trend"] = "rising" if slope > 0 else "declining"

        if slope < 0:
            out["days_to_critical"] = round(max(0.0, (current - config.CRITICAL_LEVEL_CM) / -slope), 1)

        for h in HORIZONS:
            pred = slope * (t[-1] + h) + intercept
            band = 1.96 * resid_std * float(np.sqrt(1 + h / max(span, 1.0)))
            pred_c = max(0.0, float(pred))
            out["predictions"].append({
                "days": h,
                "level_cm": round(pred_c, 1),
                "low_cm": round(max(0.0, pred_c - band), 1),
                "high_cm": round(pred_c + band, 1),
                "status": _level_status(pred_c),
            })

        rate = out["depletion_rate_cm_per_day"]
        if rate >= config.RATE_CRITICAL_CM_PER_DAY:
            alerts.append(_alert("critical", "rate", f"Level is falling fast: {rate:.1f} cm/day."))
        elif rate >= config.RATE_WARNING_CM_PER_DAY:
            alerts.append(_alert("warning", "rate", f"Level is falling at {rate:.1f} cm/day."))

        p30 = next(p for p in out["predictions"] if p["days"] == 30)
        if level_state == "normal" and p30["level_cm"] <= config.CRITICAL_LEVEL_CM:
            alerts.append(_alert("warning", "forecast", f"At the current rate the level may reach the critical limit within 30 days (forecast {p30['level_cm']:.1f} cm)."))

    severities = {a["severity"] for a in alerts}
    out["status"] = "critical" if "critical" in severities else "warning" if "warning" in severities else "normal"
    return out
