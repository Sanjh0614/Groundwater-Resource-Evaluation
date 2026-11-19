import {
  Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const STATUS = {
  normal: { label: "Normal", cls: "ok" },
  warning: { label: "Warning", cls: "warn" },
  critical: { label: "Critical", cls: "crit" },
  no_data: { label: "No data", cls: "idle" },
};
const fmt = (v, d = 1) => (v == null ? "—" : Number(v).toFixed(d));

function timeAgo(iso) {
  if (!iso) return "never";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

/* Borewell cross-section: the memorable element of the dashboard */
export function WellGauge({ analytics: a, lastSeen }) {
  const st = STATUS[a.status] || STATUS.no_data;
  const level = a.current_level_cm ?? 0;
  const { warning_cm: warn, critical_cm: crit } = a.thresholds;
  const scale = Math.max(warn * 2.5, level * 1.15, 10);
  const H = 260;
  const y = (cm) => H - Math.min(cm / scale, 1) * H;

  return (
    <div className="gauge panel">
      <div className="gauge-head">
        <span className={`pill ${st.cls}`}>{st.label}</span>
        <span className="muted">{timeAgo(lastSeen)}</span>
      </div>
      <div className="gauge-body">
        <svg viewBox={`0 0 120 ${H + 8}`} className="well" role="img" aria-label={`Water level ${fmt(level)} centimetres`}>
          <rect x="30" y="4" width="60" height={H} rx="4" className="well-wall" />
          <rect x="31" y={4 + y(level)} width="58" height={H - y(level)} className={`water ${st.cls}`} />
          <line x1="24" x2="96" y1={4 + y(warn)} y2={4 + y(warn)} className="mark warn" />
          <line x1="24" x2="96" y1={4 + y(crit)} y2={4 + y(crit)} className="mark crit" />
          <text x="98" y={8 + y(warn)} className="mark-label">warn</text>
          <text x="98" y={8 + y(crit)} className="mark-label">crit</text>
        </svg>
        <div>
          <div className="big">{fmt(a.current_level_cm)}<small> cm</small></div>
          <div className="muted">water column in borewell</div>
        </div>
      </div>
    </div>
  );
}

export function LevelChart({ readings, thresholds }) {
  const data = readings.map((r) => ({ t: new Date(r.recorded_at).getTime(), level: r.water_level_cm }));
  const span = data.length ? data[data.length - 1].t - data[0].t : 0;
  const tick = (t) => {
    const d = new Date(t);
    return span > 2 * 86400000
      ? d.toLocaleDateString([], { day: "numeric", month: "short" })
      : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };
  return (
    <div className="chart panel">
      <h2>Water level history</h2>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2a9096" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#2a9096" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e3eaf0" vertical={false} />
          <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={tick} tick={{ fontSize: 12 }} stroke="#8a9bab" />
          <YAxis domain={[0, (m) => Math.max(Math.ceil(m / 10) * 10, thresholds.warning_cm + 10)]} tick={{ fontSize: 12 }} stroke="#8a9bab" unit=" cm" width={56} />
          <Tooltip labelFormatter={(t) => new Date(t).toLocaleString()} formatter={(v) => [`${Number(v).toFixed(1)} cm`, "Level"]} />
          <ReferenceLine y={thresholds.warning_cm} stroke="#c77d1a" strokeDasharray="5 4" />
          <ReferenceLine y={thresholds.critical_cm} stroke="#b83a3a" strokeDasharray="5 4" />
          <Area type="monotone" dataKey="level" stroke="#17344f" strokeWidth={2} fill="url(#fill)" dot={false} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function Metrics({ analytics: a }) {
  const arrow = { rising: "↑", stable: "→", declining: "↓" }[a.trend] || "";
  const trendCls = { rising: "ok", stable: "", declining: "warn" }[a.trend] || "";
  const slope = a.slope_cm_per_day;
  return (
    <section className="metrics">
      <div>
        <span className="label">Trend</span>
        <strong className={trendCls}>{arrow} {a.trend === "unknown" ? "Not enough data" : a.trend}</strong>
        <span className="muted">{slope == null ? "needs a few hours of readings" : `${slope > 0 ? "+" : ""}${fmt(slope, 2)} cm/day`}</span>
      </div>
      <div>
        <span className="label">Depletion rate</span>
        <strong>{a.depletion_rate_cm_per_day == null ? "—" : `${fmt(a.depletion_rate_cm_per_day, 2)} cm/day`}</strong>
        <span className="muted">{a.depletion_rate_cm_per_day === 0 ? "level is not falling" : "average fall over the range"}</span>
      </div>
      <div>
        <span className="label">Time to critical level</span>
        <strong>{a.days_to_critical == null ? "—" : a.days_to_critical === 0 ? "Reached" : `${fmt(a.days_to_critical)} days`}</strong>
        <span className="muted">if the current trend continues</span>
      </div>
      <div>
        <span className="label">Forecast confidence</span>
        <strong>{a.confidence === "none" ? "—" : a.confidence}</strong>
        <span className="muted">{a.points_used} readings over {fmt(a.window_span_days, 1)} days</span>
      </div>
    </section>
  );
}

export function Forecast({ analytics: a }) {
  return (
    <div className="panel">
      <h2>Level forecast</h2>
      {a.predictions.length === 0 ? (
        <p className="muted">Forecasts appear once there are a few hours of readings.</p>
      ) : (
        <table>
          <thead><tr><th>In</th><th>Expected level</th><th>Likely range</th><th>Status</th></tr></thead>
          <tbody>
            {a.predictions.map((p) => (
              <tr key={p.days}>
                <td>{p.days} days</td>
                <td><strong>{fmt(p.level_cm)} cm</strong></td>
                <td>{fmt(p.low_cm)} – {fmt(p.high_cm)} cm</td>
                <td><span className={`pill ${STATUS[p.status].cls}`}>{STATUS[p.status].label}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {a.confidence === "low" && a.predictions.length > 0 && (
        <p className="note">Based on under a day of data, so treat the 30- and 90-day values as rough.</p>
      )}
    </div>
  );
}

export function Alerts({ alerts }) {
  return (
    <div className="panel">
      <h2>Alerts</h2>
      {alerts.length === 0 ? (
        <p className="muted">No active alerts. Level and depletion rate are within limits.</p>
      ) : (
        <ul className="alerts">
          {alerts.map((al, i) => (
            <li key={i} className={al.severity}>
              <span className={`pill ${al.severity === "critical" ? "crit" : "warn"}`}>{al.severity}</span>
              {al.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
