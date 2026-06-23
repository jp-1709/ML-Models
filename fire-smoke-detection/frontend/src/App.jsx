import { useState, useEffect, useRef, useCallback } from "react";
import DetectionCanvas from "./components/DetectionCanvas";
import AlertPanel from "./components/AlertPanel";
import StatsGrid from "./components/StatsGrid";
import StatusBar from "./components/StatusBar";
import ControlPanel from "./components/ControlPanel";
import useDetection from "./hooks/useDetection";
import useCamera from "./hooks/useCamera";
import "./App.css";

export default function App() {
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem("api_url") || "http://localhost:5050"
  );
  const [isRunning, setIsRunning] = useState(false);
  const [sensitivity, setSensitivity] = useState(0.45);
  const [showSettings, setShowSettings] = useState(false);

  const { videoRef, startCamera, stopCamera, cameraError, cameraActive } =
    useCamera();

  const { detectionResult, stats, health, sendFrame, resetStats } =
    useDetection({ apiUrl, sensitivity });

  // Detection loop
  const loopRef = useRef(null);

  const captureAndDetect = useCallback(() => {
    if (!videoRef.current || !isRunning) return;
    const video = videoRef.current;
    if (video.readyState < 2) return;

    const canvas = document.createElement("canvas");
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    sendFrame(dataUrl);
  }, [isRunning, videoRef, sendFrame]);

  useEffect(() => {
    if (isRunning) {
      loopRef.current = setInterval(captureAndDetect, 200); // 5 fps
    } else {
      clearInterval(loopRef.current);
    }
    return () => clearInterval(loopRef.current);
  }, [isRunning, captureAndDetect]);

  const handleStart = async () => {
    await startCamera();
    setIsRunning(true);
  };

  const handleStop = () => {
    setIsRunning(false);
    stopCamera();
  };

  const saveApiUrl = (url) => {
    localStorage.setItem("api_url", url);
    setApiUrl(url);
  };

  return (
    <div className="app-root">
      {/* ── Top Header ──────────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="header-brand">
          <div className="header-icon">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 3L28 26H4L16 3Z" fill="#E84040" />
              <path d="M16 10L22 22H10L16 10Z" fill="#FF7043" />
              <path d="M16 17L18 22H14L16 17Z" fill="#FFC107" />
            </svg>
          </div>
          <div>
            <h1 className="header-title">PYREGUARD</h1>
            <span className="header-sub">Industrial Fire &amp; Smoke Detection System</span>
          </div>
        </div>

        <div className="header-meta">
          <StatusBar health={health} isRunning={isRunning} cameraActive={cameraActive} />
          <button
            className="icon-btn"
            title="Settings"
            onClick={() => setShowSettings(!showSettings)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v3M12 20v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M1 12h3M20 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" />
            </svg>
          </button>
        </div>
      </header>

      {/* ── Settings Drawer ──────────────────────────────────────────────── */}
      {showSettings && (
        <div className="settings-drawer">
          <div className="settings-row">
            <label className="settings-label">BACKEND API ENDPOINT</label>
            <div className="settings-input-row">
              <input
                className="settings-input"
                defaultValue={apiUrl}
                onBlur={(e) => saveApiUrl(e.target.value)}
                placeholder="http://localhost:5050"
              />
              <span className="settings-hint">SSH: forward port 5050 → localhost:5050</span>
            </div>
          </div>
          <div className="settings-row">
            <label className="settings-label">
              DETECTION SENSITIVITY — {Math.round(sensitivity * 100)}%
            </label>
            <input
              type="range" min="20" max="80" value={sensitivity * 100}
              onChange={(e) => setSensitivity(e.target.value / 100)}
              className="settings-slider"
            />
          </div>
        </div>
      )}

      {/* ── Main Grid ───────────────────────────────────────────────────── */}
      <main className="app-main">
        {/* Left col: camera + canvas */}
        <section className="camera-section">
          <div className="panel camera-panel">
            <div className="panel-header">
              <span className="panel-title">LIVE FEED</span>
              <div className="panel-badges">
                {isRunning && <span className="badge badge-live">● LIVE</span>}
                {detectionResult?.fps && (
                  <span className="badge">{detectionResult.fps} fps</span>
                )}
                {detectionResult?.processing_ms && (
                  <span className="badge">{detectionResult.processing_ms} ms</span>
                )}
              </div>
            </div>

            <DetectionCanvas
              videoRef={videoRef}
              detectionResult={detectionResult}
              isRunning={isRunning}
            />

            {cameraError && (
              <div className="camera-error">
                <span>⚠ {cameraError}</span>
              </div>
            )}

            <ControlPanel
              isRunning={isRunning}
              onStart={handleStart}
              onStop={handleStop}
              onReset={resetStats}
            />
          </div>
        </section>

        {/* Right col: alerts + stats */}
        <aside className="sidebar">
          <AlertPanel detectionResult={detectionResult} />
          <StatsGrid stats={stats} />
        </aside>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="app-footer">
        <span>PYREGUARD v2.0  ·  YOLOv8 + HSV Ensemble  ·  CLAHE Enhanced</span>
        <span>Camera: Local Browser  ·  API: {apiUrl}</span>
      </footer>
    </div>
  );
}
