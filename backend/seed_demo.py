"""
Fill the database with realistic demo data so the dashboard works before the hardware does.
Usage (from backend/):  python seed_demo.py --days 30 --device demo-node
"""
import argparse
import math
import random
from datetime import datetime, timedelta, timezone

from db import sb

p = argparse.ArgumentParser()
p.add_argument("--device", default="demo-node")
p.add_argument("--days", type=int, default=30)
p.add_argument("--start", type=float, default=70.0, help="starting level in cm")
p.add_argument("--decline", type=float, default=1.1, help="average fall in cm/day")
p.add_argument("--every-min", type=int, default=30)
a = p.parse_args()

now = datetime.now(timezone.utc)
begin = now - timedelta(days=a.days)
rows, i = [], 0
while True:
    ts = begin + timedelta(minutes=a.every_min * i)
    if ts > now:
        break
    d = (ts - begin).total_seconds() / 86400
    level = a.start - a.decline * d
    level += 0.8 * math.sin(2 * math.pi * d)                      # daily pumping cycle
    if d > 12:
        level += 5 * math.exp(-(d - 12) / 1.5)                    # one rain/recharge event
    level += random.gauss(0, 0.3)                                 # sensor noise
    rows.append({"device_id": a.device, "water_level_cm": round(max(level, 0), 2),
                 "voltage": round(0.5 + level * 0.0005, 4), "recorded_at": ts.isoformat()})
    i += 1

for k in range(0, len(rows), 500):
    sb().table("readings").insert(rows[k:k + 500]).execute()
print(f"Inserted {len(rows)} readings for '{a.device}'")
