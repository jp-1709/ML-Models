/**
 * MetricsPanel.jsx
 * ─────────────────────────────────────────────────────────────
 * Displays real-time detector metrics:
 *   • C_motion  (0–100%)
 *   • σ_θ       (orientation std-dev, 0–90°)
 *   • σ_ρ       (ratio std-dev, 0–2.0)
 *   • Pose score (0–1)
 * Each metric has a labelled bar + numeric readout.
 * ─────────────────────────────────────────────────────────────
 */

import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';

/* ── Gauge bar ───────────────────────────────────────────────── */
function MetricBar({ label, value, max, threshold, unit = '', decimals = 1 }) {
  const pct = Math.min((value / max) * 100, 100);
  const over = value >= threshold;

  const barColor = over
    ? (pct > 90 ? '#ef4444' : '#f97316')
    : '#3b82f6';

  return (
    <div style={styles.metricRow}>
      <div style={styles.metricHeader}>
        <span style={styles.metricLabel}>{label}</span>
        <span style={{ ...styles.metricValue, color: over ? '#f97316' : '#e2e8f0' }}>
          {value.toFixed(decimals)}{unit}
        </span>
      </div>

      {/* Track */}
      <div style={styles.track}>
        {/* Threshold tick */}
        <div style={{
          ...styles.tick,
          left: `${(threshold / max) * 100}%`,
        }} />
        {/* Fill bar */}
        <div style={{
          ...styles.fill,
          width: `${pct}%`,
          background: barColor,
          boxShadow: over ? `0 0 8px ${barColor}88` : 'none',
          transition: 'width 300ms ease, background 300ms ease',
        }} />
      </div>

      <div style={styles.thresholdLabel}>
        threshold: {threshold}{unit}
      </div>
    </div>
  );
}

/* ── Tiny spark-line chart ───────────────────────────────────── */
function Sparkline({ data, color }) {
  return (
    <ResponsiveContainer width="100%" height={52}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={color} stopOpacity={0.35} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <YAxis domain={[0, 100]} hide />
        <XAxis dataKey="t" hide />
        <Tooltip
          contentStyle={{ background: '#161b22', border: '1px solid #252d3a', borderRadius: 4, fontSize: 11 }}
          labelStyle={{ display: 'none' }}
          itemStyle={{ color }}
        />
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#grad-${color})`}
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ── Main component ──────────────────────────────────────────── */
export default function MetricsPanel({ metrics = {}, history = [] }) {
  const {
    c_motion    = 0,
    sigma_theta = 0,
    sigma_rho   = 0,
    pose_score  = 0,
  } = metrics;

  return (
    <div style={styles.panel}>
      <div style={styles.panelHeader}>
        <span style={styles.panelTitle}>DETECTOR METRICS</span>
        <span style={styles.panelSub}>live · 1 Hz polling</span>
      </div>

      <MetricBar
        label="C_motion"
        value={c_motion}
        max={100}
        threshold={65}
        unit="%"
        decimals={1}
      />
      <MetricBar
        label="σ_θ (orientation)"
        value={sigma_theta}
        max={90}
        threshold={15}
        unit="°"
        decimals={1}
      />
      <MetricBar
        label="σ_ρ (ratio)"
        value={sigma_rho}
        max={2}
        threshold={0.9}
        unit=""
        decimals={3}
      />
      <MetricBar
        label="Pose score"
        value={pose_score}
        max={1}
        threshold={0.6}
        unit=""
        decimals={2}
      />

      {/* Sparkline for C_motion history */}
      {history.length > 1 && (
        <div style={styles.sparkWrap}>
          <div style={styles.sparkLabel}>C_motion history</div>
          <Sparkline data={history} color="#3b82f6" />
        </div>
      )}
    </div>
  );
}

/* ── Styles ──────────────────────────────────────────────────── */
const styles = {
  panel: {
    background: '#111418',
    border: '1px solid #252d3a',
    borderRadius: 8,
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingBottom: 8,
    borderBottom: '1px solid #1e2530',
    marginBottom: 2,
  },
  panelTitle: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.14em',
    color: '#94a3b8',
  },
  panelSub: { fontSize: 10, color: '#334155' },

  metricRow: { display: 'flex', flexDirection: 'column', gap: 4 },
  metricHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' },
  metricLabel: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 10,
    color: '#64748b',
    letterSpacing: '0.06em',
  },
  metricValue: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 13,
    fontWeight: 700,
  },
  track: {
    height: 6,
    background: '#1e2530',
    borderRadius: 3,
    position: 'relative',
    overflow: 'visible',
  },
  fill: {
    height: '100%',
    borderRadius: 3,
    minWidth: 2,
  },
  tick: {
    position: 'absolute',
    top: -3,
    width: 1,
    height: 12,
    background: '#475569',
    zIndex: 2,
  },
  thresholdLabel: {
    fontSize: 9,
    color: '#334155',
    fontFamily: 'Space Mono, monospace',
    letterSpacing: '0.04em',
  },

  sparkWrap: {
    paddingTop: 8,
    borderTop: '1px solid #1e2530',
  },
  sparkLabel: {
    fontSize: 9,
    color: '#475569',
    fontFamily: 'Space Mono, monospace',
    letterSpacing: '0.06em',
    marginBottom: 4,
  },
};
