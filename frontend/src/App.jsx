import { useCallback, useEffect, useState } from "react";
import { getDashboard, getDevices } from "./api";
import { Alerts, Forecast, LevelChart, Metrics, WellGauge } from "./components/panels.jsx";

const RANGES = [
  { days: 1, label: "24 hours" },
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
];
const REFRESH_MS = 10000;

export default function App() {
  const [devices, setDevices] = useState([]);
  const [deviceId, setDeviceId] = useState("");
  const [days, setDays] = useState(7);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loadedDevices, setLoadedDevices] = useState(false);
  const [updated, setUpdated] = useState(null);

  useEffect(() => {
    getDevices()
      .then((list) => {
        setDevices(list);
        if (list.length) setDeviceId(list[0]);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadedDevices(true));
  }, []);

  const load = useCallback(async () => {
    if (!deviceId) return;
    try {
      setData(await getDashboard(deviceId, days));
      setError("");
      setUpdated(new Date());
    } catch (e) {
      setError(e.message);
    }
  }, [deviceId, days]);

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  const a = data?.analytics;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Groundwater Monitor</h1>
          <p>Real-time resource evaluation from DWLR sensor data</p>
        </div>
        <div className="controls">
          <label>
            Sensor node
            <select value={deviceId} onChange={(e) => { setData(null); setDeviceId(e.target.value); }}>
              {devices.map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
          <label>
            Time range
            <select value={days} onChange={(e) => { setData(null); setDays(Number(e.target.value)); }}>
              {RANGES.map((r) => <option key={r.days} value={r.days}>{r.label}</option>)}
            </select>
          </label>
        </div>
      </header>

      <main>
        {error && <div className="banner" role="alert">{error}</div>}

        {loadedDevices && !devices.length && !error && (
          <div className="empty">
            <h2>No readings yet</h2>
            <p>Power on the ESP32 node, or load sample data with <code>python seed_demo.py</code> in the backend folder.</p>
          </div>
        )}

        {data && a && (
          <>
            <section className="hero">
              <WellGauge analytics={a} lastSeen={data.latest?.recorded_at} />
              <LevelChart readings={data.readings} thresholds={a.thresholds} />
            </section>
            <Metrics analytics={a} />
            <section className="lower">
              <Forecast analytics={a} />
              <Alerts alerts={a.alerts} />
            </section>
            <footer>
              {updated && <>Refreshed {updated.toLocaleTimeString()} · updates every {REFRESH_MS / 1000} s · </>}
              Forecast uses a linear trend over the selected range.
            </footer>
          </>
        )}
        {deviceId && !data && !error && <p className="loading">Loading readings…</p>}
      </main>
    </div>
  );
}
