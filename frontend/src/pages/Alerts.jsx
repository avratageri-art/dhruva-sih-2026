import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  AlertTriangle, Bell, CheckCircle, X, Clock, User, Shield,
  Filter, Search, Plus, ChevronDown, Info, Eye, MessageSquare,
  Key, Wallet, Server, Network, Globe
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Synthetic alerts seeded from assessment data
const STATIC_ALERTS = [
  {
    id: 'ALT-001',
    trigger: 'Attribution Confidence Threshold',
    rule: 'Score >= 80',
    actor: 'ShadowFox',
    actor_id: 1,
    timestamp: '2024-03-15T09:14:22Z',
    source: 'Attribution Engine',
    confidence: 84,
    status: 'NEW',
    priority: 'HIGH',
    evidence: 'ShadowFox ↔ ZeroByte: shared PGP fingerprint + stylometric match 86%',
    category: 'attribution',
  },
  {
    id: 'ALT-002',
    trigger: 'New PGP Identifier Observed',
    rule: 'Tracked actor gains new PGP key',
    actor: 'ShadowFox',
    actor_id: 1,
    timestamp: '2024-02-20T14:33:01Z',
    source: 'BFD Forum Monitor',
    confidence: 92,
    status: 'REVIEWED',
    priority: 'MEDIUM',
    evidence: 'PGP fingerprint 3A9F2B1C... observed on BFD Forum (same as ShadowFox key)',
    category: 'identifier',
  },
  {
    id: 'ALT-003',
    trigger: 'Persona Migration Detected',
    rule: 'Handle inactivity > 60 days + new persona emergence',
    actor: 'ZeroByte',
    actor_id: 2,
    timestamp: '2024-01-10T07:02:44Z',
    source: 'Behavioural Monitor',
    confidence: 78,
    status: 'NEW',
    priority: 'HIGH',
    evidence: '@shadow_fox99 inactive 65 days → ZeroByte active on Breached with matching behavioural profile',
    category: 'migration',
  },
  {
    id: 'ALT-004',
    trigger: 'Wallet Address Observed',
    rule: 'New wallet linked to tracked actor',
    actor: 'GhostNet',
    actor_id: 3,
    timestamp: '2024-01-05T19:48:10Z',
    source: 'CryptoTrace',
    confidence: 88,
    status: 'CONFIRMED_BY_ANALYST',
    priority: 'MEDIUM',
    evidence: 'BTC wallet address 1Ghost... observed in forum signature. Previously unlinked.',
    category: 'wallet',
  },
  {
    id: 'ALT-005',
    trigger: 'High-Volume Posting Activity',
    rule: 'Actor posts > 10 in 24h',
    actor: 'NullAdmin',
    actor_id: 6,
    timestamp: '2023-12-28T11:25:30Z',
    source: 'Breached Dark Forum Monitor',
    confidence: 71,
    status: 'DISMISSED',
    priority: 'LOW',
    evidence: '14 posts in 22 hours on Breached. Topic: credential sales.',
    category: 'activity',
  },
  {
    id: 'ALT-006',
    trigger: 'New Onion Service Detected',
    rule: 'Service linked to known infrastructure fingerprint',
    actor: 'ShadowFox',
    actor_id: 1,
    timestamp: '2023-12-01T03:10:00Z',
    source: 'Infrastructure Monitor',
    confidence: 67,
    status: 'REVIEWED',
    priority: 'MEDIUM',
    evidence: 'TLS fingerprint JA3:a1b2c3... matches previously observed ShadowFox infrastructure.',
    category: 'infrastructure',
  },
];

const STATUS_CONFIG = {
  NEW: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', label: 'New' },
  REVIEWED: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: 'Reviewed' },
  CONFIRMED_BY_ANALYST: { color: '#22c55e', bg: 'rgba(34,197,94,0.12)', label: 'Confirmed' },
  DISMISSED: { color: '#475569', bg: 'rgba(71,85,105,0.12)', label: 'Dismissed' },
};

const PRIORITY_CONFIG = {
  HIGH: { color: '#ef4444' },
  MEDIUM: { color: '#f59e0b' },
  LOW: { color: '#94a3b8' },
};

