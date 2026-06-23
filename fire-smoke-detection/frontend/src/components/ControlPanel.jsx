import "./ControlPanel.css";

export default function ControlPanel({ isRunning, onStart, onStop, onReset }) {
  return (
    <div className="control-panel">
      {!isRunning ? (
        <button className="ctrl-btn ctrl-start" onClick={onStart}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5,3 19,12 5,21" />
          </svg>
          START DETECTION
        </button>
      ) : (
        <button className="ctrl-btn ctrl-stop" onClick={onStop}>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" rx="1" />
            <rect x="14" y="4" width="4" height="16" rx="1" />
          </svg>
          STOP
        </button>
      )}

      <button className="ctrl-btn ctrl-reset" onClick={onReset} title="Reset session statistics">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="1 4 1 10 7 10" />
          <path d="M3.51 15a9 9 0 1 0 .49-3.5" />
        </svg>
        RESET STATS
      </button>
    </div>
  );
}
