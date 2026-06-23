import "./StatsGrid.css";

function StatCard({ label, value, unit, color, icon }) {
  return (
    <div className="stat-card" style={{ borderTopColor: color }}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-body">
        <span className="stat-label">{label}</span>
        <div className="stat-value-row">
          <span className="stat-value" style={{ color }}>
            {value ?? "—"}
          </span>
          {unit && <span className="stat-unit">{unit}</span>}
        </div>
      </div>
    </div>
  );
}

export default function StatsGrid({ stats }) {
  if (!stats) return null;

  const uptime = stats.session_minutes
    ? stats.session_minutes >= 60
      ? `${Math.floor(stats.session_minutes / 60)}h ${Math.round(stats.session_minutes % 60)}m`
      : `${stats.session_minutes}m`
    : "—";

  const detRate =
    stats.total_frames > 0
      ? Math.round(((stats.fire_detections + stats.smoke_detections) / stats.total_frames) * 100)
      : 0;

  return (
    <div className="panel stats-panel">
      <div className="panel-header">
        <span className="panel-title">SESSION METRICS</span>
      </div>

      <div className="stats-grid">
        <StatCard
          label="FRAMES ANALYSED"
          value={stats.total_frames?.toLocaleString()}
          color="#1E5FA8"
          icon="⬛"
        />
        <StatCard
          label="FIRE EVENTS"
          value={stats.fire_detections}
          color="#E84040"
          icon="🔥"
        />
        <StatCard
          label="SMOKE EVENTS"
          value={stats.smoke_detections}
          color="#7E8B98"
          icon="💨"
        />
        <StatCard
          label="ALERTS TRIGGERED"
          value={stats.alerts_triggered}
          color="#F5A623"
          icon="🚨"
        />
        <StatCard
          label="DETECTION RATE"
          value={detRate}
          unit="%"
          color="#9B59B6"
          icon="📊"
        />
        <StatCard
          label="SESSION UPTIME"
          value={uptime}
          color="#2E9E6A"
          icon="⏱"
        />
      </div>

      {/* Mini sparkline for last‑detection time */}
      {stats.last_detection && (
        <div className="last-detection">
          <span className="last-det-label">LAST DETECTION</span>
          <span className="last-det-time">
            {new Date(stats.last_detection * 1000).toLocaleTimeString("en-GB")}
          </span>
        </div>
      )}
    </div>
  );
}
