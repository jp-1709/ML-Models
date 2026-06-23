/**
 * VideoFeed.jsx
 * ─────────────────────────────────────────────────────────────
 * Renders the live MJPEG stream from the backend.
 * Shows a connecting / error overlay when the stream is not
 * yet available.
 * ─────────────────────────────────────────────────────────────
 */

import React, { useState, useRef, useEffect } from 'react';
import SimpleWebcamDetection from './SimpleWebcamDetection';

const STREAM_URL = '/video_feed';

export default function VideoFeed({ alertActive }) {
  const [status, setStatus] = useState('connecting'); // connecting | live | error
  const [useWebcam, setUseWebcam] = useState(false);
  const imgRef = useRef(null);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;

    const onLoad = () => setStatus('live');
    const onError = () => setStatus('error');

    img.addEventListener('load', onLoad);
    img.addEventListener('error', onError);
    return () => {
      img.removeEventListener('load', onLoad);
      img.removeEventListener('error', onError);
    };
  }, []);

  return (
    <div style={styles.wrapper}>
      {/* Mode toggle */}
      <div style={styles.modeToggle}>
        <button
          style={{
            ...styles.toggleBtn,
            background: !useWebcam ? '#22c55e' : 'transparent',
            color: !useWebcam ? '#fff' : '#64748b',
          }}
          onClick={() => setUseWebcam(false)}
        >
          📹 Camera Feed
        </button>
        <button
          style={{
            ...styles.toggleBtn,
            background: useWebcam ? '#22c55e' : 'transparent',
            color: useWebcam ? '#fff' : '#64748b',
          }}
          onClick={() => setUseWebcam(true)}
        >
          🌐 Browser Webcam
        </button>
      </div>

      {useWebcam ? (
        <SimpleWebcamDetection onDetection={(result) => {
          console.log('Detection result:', result);
          if (result.fall_detected) {
            console.log('🚨 FALL DETECTED!');
          }
        }} />
      ) : (
        <>
          {/* Corner decorations – surveillance aesthetic */}
          <Corner pos="tl" /><Corner pos="tr" />
          <Corner pos="bl" /><Corner pos="br" />

      {/* LIVE badge */}
      <div style={{
        ...styles.liveBadge,
        background: status === 'live' ? '#22c55e20' : '#f59e0b20',
        borderColor: status === 'live' ? '#22c55e' : '#f59e0b',
        color: status === 'live' ? '#22c55e' : '#f59e0b',
      }}>
        <span style={{
          ...styles.dot,
          background: status === 'live' ? '#22c55e' : '#f59e0b',
          animation: status === 'live' ? 'blink 1.6s ease infinite' : 'none',
        }} />
        {status === 'live' ? 'LIVE' : status === 'connecting' ? 'CONNECTING' : 'ERROR'}
      </div>

      {/* Camera label */}
      <div style={styles.camLabel}>CAM-01 · WIDE-ANGLE</div>

      {/* Stream image */}
      <img
        ref={imgRef}
        src={STREAM_URL}
        alt="Live camera feed"
        style={{
          ...styles.stream,
          filter: alertActive ? 'brightness(1.08)' : 'none',
          border: alertActive ? '2px solid #ef4444' : '2px solid transparent',
        }}
      />

      {/* Alert overlay banner */}
      {alertActive && (
        <div style={styles.alertBanner}>
          <span style={styles.alertIcon}>⚠</span>
          FALL DETECTED
          <span style={styles.alertIcon}>⚠</span>
        </div>
      )}

      {/* Connecting / Error overlay */}
      {status !== 'live' && (
        <div style={styles.overlay}>
          {status === 'connecting' ? (
            <>
              <div style={styles.spinner} />
              <p style={{ marginTop: 14, color: '#f59e0b', fontFamily: 'Space Mono, monospace', fontSize: 13 }}>
                Establishing video feed…
              </p>
            </>
          ) : (
            <>
              <div style={{ fontSize: 36 }}>📷</div>
              <p style={{ marginTop: 10, color: '#ef4444', fontFamily: 'Space Mono, monospace', fontSize: 13 }}>
                Camera unavailable.<br />Check backend connection.
              </p>
            </>
          )}
        </div>
      )}
        </>
      )}
    </div>
  );
}

/* ── Sub-component: corner bracket ─────────────────────────── */
function Corner({ pos }) {
  const map = {
    tl: { top: 0, left: 0, borderTop: '2px solid', borderLeft: '2px solid' },
    tr: { top: 0, right: 0, borderTop: '2px solid', borderRight: '2px solid' },
    bl: { bottom: 0, left: 0, borderBottom: '2px solid', borderLeft: '2px solid' },
    br: { bottom: 0, right: 0, borderBottom: '2px solid', borderRight: '2px solid' },
  };
  return (
    <div style={{
      position: 'absolute', width: 18, height: 18,
      borderColor: '#475569', zIndex: 3,
      ...map[pos],
    }} />
  );
}

/* ── Styles ──────────────────────────────────────────────────── */
const styles = {
  wrapper: {
    position: 'relative',
    width: '100%',
    background: '#000',
    borderRadius: 8,
    overflow: 'hidden',
    aspectRatio: '4 / 3',
    border: '1px solid #252d3a',
  },
  stream: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: 'block',
    transition: 'border 200ms ease',
  },
  liveBadge: {
    position: 'absolute', top: 10, left: 10, zIndex: 4,
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '3px 10px',
    border: '1px solid',
    borderRadius: 3,
    fontSize: 10,
    fontFamily: 'Space Mono, monospace',
    fontWeight: 700,
    letterSpacing: '0.1em',
    backdropFilter: 'blur(4px)',
  },
  dot: {
    width: 6, height: 6, borderRadius: '50%',
  },
  camLabel: {
    position: 'absolute', top: 10, right: 10, zIndex: 4,
    fontFamily: 'Space Mono, monospace',
    fontSize: 9,
    color: '#475569',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  },
  alertBanner: {
    position: 'absolute',
    bottom: 0, left: 0, right: 0,
    zIndex: 5,
    background: 'rgba(239,68,68,0.9)',
    color: '#fff',
    fontFamily: 'Space Mono, monospace',
    fontWeight: 700,
    fontSize: 14,
    letterSpacing: '0.2em',
    textAlign: 'center',
    padding: '8px 0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    animation: 'blink 0.9s ease infinite',
  },
  alertIcon: { fontSize: 16 },
  overlay: {
    position: 'absolute', inset: 0, zIndex: 6,
    background: 'rgba(10,12,15,0.85)',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    textAlign: 'center',
  },
  spinner: {
    width: 32, height: 32,
    border: '3px solid #252d3a',
    borderTopColor: '#f59e0b',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  modeToggle: {
    position: 'absolute',
    top: 10,
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 5,
    display: 'flex',
    background: '#111418',
    border: '1px solid #252d3a',
    borderRadius: 4,
    overflow: 'hidden',
  },
  toggleBtn: {
    padding: '4px 12px',
    border: 'none',
    fontSize: 10,
    fontFamily: 'Space Mono, monospace',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 200ms ease',
    letterSpacing: '0.05em',
  },
};