const CATEGORY_ICONS = {
  attribution: Shield,
  identifier: Key,
  wallet: Wallet,
  migration: User,
  infrastructure: Server,
  activity: Globe,
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.NEW;
  return (
    <span style={{
      padding: '3px 10px', borderRadius: '4px', fontSize: '0.7rem',
      fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
      background: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.color}40`,
    }}>{cfg.label}</span>
  );
}

export default function Alerts() {
  const [alerts, setAlerts] = useState(STATIC_ALERTS);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');
  const [searchQ, setSearchQ] = useState('');
  const [analystNote, setAnalystNote] = useState('');
  const [stats, setStats] = useState({ total: 0, new: 0, high: 0, confirmed: 0 });

  // Try to fetch real alerts from backend
  useEffect(() => {
    axios.get(`${API_BASE}/api/alerts`)
      .then(r => { if (r.data?.length) setAlerts(r.data); })
      .catch(() => {/* use static */});

    const s = STATIC_ALERTS.reduce((acc, a) => {
      acc.total++;
      if (a.status === 'NEW') acc.new++;
      if (a.priority === 'HIGH') acc.high++;
      if (a.status === 'CONFIRMED_BY_ANALYST') acc.confirmed++;
      return acc;
    }, { total: 0, new: 0, high: 0, confirmed: 0 });
    setStats(s);
  }, []);

  const filtered = alerts.filter(a => {
    if (filterStatus !== 'ALL' && a.status !== filterStatus) return false;
    if (filterPriority !== 'ALL' && a.priority !== filterPriority) return false;
    if (searchQ && !a.actor?.toLowerCase().includes(searchQ.toLowerCase()) &&
        !a.trigger?.toLowerCase().includes(searchQ.toLowerCase()) &&
        !a.evidence?.toLowerCase().includes(searchQ.toLowerCase())) return false;
    return true;
  });

  function updateStatus(id, newStatus) {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: newStatus } : a));
    if (selectedAlert?.id === id) setSelectedAlert(prev => ({ ...prev, status: newStatus }));
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0 }}>Alerts &amp; Watchlist</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '0.9rem' }}>
            Automated intelligence threshold monitoring and analyst review queue.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm">
            <Filter size={14} /> Filter
          </button>
          <button className="btn btn-primary btn-sm">
            <Plus size={14} /> New Rule
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4" style={{ marginBottom: '20px', gap: '12px' }}>
        {[
          { label: 'Total Alerts', value: stats.total, color: 'var(--text-primary)' },
          { label: 'Awaiting Review', value: stats.new, color: '#ef4444' },
          { label: 'High Priority', value: stats.high, color: '#f59e0b' },
          { label: 'Analyst Confirmed', value: stats.confirmed, color: '#22c55e' },
        ].map((s, i) => (
          <div key={i} className="card" style={{ padding: '16px' }}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value" style={{ fontSize: '1.8rem', color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedAlert ? '1fr 380px' : '1fr', gap: '20px', alignItems: 'start' }}>
        {/* Alert List */}
        <div className="card">
          <div className="card-header" style={{ justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Bell size={16} color="#ef4444" />
              <span style={{ fontWeight: 600 }}>Alert Queue</span>
              <span className="badge badge-neutral">{filtered.length}</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <div style={{ position: 'relative' }}>
                <Search size={13} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  value={searchQ} onChange={e => setSearchQ(e.target.value)}
                  placeholder="Search alerts..." className="form-input"
                  style={{ paddingLeft: '30px', width: '200px', fontSize: '0.8rem' }}
                />
              </div>
              <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="form-select" style={{ fontSize: '0.8rem' }}>
                <option value="ALL">All Status</option>
                <option value="NEW">New</option>
                <option value="REVIEWED">Reviewed</option>
                <option value="CONFIRMED_BY_ANALYST">Confirmed</option>
                <option value="DISMISSED">Dismissed</option>
              </select>
              <select value={filterPriority} onChange={e => setFilterPriority(e.target.value)} className="form-select" style={{ fontSize: '0.8rem' }}>
                <option value="ALL">All Priority</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>

          {/* Alert rows */}
          {filtered.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No alerts match the current filters.
            </div>
          ) : (
            <div>
              {filtered.map(alert => {
                const CatIcon = CATEGORY_ICONS[alert.category] || AlertTriangle;
                const prCfg = PRIORITY_CONFIG[alert.priority] || PRIORITY_CONFIG.MEDIUM;
                const isSelected = selectedAlert?.id === alert.id;
                return (
                  <div
                    key={alert.id}
                    onClick={() => setSelectedAlert(isSelected ? null : alert)}
                    style={{
                      padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)',
                      cursor: 'pointer', transition: 'background 0.1s',
                      background: isSelected ? 'rgba(59,130,246,0.06)' : 'transparent',
                      borderLeft: isSelected ? '3px solid var(--accent-primary)' : '3px solid transparent',
                    }}
                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', flex: 1, minWidth: 0 }}>
                        {/* Category icon */}
                        <div style={{
                          width: '36px', height: '36px', borderRadius: '8px',
                          background: prCfg.color + '18', border: `1px solid ${prCfg.color}30`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                        }}>
                          <CatIcon size={16} color={prCfg.color} />
                        </div>

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>{alert.id}</span>
                            <StatusBadge status={alert.status} />
                            <span style={{
                              padding: '2px 6px', borderRadius: '3px', fontSize: '0.68rem',
                              fontWeight: 700, textTransform: 'uppercase',
                              background: prCfg.color + '15', color: prCfg.color
                            }}>{alert.priority}</span>
                          </div>
                          <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)', marginBottom: '3px' }}>
                            {alert.trigger}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            Actor: <span style={{ color: 'var(--accent-primary)' }}>{alert.actor}</span>
                            {' · '}
                            <span style={{ color: 'var(--text-muted)' }}>{alert.source}</span>
                          </div>
                        </div>
                      </div>

                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {new Date(alert.timestamp).toLocaleDateString()}
                        </div>
                        <div style={{ marginTop: '4px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
                          color: alert.confidence >= 80 ? '#22c55e' : alert.confidence >= 60 ? '#f59e0b' : '#94a3b8'
                        }}>
                          {alert.confidence}% conf
                        </div>
                      </div>
                    </div>

                    {/* Evidence snippet */}
                    <div style={{
                      marginTop: '10px', padding: '8px 12px', borderRadius: '4px',
                      background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)',
                      fontSize: '0.78rem', color: 'var(--text-muted)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                    }}>
                      {alert.evidence}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedAlert && (
          <div className="card" style={{ position: 'sticky', top: '20px' }}>
            <div className="card-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Eye size={16} color="var(--accent-primary)" />
                <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>Alert Detail</span>
              </div>
              <button className="btn-ghost" style={{ padding: '4px', cursor: 'pointer', background: 'none', border: 'none' }}
                onClick={() => setSelectedAlert(null)}>
                <X size={16} color="var(--text-muted)" />
              </button>
            </div>

            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Status */}
              <div>
                <div className="section-label">Status</div>
                <StatusBadge status={selectedAlert.status} />
              </div>

              {/* Alert ID & Trigger */}
              <div>
                <div className="section-label">Trigger</div>
                <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>{selectedAlert.trigger}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Rule: {selectedAlert.rule}
                </div>
              </div>

              {/* Actor */}
              <div>
                <div className="section-label">Linked Actor</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <User size={14} color="var(--accent-primary)" />
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{selectedAlert.actor}</span>
                </div>
              </div>

              {/* Source & Timestamp */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <div className="section-label">Source</div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{selectedAlert.source}</div>
                </div>
                <div>
                  <div className="section-label">Detected</div>
                  <div style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    {new Date(selectedAlert.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Confidence */}
              <div>
                <div className="section-label">Confidence</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ flex: 1, height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px' }}>
                    <div style={{
                      width: `${selectedAlert.confidence}%`, height: '100%', borderRadius: '3px',
                      background: selectedAlert.confidence >= 80 ? '#22c55e' : selectedAlert.confidence >= 60 ? '#f59e0b' : '#94a3b8'
                    }} />
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                    {selectedAlert.confidence}%
                  </span>
                </div>
              </div>

              {/* Evidence */}
              <div>
                <div className="section-label">Evidence</div>
                <div style={{
                  padding: '12px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--border-subtle)', fontSize: '0.82rem',
                  color: 'var(--text-secondary)', lineHeight: '1.5'
                }}>
                  {selectedAlert.evidence}
                </div>
              </div>

              {/* Analyst Actions */}
              <div>
                <div className="section-label">Analyst Review</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => updateStatus(selectedAlert.id, 'CONFIRMED_BY_ANALYST')}
                      className="btn btn-sm"
                      style={{ flex: 1, background: 'rgba(34,197,94,0.12)', color: '#86efac', border: '1px solid rgba(34,197,94,0.3)', justifyContent: 'center' }}>
                      <CheckCircle size={13} /> Confirm
                    </button>
                    <button
                      onClick={() => updateStatus(selectedAlert.id, 'REVIEWED')}
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1, justifyContent: 'center' }}>
                      <Eye size={13} /> Reviewed
                    </button>
                    <button
                      onClick={() => updateStatus(selectedAlert.id, 'DISMISSED')}
                      className="btn btn-sm"
                      style={{ flex: 1, background: 'rgba(71,85,105,0.12)', color: '#94a3b8', border: '1px solid rgba(71,85,105,0.3)', justifyContent: 'center' }}>
                      <X size={13} /> Dismiss
                    </button>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '6px', fontSize: '0.75rem', color: '#fcd34d' }}>
                    <Info size={12} style={{ display: 'inline', marginRight: '6px' }} />
                    "Confirmed by analyst" affirms the analytical relationship only. It does not confirm legal identity.
                  </div>
                </div>
              </div>

              {/* Analyst Note */}
              <div>
                <div className="section-label">Analyst Note</div>
                <textarea
                  value={analystNote} onChange={e => setAnalystNote(e.target.value)}
                  placeholder="Add investigation notes..."
                  className="form-input"
                  style={{ minHeight: '80px', resize: 'vertical', fontSize: '0.82rem' }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
