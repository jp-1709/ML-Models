/**
 * App.jsx
 * ─────────────────────────────────────────────────────────────
 * Root dashboard component.
 *
 * Data flow:
 *   • HTTP polling  (/api/status)    → metrics + state, every 800ms
 *   • HTTP polling  (/api/events)    → event log, every 2s
 *   • WebSocket     (/ws/alerts)     → instant fall alert push
 *
 * Layout (CSS Grid):
 *   ┌─────────────────────────────────────────────────────┐
 *   │  HEADER: logo · connection badge · reset btn        │
 *   ├───────────────────────┬─────────────────────────────┤
 *   │  VIDEO FEED  (2 cols) │  STATUS PANEL               │
 *   │                       ├─────────────────────────────┤
 *   │                       │  METRICS PANEL              │
 *   ├───────────────────────┴─────────────────────────────┤
 *   │  ALERT LOG  (full width)                            │
 *   └─────────────────────────────────────────────────────┘
 * ─────────────────────────────────────────────────────────────
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import VideoFeed from './components/VideoFeed';
import StatusPanel from './components/StatusPanel';
import MetricsPanel from './components/MetricsPanel';
import AlertLog from './components/AlertLog';
import WebcamSender from './components/WebcamSender';

const API_BASE = '';
const WS_URL = `ws://localhost:8000/ws/alerts`;
const MAX_HISTORY = 60;   // keep last 60 C_motion samples for sparkline

/* ── useWebSocket hook ────────────────────────────────────────── */
function useWebSocket(url, onMessage) {
  const wsRef = useRef(null);
  const reconnTimer = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return;
    const ws = new WebSocket(url);
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); } catch (_) { }
    };
    ws.onclose = () => {
      reconnTimer.current = setTimeout(connect, 3000);
    };
    wsRef.current = ws;
  }, [url, onMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef;
}

