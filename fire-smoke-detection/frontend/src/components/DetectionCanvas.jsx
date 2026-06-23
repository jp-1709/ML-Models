import { useEffect, useRef } from "react";
import "./DetectionCanvas.css";

const RISK_COLORS = {
  CRITICAL: "#D42B2B",
  HIGH:     "#E84040",
  MEDIUM:   "#F5A623",
  LOW:      "#3D9970",
  CLEAR:    "#2E9E6A",
};

const CLASS_COLORS = {
  fire:  "#E84040",
  smoke: "#7E8B98",
};

export default function DetectionCanvas({ videoRef, detectionResult, isRunning }) {
  const overlayRef = useRef(null);

  // Draw detections on overlay canvas
  useEffect(() => {
    const canvas = overlayRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!detectionResult?.detections?.length) return;

    const { detections } = detectionResult;

    detections.forEach((det) => {
      const [x1, y1, x2, y2] = det.bbox;
      const w = x2 - x1;
      const h = y2 - y1;
      const color = CLASS_COLORS[det.class] || "#FFF";
      const label = `${det.class.toUpperCase()}  ${Math.round(det.confidence * 100)}%`;

      // ── Glow effect ────────────────────────────────────────────────────
      ctx.shadowColor = color;
      ctx.shadowBlur  = 12;

      // ── Corner-bracket bounding box (industrial style) ─────────────────
      const bracketLen = Math.min(w, h) * 0.25;
      ctx.strokeStyle = color;
      ctx.lineWidth   = 2.5;
      ctx.shadowBlur  = 8;

      const corners = [
        // top-left
        [[x1, y1 + bracketLen], [x1, y1], [x1 + bracketLen, y1]],
        // top-right
        [[x2 - bracketLen, y1], [x2, y1], [x2, y1 + bracketLen]],
        // bottom-right
        [[x2, y2 - bracketLen], [x2, y2], [x2 - bracketLen, y2]],
        // bottom-left
        [[x1 + bracketLen, y2], [x1, y2], [x1, y2 - bracketLen]],
      ];

      corners.forEach(([p1, corner, p2]) => {
        ctx.beginPath();
        ctx.moveTo(...p1);
        ctx.lineTo(...corner);
        ctx.lineTo(...p2);
        ctx.stroke();
      });

      // ── Centre crosshair ────────────────────────────────────────────────
      const cx = x1 + w / 2;
      const cy = y1 + h / 2;
      ctx.shadowBlur = 4;
      ctx.beginPath();
      ctx.moveTo(cx - 6, cy); ctx.lineTo(cx + 6, cy);
      ctx.moveTo(cx, cy - 6); ctx.lineTo(cx, cy + 6);
      ctx.stroke();

      // ── Label tag ──────────────────────────────────────────────────────
      ctx.shadowBlur = 0;
      ctx.font       = "bold 12px IBM Plex Mono, monospace";
      const tw = ctx.measureText(label).width + 12;
      const th = 20;
      const lx = x1;
      const ly = Math.max(0, y1 - th - 2);

      ctx.fillStyle = color;
      ctx.fillRect(lx, ly, tw, th);
      ctx.fillStyle = "#FFFFFF";
      ctx.fillText(label, lx + 6, ly + 14);

      // ── Source badge ───────────────────────────────────────────────────
      if (det.ensemble) {
        const badge = "ENS";
        ctx.font = "10px IBM Plex Mono, monospace";
        const bw = ctx.measureText(badge).width + 8;
        ctx.fillStyle = "rgba(0,0,0,0.6)";
        ctx.fillRect(x2 - bw - 2, y2 - 18, bw, 16);
        ctx.fillStyle = "#FFF";
        ctx.fillText(badge, x2 - bw + 2, y2 - 5);
      }
    });
  }, [detectionResult]);

  // Sync canvas size to video
  useEffect(() => {
    const video = videoRef.current;
    const canvas = overlayRef.current;
    if (!video || !canvas) return;

    const resize = () => {
      const rect = video.getBoundingClientRect();
      canvas.width  = rect.width;
      canvas.height = rect.height;
      canvas.style.width  = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
    };

    const ro = new ResizeObserver(resize);
    ro.observe(video);
    return () => ro.disconnect();
  }, [videoRef]);

  const risk = detectionResult?.risk_level || "CLEAR";
  const riskColor = RISK_COLORS[risk] || "#2E9E6A";
  const annotatedFrame = detectionResult?.annotated_frame;

  return (
    <div className="detection-canvas-wrap">
      {/* ── Video element (captures local camera) ──── */}
      <video
        ref={videoRef}
        className="camera-video"
        autoPlay
        playsInline
        muted
        style={{ display: isRunning ? "block" : "none" }}
      />

      {/* ── Annotated frame from backend (optional overlay mode) ───── */}
      {annotatedFrame && isRunning && (
        <img
          className="annotated-frame"
          src={annotatedFrame}
          alt="detection"
        />
      )}

      {/* ── SVG overlay for JS-drawn boxes ───── */}
      <canvas ref={overlayRef} className="overlay-canvas" />

      {/* ── Idle / placeholder ─────────────────── */}
      {!isRunning && (
        <div className="camera-idle">
          <div className="idle-icon">
            <svg viewBox="0 0 64 64" fill="none">
              <rect x="4" y="12" width="56" height="40" rx="4" stroke="#B8B4AE" strokeWidth="2" />
              <circle cx="32" cy="32" r="10" stroke="#B8B4AE" strokeWidth="2" />
              <circle cx="32" cy="32" r="4"  fill="#B8B4AE" />
              <circle cx="50" cy="18" r="3"  fill="#B8B4AE" />
            </svg>
          </div>
          <span className="idle-text">CAMERA INACTIVE</span>
          <span className="idle-sub">Press START to begin detection</span>
        </div>
      )}

      {/* ── Risk level banner overlay ──────────── */}
      {isRunning && risk !== "CLEAR" && (
        <div
          className="risk-overlay-badge"
          style={{ borderColor: riskColor, color: riskColor }}
        >
          <span className="risk-dot" style={{ background: riskColor }} />
          {risk}
        </div>
      )}

      {/* ── Corner decorations (industrial feel) ── */}
      <div className="corner corner-tl" />
      <div className="corner corner-tr" />
      <div className="corner corner-bl" />
      <div className="corner corner-br" />
    </div>
  );
}
