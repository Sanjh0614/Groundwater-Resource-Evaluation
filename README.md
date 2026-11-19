# Real-Time Groundwater Resource Evaluation: software

ESP32 -> FastAPI -> Supabase (PostgreSQL) -> analytics -> React + Vite dashboard

## 1. Database (Supabase)
1. Create a project at supabase.com.
2. SQL Editor -> paste and run `backend/schema.sql`.
3. Project Settings -> API: copy the Project URL and the **service_role** key.

## 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, DEVICE_API_KEY
python seed_demo.py --days 30                          # optional: demo data, no hardware needed
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
API docs: http://localhost:8000/docs  (Python 3.11+ required)

## 3. Dashboard
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

## 4. ESP32
Open `esp32/groundwater_node.ino`, set Wi-Fi, `API_URL` (your PC's LAN IP), `API_KEY`, and calibration values, then flash.
Test without hardware:
```bash
curl -X POST http://localhost:8000/api/readings -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" -d '{"device_id":"node-1","water_level_cm":62.5}'
```

## API
| Method | Path | Purpose |
|---|---|---|
| POST | /api/readings | ESP32 upload (needs X-API-Key) |
| GET | /api/dashboard?device_id=&days= | latest + analytics + chart data |
| GET | /api/analytics, /api/readings, /api/devices | individual pieces |

## How the analytics work
Readings are bucket-averaged, then a least-squares line gives the slope (cm/day).
Trend = rising/stable/declining by slope threshold; depletion rate = max(0, -slope);
forecast = line extended 7/30/90 days with a widening 95% band; alerts come from level
thresholds, depletion rate, 30-day forecast and a "node offline" check. All thresholds are in `backend/.env`.

## Deploying
Backend -> Render/Railway (start: `uvicorn main:app --host 0.0.0.0 --port $PORT`), frontend -> Vercel/Netlify
with `VITE_API_URL` set, and add the frontend URL to `CORS_ORIGINS`.
