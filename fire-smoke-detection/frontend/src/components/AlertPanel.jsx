import { useState, useEffect } from "react";
import "./AlertPanel.css";

const RISK_META = {
  CRITICAL: { label: "CRITICAL",  color: "#D42B2B", bg: "rgba(212,43,43,0.08)",   icon: "🔥", desc: "Immediate action required" },
  HIGH:     { label: "HIGH",      color: "#E84040", bg: "rgba(232,64,64,0.07)",   icon: "⚠",  desc: "Fire detected — evacuate" },
  MEDIUM:   { label: "MEDIUM",    color: "#F5A623", bg: "rgba(245,166,35,0.07)",  icon: "〰",  desc: "Smoke / early-stage fire" },
  LOW:      { label: "LOW",       color: "#3D9970", bg: "rgba(61,153,112,0.07)",  icon: "◐",  desc: "Trace smoke detected" },
  CLEAR:    { label: "CLEAR",     color: "#2E9E6A", bg: "rgba(46,158,106,0.05)",  icon: "✓",  desc: "No threats detected" },
};

const MAX_HISTORY = 8;

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString("en-GB", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export default function AlertPanel({ detectionResult }) {
  const [history, setHistory] = useState([]);
  const [alertActive, setAlertActive] = useState(false);

  const risk = detectionResult?.risk_level || "CLEAR";
  const meta = RISK_META[risk] || RISK_META.CLEAR;

  useEffect(() => {
    if (!detectionResult) return;
    const { risk_level, alert, detections } = detectionResult;
    if (!detections?.length) return;

    setAlertActive(alert);

    const entry = {
      id:        Date.now(),
      timestamp: Date.now(),
      risk:      risk_level,
      detections: detections.map((d) => `${d.class} ${Math.round(d.confidence * 100)}%`).join(", "),
      alert,
    };

    setHistory((prev) => [entry, ...prev].slice(0, MAX_HISTORY));
  }, [detectionResult]);

  return (
    <div className="panel alert-panel">
      {/* Header */}
      <div className="panel-header">
        <span className="panel-title">THREAT STATUS</span>
        {alertActive && <span className="badge badge-live">● ALERT</span>}
      </div>

      {/* Current risk indicator */}
      <div
        className="risk-indicator"
        style={{ background: meta.bg, borderColor: meta.color + "40" }}
      >
        <div className="risk-main">
          <span className="risk-icon">{meta.icon}</span>
          <div className="risk-content">
            <span className="risk-label" style={{ color: meta.color }}>
              {meta.label}
            </span>
            <span className="risk-desc">{meta.desc}</span>
          </div>
        </div>

        {/* Gauge bar */}
        <div className="risk-bar-wrap">
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((level) => {
            const active = ["CLEAR", "LOW", "MEDIUM", "HIGH", "CRITICAL"].indexOf(risk)
              >= ["CLEAR", "LOW", "MEDIUM", "HIGH", "CRITICAL"].indexOf(level);
            return (
              <div
                key={level}
                className={`risk-bar-seg ${active ? "active" : ""}`}
                style={active ? { background: RISK_META[level].color } : {}}
              />
            );
          })}
        </div>

        {/* Detected classes */}
        {detectionResult?.detections?.length > 0 && (
          <div className="detection-chips">
            {detectionResult.detections.map((d, i) => (
              <span
                key={i}
                className="det-chip"
                style={{
                  background: d.class === "fire" ? "rgba(232,64,64,0.12)" : "rgba(126,139,152,0.12)",
                  color:      d.class === "fire" ? "#E84040" : "#5C7080",
                  borderColor: d.class === "fire" ? "rgba(232,64,64,0.25)" : "rgba(126,139,152,0.2)",
                }}
              >
                {d.class === "fire" ? "🔥" : "💨"} {d.class} {Math.round(d.confidence * 100)}%
                {d.ensemble && <span className="chip-ens">ENS</span>}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Event history log */}
      <div className="alert-history">
        <div className="history-header">
          <span className="history-title">EVENT LOG</span>
          {history.length > 0 && (
            <button
              className="history-clear-btn"
              onClick={() => setHistory([])}
            >
              CLEAR
            </button>
          )}
        </div>

        <div className="history-list">
          {history.length === 0 ? (
            <div className="history-empty">No events recorded</div>
          ) : (
            history.map((evt) => {
              const m = RISK_META[evt.risk] || RISK_META.CLEAR;
              return (
                <div key={evt.id} className="history-item">
                  <span className="history-dot" style={{ background: m.color }} />
                  <div className="history-body">
                    <span className="history-risk" style={{ color: m.color }}>
                      {evt.risk}
                    </span>
                    <span className="history-dets">{evt.detections}</span>
                  </div>
                  <span className="history-time">{formatTime(evt.timestamp)}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
