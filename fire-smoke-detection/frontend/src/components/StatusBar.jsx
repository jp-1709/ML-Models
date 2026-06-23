import "./StatusBar.css";

export default function StatusBar({ health, isRunning, cameraActive }) {
  const apiOk = health?.status === "operational";
  const modelOk = health?.model_loaded;

  const indicators = [
    {
      label: "API",
      ok: apiOk,
      detail: apiOk ? "CONNECTED" : "OFFLINE",
    },
    {
      label: "MODEL",
      ok: modelOk,
      detail: modelOk ? `${health?.device?.toUpperCase() ?? "CPU"}` : "NOT LOADED",
    },
    {
      label: "CAMERA",
      ok: cameraActive,
      detail: cameraActive ? "ACTIVE" : "INACTIVE",
    },
    {
      label: "SCAN",
      ok: isRunning,
      detail: isRunning ? "RUNNING" : "STOPPED",
    },
  ];

  return (
    <div className="status-bar">
      {indicators.map((ind) => (
        <div key={ind.label} className="status-item">
          <span
            className="status-dot"
            style={{ background: ind.ok ? "#2ECC71" : "#E84040" }}
          />
          <div className="status-text">
            <span className="status-label">{ind.label}</span>
            <span
              className="status-detail"
              style={{ color: ind.ok ? "rgba(232,228,220,0.7)" : "#E84040" }}
            >
              {ind.detail}
            </span>
          </div>
        </div>
      ))}

      {health?.uptime_seconds !== undefined && (
        <div className="status-uptime">
          <span className="status-label">UPTIME</span>
          <span className="status-detail" style={{ color: "rgba(232,228,220,0.7)" }}>
            {Math.floor(health.uptime_seconds / 60)}m {Math.round(health.uptime_seconds % 60)}s
          </span>
        </div>
      )}
    </div>
  );
}
