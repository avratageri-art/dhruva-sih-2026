import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Clock, Filter, User, Hash, Key, Wallet, Server, Globe,
  Shield, AlertTriangle, Search, ChevronDown, ChevronRight,
  Network, FileText, Activity
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const EVENT_CONFIG = {
  POST: { color: '#3b82f6', icon: FileText, label: 'Post' },
  HANDLE_REGISTERED: { color: '#06b6d4', icon: Hash, label: 'Handle Registered' },
  PGP_OBSERVED: { color: '#a855f7', icon: Key, label: 'PGP Observed' },
  WALLET_OBSERVED: { color: '#10b981', icon: Wallet, label: 'Wallet Observed' },
  PLATFORM_ACTIVITY: { color: '#f59e0b', icon: Globe, label: 'Platform Activity' },
  INFRASTRUCTURE_CHANGE: { color: '#ef4444', icon: Server, label: 'Infrastructure' },
  RELATIONSHIP_DISCOVERED: { color: '#ec4899', icon: Network, label: 'Relationship' },
};

function EventBadge({ type }) {
  const cfg = EVENT_CONFIG[type] || { color: '#94a3b8', icon: Activity, label: type };
  const Icon = cfg.icon;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '3px 8px', borderRadius: '4px', fontSize: '0.7rem',
      fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
      background: cfg.color + '18', color: cfg.color,
      border: `1px solid ${cfg.color}40`,
    }}>
      <Icon size={10} />
      {cfg.label}
    </span>
  );
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 85 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#94a3b8';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '2px' }} />
      </div>
      <span style={{ fontSize: '0.75rem', color, fontFamily: 'var(--font-mono)', minWidth: '36px' }}>{pct}%</span>
    </div>
  );
}