/* ── Main App ─────────────────────────────────────────────────── */
export default function App() {
  const [status, setStatus] = useState({});
  const [events, setEvents] = useState([]);
  const [history, setHistory] = useState([]);   // [{t, v}] for sparkline
  const [wsAlive, setWsAlive] = useState(false);
  const [apiAlive, setApiAlive] = useState(false);
  const [flashAlert, setFlashAlert] = useState(false);

  // ── WebSocket ────────────────────────────────────────────────
  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'heartbeat') {
      setWsAlive(true);
    } else if (msg.type === 'fall_alert') {
      setFlashAlert(true);
      setTimeout(() => setFlashAlert(false), 6000);
      // Prepend new event immediately without waiting for poll
      setEvents((prev) => [msg, ...prev].slice(0, 100));
    }
  }, []);

  useWebSocket(WS_URL, handleWsMessage);

  // ── HTTP polling: status ─────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch(`${API_BASE}/api/status`, { signal: AbortSignal.timeout(2000) });
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!cancelled) {
          setStatus(data);
          setApiAlive(true);
          setHistory((prev) => {
            const next = [...prev, { t: Date.now(), v: data.c_motion ?? 0 }];
            return next.slice(-MAX_HISTORY);
          });
        }
      } catch {
        if (!cancelled) setApiAlive(false);
      }
    }
    poll();
    const id = setInterval(poll, 800);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // ── HTTP polling: events ─────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch(`${API_BASE}/api/events?limit=50`, { signal: AbortSignal.timeout(2000) });
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!cancelled) setEvents(data.events ?? []);
      } catch { }
    }
    poll();
    const id = setInterval(poll, 2000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // ── Reset ────────────────────────────────────────────────────
  async function handleReset() {
    try {
      await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
      setEvents([]);
      setHistory([]);
      setStatus({});
    } catch (e) {
      alert('Reset failed – is the backend running?');
    }
  }

  const state = status.state ?? 'IDLE';
  const alertActive = status.alert_active || flashAlert;
  const metrics = status;

  return (
    <div style={styles.root}>
      <WebcamSender />
      {/* ── Scanline overlay (aesthetic) ─────────────────────── */}
      <div style={styles.scanline} />

      {/* ── Header ───────────────────────────────────────────── */}
      <header style={styles.header}>
        <div style={styles.brand}>
          <div style={styles.brandIcon}>⬡</div>
          <div>
            <div style={styles.brandName}>SENTINEL</div>
            <div style={styles.brandSub}>Fall Detection System v1.0</div>
          </div>
        </div>

        <div style={styles.headerRight}>
          {/* Connection indicators */}
          <ConnBadge label="API" alive={apiAlive} />
          <ConnBadge label="WebSocket" alive={wsAlive} />

          <button onClick={handleReset} style={styles.resetBtn}>
            ↺ Reset
          </button>
        </div>
      </header>

      {/* ── Main grid ────────────────────────────────────────── */}
      <main style={styles.grid}>

        {/* Column 1: Video */}
        <div style={styles.videoCol}>
          <SectionLabel>LIVE FEED</SectionLabel>
          <VideoFeed alertActive={alertActive} />

          {/* Algorithm info card */}
          <div style={styles.infoCard}>
            <div style={styles.infoTitle}>Algorithm Pipeline</div>
            <div style={styles.pipeline}>
              {['Background Sub.', 'MHI (C_motion)', 'Ellipse Fit', 'Shape Analysis', 'Pose Est.', 'Immobility Check', 'Alert'].map((s, i) => (
                <React.Fragment key={s}>
                  <span style={styles.pipeStep}>{s}</span>
                  {i < 6 && <span style={styles.pipeArrow}>›</span>}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>

        {/* Column 2: Status + Metrics */}
        <div style={styles.sideCol}>
          <SectionLabel>STATUS</SectionLabel>
          <StatusPanel
            state={state}
            alertCount={events.length}
          />

          <div style={{ height: 16 }} />

          <SectionLabel>METRICS</SectionLabel>
          <MetricsPanel metrics={metrics} history={history} />
        </div>

        {/* Full-width row: Event log */}
        <div style={styles.logRow}>
          <SectionLabel>ALERT LOG</SectionLabel>
          <AlertLog events={events} onClear={() => setEvents([])} />
        </div>

      </main>
    </div>
  );
}

/* ── Helper components ────────────────────────────────────────── */
function SectionLabel({ children }) {
  return (
    <div style={{
      fontFamily: 'Space Mono, monospace',
      fontSize: 9,
      letterSpacing: '0.18em',
      color: '#334155',
      marginBottom: 6,
      textTransform: 'uppercase',
    }}>
      {children}
    </div>
  );
}

function ConnBadge({ label, alive }) {
  return (
    <div style={styles.connBadge}>
      <div style={{
        width: 6, height: 6, borderRadius: '50%',
        background: alive ? '#22c55e' : '#ef4444',
        animation: alive ? 'blink 2s ease infinite' : 'none',
      }} />
      <span style={{ fontSize: 10, color: alive ? '#94a3b8' : '#ef4444' }}>{label}</span>
    </div>
  );
}

/* ── Styles ──────────────────────────────────────────────────── */
const styles = {
  root: {
    minHeight: '100vh',
    background: '#0a0c0f',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    overflow: 'hidden',
  },
  scanline: {
    position: 'fixed',
    top: 0, left: 0, right: 0,
    height: '2px',
    background: 'linear-gradient(transparent, rgba(255,255,255,0.03), transparent)',
    zIndex: 1000,
    pointerEvents: 'none',
    animation: 'scanline 8s linear infinite',
  },

  // Header
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    borderBottom: '1px solid #1e2530',
    background: '#0d1117',
    flexShrink: 0,
    zIndex: 10,
  },
  brand: { display: 'flex', alignItems: 'center', gap: 12 },
  brandIcon: {
    fontSize: 22,
    color: '#3b82f6',
    lineHeight: 1,
  },
  brandName: {
    fontFamily: 'Space Mono, monospace',
    fontWeight: 700,
    fontSize: 16,
    letterSpacing: '0.2em',
    color: '#e2e8f0',
  },
  brandSub: { fontSize: 10, color: '#334155', marginTop: 1 },

  headerRight: { display: 'flex', alignItems: 'center', gap: 14 },
  connBadge: {
    display: 'flex', alignItems: 'center', gap: 5,
    background: '#111418',
    border: '1px solid #1e2530',
    borderRadius: 4,
    padding: '4px 10px',
  },
  resetBtn: {
    background: 'transparent',
    border: '1px solid #334155',
    color: '#94a3b8',
    borderRadius: 4,
    padding: '5px 14px',
    fontSize: 12,
    cursor: 'pointer',
    fontFamily: 'Space Mono, monospace',
    letterSpacing: '0.06em',
    transition: 'all 200ms ease',
  },

  // Grid
  grid: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: '1fr 340px',
    gridTemplateRows: 'auto auto',
    gap: 0,
    padding: 20,
    columnGap: 20,
    rowGap: 20,
    alignItems: 'start',
    maxWidth: 1400,
    width: '100%',
    margin: '0 auto',
  },

  videoCol: {
    gridColumn: '1',
    gridRow: '1',
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
  },
  sideCol: {
    gridColumn: '2',
    gridRow: '1',
    display: 'flex',
    flexDirection: 'column',
  },
  logRow: {
    gridColumn: '1 / -1',
    gridRow: '2',
    maxHeight: 320,
    display: 'flex',
    flexDirection: 'column',
  },

  // Info card
  infoCard: {
    marginTop: 12,
    background: '#111418',
    border: '1px solid #1e2530',
    borderRadius: 8,
    padding: '10px 14px',
  },
  infoTitle: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 9,
    letterSpacing: '0.12em',
    color: '#334155',
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  pipeline: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 4,
  },
  pipeStep: {
    background: '#161b22',
    border: '1px solid #252d3a',
    borderRadius: 3,
    padding: '3px 8px',
    fontSize: 10,
    color: '#64748b',
    fontFamily: 'Space Mono, monospace',
    whiteSpace: 'nowrap',
  },
  pipeArrow: { color: '#334155', fontSize: 14 },
};
