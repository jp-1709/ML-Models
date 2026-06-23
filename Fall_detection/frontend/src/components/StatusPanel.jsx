/**
 * StatusPanel.jsx
 * ─────────────────────────────────────────────────────────────
 * Displays the current detector state with a large coloured
 * indicator and animated transitions.
 * ─────────────────────────────────────────────────────────────
 */

import React from 'react';

const STATE_CONFIG = {
  IDLE: {
    label: 'Normal Activity',
    sublabel: 'No anomaly detected',
    color: '#22c55e',
    bg: '#052e16',
    icon: '✓',
  },
  MOTION_DETECTED: {
    label: 'Motion Detected',
    sublabel: 'Monitoring movement…',
    color: '#f59e0b',
    bg: '#1c1003',
    icon: '◉',
  },
  SHAPE_TRIGGERED: {
    label: 'Shape Analysis',
    sublabel: 'Verifying fall posture…',
    color: '#f97316',
    bg: '#1c0a03',
    icon: '◌',
  },
  FALL_CONFIRMED: {
    label: 'FALL DETECTED',
    sublabel: 'Alert has been triggered',
    color: '#ef4444',
    bg: '#1c0505',
    icon: '⚠',
  },
};

export default function StatusPanel({ state = 'IDLE', alertCount = 0 }) {
  const cfg = STATE_CONFIG[state] || STATE_CONFIG.IDLE;
  const isPanic = state === 'FALL_CONFIRMED';

  return (
    <div style={{
      ...styles.card,
      background: cfg.bg,
      border: `1px solid ${cfg.color}40`,
      animation: isPanic ? 'alertPulse 1s ease infinite' : 'none',
    }}>
      {/* Icon */}
      <div style={{ ...styles.icon, color: cfg.color,
        animation: isPanic ? 'blink 0.8s ease infinite' : 'none' }}>
        {cfg.icon}
      </div>

      {/* Text */}
      <div style={styles.textBlock}>
        <div style={{ ...styles.label, color: cfg.color }}>
          {cfg.label}
        </div>
        <div style={styles.sublabel}>{cfg.sublabel}</div>
      </div>

      {/* State badge */}
      <div style={{ ...styles.badge, color: cfg.color, borderColor: `${cfg.color}60` }}>
        {state.replace('_', ' ')}
      </div>

      {/* Alert counter */}
      <div style={styles.counter}>
        <span style={styles.counterNum}>{alertCount}</span>
        <span style={styles.counterLabel}>alerts<br/>today</span>
      </div>
    </div>
  );
}

const styles = {
  card: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: '14px 18px',
    borderRadius: 8,
    transition: 'background 300ms ease, border 300ms ease',
    position: 'relative',
    overflow: 'hidden',
  },
  icon: {
    fontSize: 28,
    fontWeight: 700,
    width: 36,
    textAlign: 'center',
    flexShrink: 0,
  },
  textBlock: { flex: 1, minWidth: 0 },
  label: {
    fontFamily: 'Space Mono, monospace',
    fontWeight: 700,
    fontSize: 15,
    letterSpacing: '0.04em',
    whiteSpace: 'nowrap',
  },
  sublabel: {
    color: '#64748b',
    fontSize: 12,
    marginTop: 2,
  },
  badge: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 9,
    letterSpacing: '0.1em',
    border: '1px solid',
    borderRadius: 3,
    padding: '3px 7px',
    textTransform: 'uppercase',
    whiteSpace: 'nowrap',
  },
  counter: {
    textAlign: 'center',
    paddingLeft: 14,
    borderLeft: '1px solid #252d3a',
  },
  counterNum: {
    display: 'block',
    fontFamily: 'Space Mono, monospace',
    fontSize: 22,
    fontWeight: 700,
    color: '#e2e8f0',
    lineHeight: 1,
  },
  counterLabel: {
    display: 'block',
    fontSize: 9,
    color: '#475569',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginTop: 2,
  },
};