export default function Timeline() {
  const [actors, setActors] = useState([]);
  const [selectedActor, setSelectedActor] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState('ALL');
  const [searchQ, setSearchQ] = useState('');
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    axios.get(`${API_BASE}/api/actors?limit=25`)
      .then(r => {
        setActors(r.data);
        // Auto-select ShadowFox for the demo
        const sf = r.data.find(a => a.actor_name === 'ShadowFox') || r.data[0];
        if (sf) setSelectedActor(sf);
      })
      .catch(() => setActors([]));
  }, []);

  useEffect(() => {
    if (!selectedActor) return;
    setLoading(true);
    axios.get(`${API_BASE}/api/actors/${selectedActor.id}/timeline`)
      .then(r => setEvents(r.data))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [selectedActor]);

  const EVENT_TYPES = ['ALL', 'POST', 'HANDLE_REGISTERED', 'PGP_OBSERVED', 'WALLET_OBSERVED'];

  const filtered = events.filter(e => {
    if (filterType !== 'ALL' && e.type !== filterType) return false;
    if (searchQ && !e.summary?.toLowerCase().includes(searchQ.toLowerCase()) &&
        !e.platform?.toLowerCase().includes(searchQ.toLowerCase())) return false;
    return true;
  });

  // Group events by month
  const grouped = filtered.reduce((acc, ev) => {
    const key = ev.date ? ev.date.substring(0, 7) : 'Unknown';
    if (!acc[key]) acc[key] = [];
    acc[key].push(ev);
    return acc;
  }, {});

  const cfg = (type) => EVENT_CONFIG[type] || { color: '#94a3b8', icon: Activity };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.6rem' }}>Activity Timeline</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '0.9rem' }}>
            Chronological intelligence events for tracked threat actor personas.
          </p>
        </div>
        <span style={{
          padding: '4px 12px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700,
          background: 'rgba(245,158,11,0.1)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)',
          letterSpacing: '0.06em'
        }}>CONTROLLED DEMO DATA</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '20px', alignItems: 'start' }}>
        {/* Left panel — actor selector + filters */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Actor Selector */}
          <div className="card">
            <div className="card-header" style={{ padding: '14px 16px' }}>
              <User size={16} color="var(--accent-primary)" />
              <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>Select Actor</span>
            </div>
            <div style={{ padding: '8px' }}>
              {actors.map(a => (
                <button
                  key={a.id}
                  onClick={() => setSelectedActor(a)}
                  style={{
                    width: '100%', textAlign: 'left', padding: '9px 12px',
                    borderRadius: '6px', cursor: 'pointer',
                    background: selectedActor?.id === a.id ? 'rgba(59,130,246,0.12)' : 'transparent',
                    border: selectedActor?.id === a.id ? '1px solid rgba(59,130,246,0.3)' : '1px solid transparent',
                    color: selectedActor?.id === a.id ? '#93c5fd' : 'var(--text-secondary)',
                    fontSize: '0.875rem', fontFamily: 'var(--font-sans)',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    marginBottom: '2px'
                  }}
                >
                  <span>{a.actor_name}</span>
                  <span style={{
                    fontSize: '0.7rem', fontFamily: 'var(--font-mono)',
                    color: a.confidence >= 0.8 ? '#22c55e' : '#f59e0b'
                  }}>{Math.round((a.confidence || 0) * 100)}%</span>
                </button>
              ))}
            </div>
          </div>

          {/* Event Type Filter */}
          <div className="card">
            <div className="card-header" style={{ padding: '14px 16px' }}>
              <Filter size={16} color="var(--text-secondary)" />
              <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>Event Filter</span>
            </div>
            <div style={{ padding: '8px' }}>
              {EVENT_TYPES.map(type => (
                <button
                  key={type}
                  onClick={() => setFilterType(type)}
                  style={{
                    width: '100%', textAlign: 'left', padding: '8px 12px',
                    borderRadius: '4px', cursor: 'pointer', marginBottom: '2px',
                    background: filterType === type ? 'rgba(255,255,255,0.06)' : 'transparent',
                    border: 'none', color: filterType === type ? 'var(--text-primary)' : 'var(--text-muted)',
                    fontSize: '0.8rem', fontFamily: 'var(--font-sans)',
                    display: 'flex', alignItems: 'center', gap: '8px',
                  }}
                >
                  {type !== 'ALL' && <span style={{
                    width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
                    background: (EVENT_CONFIG[type] || { color: '#94a3b8' }).color
                  }} />}
                  {type === 'ALL' ? '· All Events' : (EVENT_CONFIG[type]?.label || type)}
                </button>
              ))}
            </div>
          </div>

          {/* Stats */}
          {selectedActor && (
            <div className="card" style={{ padding: '16px' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>
                {selectedActor.actor_name} — Summary
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Total Events</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{events.length}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Posts</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: '#3b82f6' }}>
                    {events.filter(e => e.type === 'POST').length}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Identifiers</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: '#a855f7' }}>
                    {events.filter(e => ['PGP_OBSERVED', 'HANDLE_REGISTERED'].includes(e.type)).length}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Wallet Obs.</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: '#10b981' }}>
                    {events.filter(e => e.type === 'WALLET_OBSERVED').length}
                  </span>
                </div>
                <div className="divider" style={{ margin: '4px 0' }} />
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Confidence</div>
                  <ConfidenceBar value={selectedActor.confidence} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right panel — timeline */}
        <div className="card">
          <div className="card-header" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Clock size={18} color="var(--accent-primary)" />
              <span style={{ fontWeight: 600 }}>
                {selectedActor ? `${selectedActor.actor_name} — Timeline` : 'Select an actor'}
              </span>
              <span className="badge badge-neutral">{filtered.length} events</span>
            </div>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                value={searchQ}
                onChange={e => setSearchQ(e.target.value)}
                placeholder="Search events..."
                className="form-input"
                style={{ paddingLeft: '32px', width: '220px', fontSize: '0.82rem' }}
              />
            </div>
          </div>

          <div className="card-body" style={{ padding: '0' }}>
            {loading && (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                Loading intelligence events...
              </div>
            )}

            {!loading && filtered.length === 0 && (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                {selectedActor ? 'No events match the current filters.' : 'Select an actor to view their timeline.'}
              </div>
            )}

            {!loading && Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([month, evs]) => (
              <div key={month}>
                {/* Month header */}
                <div
                  style={{
                    padding: '10px 20px', background: 'rgba(255,255,255,0.02)',
                    borderBottom: '1px solid var(--border-subtle)',
                    borderTop: '1px solid var(--border-subtle)',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    cursor: 'pointer'
                  }}
                  onClick={() => setExpanded(p => ({ ...p, [month]: !p[month] }))}
                >
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {new Date(month + '-01').toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="badge badge-neutral">{evs.length}</span>
                    {expanded[month] ? <ChevronDown size={14} color="var(--text-muted)" /> : <ChevronRight size={14} color="var(--text-muted)" />}
                  </div>
                </div>

                {/* Events in month */}
                {!expanded[month] && evs.map((ev, idx) => {
                  const evCfg = cfg(ev.type);
                  const Icon = evCfg.icon;
                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex', gap: '16px', padding: '14px 20px',
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      {/* Dot + line */}
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '20px', flexShrink: 0 }}>
                        <div style={{
                          width: '28px', height: '28px', borderRadius: '50%',
                          background: evCfg.color + '20',
                          border: `1.5px solid ${evCfg.color}60`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                        }}>
                          <Icon size={13} color={evCfg.color} />
                        </div>
                        {idx < evs.length - 1 && (
                          <div style={{ width: '1px', flex: 1, background: 'var(--border-subtle)', marginTop: '4px' }} />
                        )}
                      </div>

                      {/* Content */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            {ev.date ? ev.date.split('T')[0] : '—'}
                          </span>
                          <EventBadge type={ev.type} />
                          {ev.platform && (
                            <span style={{
                              padding: '2px 7px', borderRadius: '3px', fontSize: '0.7rem',
                              background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)'
                            }}>{ev.platform}</span>
                          )}
                        </div>
                        <p style={{
                          fontSize: '0.875rem', color: 'var(--text-primary)',
                          lineHeight: '1.5', margin: 0,
                          overflow: 'hidden', textOverflow: 'ellipsis',
                          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical'
                        }}>
                          {ev.summary}
                        </p>
                        {ev.confidence !== undefined && (
                          <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Confidence</span>
                            <div style={{ width: '80px', height: '3px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px' }}>
                              <div style={{
                                width: `${Math.round(ev.confidence * 100)}%`, height: '100%',
                                background: evCfg.color, borderRadius: '2px'
                              }} />
                            </div>
                            <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: evCfg.color }}>
                              {Math.round(ev.confidence * 100)}%
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
