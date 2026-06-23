/**
 * AlertLog.jsx
 * ─────────────────────────────────────────────────────────────
 * Scrollable log of confirmed fall events.
 * Newest entries appear at the top with an entry animation.
 * ─────────────────────────────────────────────────────────────
 */

import React from 'react';

function methodBadge(method) {
  if (method === 'classical+pose') return { label: 'CLASSICAL + POSE', color: '#06b6d4' };
  return { label: 'CLASSICAL',        color: '#3b82f6' };
}

export default function AlertLog({ events = [], onClear }) {
  return (
    <div style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.title}>EVENT LOG</span>
          <span style={styles.count}>{events.length} events</span>
        </div>
        {events.length > 0 && (
          <button onClick={onClear} style={styles.clearBtn}>
            Clear
          </button>
        )}
      </div>

      {/* List */}
      <div style={styles.list}>
        {events.length === 0 ? (
          <div style={styles.empty}>
            <div style={styles.emptyIcon}>◯</div>
            <div style={styles.emptyText}>No fall events recorded.</div>
          </div>
        ) : (
          events.map((ev) => {
            const mb = methodBadge(ev.method);
            return (
              <div key={ev.event_id} style={styles.eventCard}>
                {/* Left accent strip */}
                <div style={{ ...styles.strip, background: '#ef4444' }} />

                <div style={styles.eventBody}>
                  {/* Row 1: ID, time, method badge */}
                  <div style={styles.row1}>
                    <span style={styles.evId}>#{ev.event_id}</span>
                    <span style={styles.evTime}>{ev.iso_time}</span>
                    <span style={{ ...styles.evBadge, color: mb.color, borderColor: `${mb.color}50` }}>
                      {mb.label}
                    </span>
                  </div>

                  {/* Row 2: metric chips */}
                  <div style={styles.chips}>
                    <Chip label="C_motion" value={`${ev.c_motion}%`}  color="#3b82f6" />
                    <Chip label="σ_θ"      value={`${ev.sigma_theta}°`} color="#f59e0b" />
                    <Chip label="σ_ρ"      value={ev.sigma_rho}       color="#8b5cf6" />
                    {ev.pose_score > 0 && (
                      <Chip label="pose" value={ev.pose_score} color="#06b6d4" />
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function Chip({ label, value, color }) {
  return (
    <span style={{ ...styles.chip, color, borderColor: `${color}40` }}>
      <span style={styles.chipLabel}>{label}</span>
      <span style={styles.chipValue}>{value}</span>
    </span>
  );
}

/* ── Styles ──────────────────────────────────────────────────── */
const styles = {
  panel: {
    background: '#111418',
    border: '1px solid #252d3a',
    borderRadius: 8,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    minHeight: 0,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 14px',
    borderBottom: '1px solid #1e2530',
    flexShrink: 0,
  },
  headerLeft: { display: 'flex', alignItems: 'baseline', gap: 10 },
  title: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.14em',
    color: '#94a3b8',
  },
  count: { fontSize: 11, color: '#334155' },
  clearBtn: {
    background: 'transparent',
    border: '1px solid #334155',
    color: '#64748b',
    borderRadius: 4,
    padding: '3px 10px',
    fontSize: 11,
    cursor: 'pointer',
    fontFamily: 'DM Sans, sans-serif',
    transition: 'all 200ms ease',
  },

  list: {
    overflowY: 'auto',
    flex: 1,
    padding: '8px 0',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '32px 16px',
    gap: 8,
  },
  emptyIcon: { fontSize: 24, color: '#334155' },
  emptyText: { fontSize: 12, color: '#334155', fontFamily: 'Space Mono, monospace' },

  eventCard: {
    display: 'flex',
    margin: '4px 10px',
    background: '#161b22',
    borderRadius: 6,
    overflow: 'hidden',
    border: '1px solid #1e2530',
    animation: 'fadeInUp 300ms ease',
  },
  strip: { width: 3, flexShrink: 0 },
  eventBody: { padding: '8px 10px', flex: 1, minWidth: 0 },

  row1: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
    flexWrap: 'wrap',
  },
  evId: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 11,
    fontWeight: 700,
    color: '#ef4444',
  },
  evTime: {
    fontSize: 11,
    color: '#64748b',
    fontFamily: 'Space Mono, monospace',
    flex: 1,
  },
  evBadge: {
    fontFamily: 'Space Mono, monospace',
    fontSize: 8,
    border: '1px solid',
    borderRadius: 2,
    padding: '2px 6px',
    letterSpacing: '0.08em',
  },

  chips: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  chip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    border: '1px solid',
    borderRadius: 3,
    padding: '2px 7px',
    fontSize: 10,
    fontFamily: 'Space Mono, monospace',
  },
  chipLabel: { opacity: 0.6, fontSize: 9 },
  chipValue: { fontWeight: 700 },
};
