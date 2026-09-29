import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, Hash, Key, Wallet, Server, Network, Shield, AlertTriangle,
  Activity, ArrowRight, TrendingUp, Clock, Globe, CheckCircle,
  RefreshCw, ExternalLink
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const CONFIDENCE_COLORS = {
  'VERY HIGH': '#22c55e',
  'HIGH': '#3b82f6',
  'MODERATE': '#f59e0b',
  'LOW': '#94a3b8',
};

function KPICard({ title, value, icon: Icon, color = 'var(--accent-primary)', subtitle, onClick }) {
  return (
    <div
      className="card"
      onClick={onClick}
      style={{ padding: '20px', cursor: onClick ? 'pointer' : 'default', transition: 'border-color 0.15s' }}
      onMouseEnter={e => { if (onClick) e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
          {title}
        </div>
        <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: color + '18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={16} color={color} />
        </div>
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color, lineHeight: 1 }}>
        {value !== null && value !== undefined ? value : <span style={{ fontSize: '1.4rem', color: 'var(--text-muted)' }}>—</span>}
      </div>
      {subtitle && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>{subtitle}</div>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '6px', padding: '10px 14px', fontSize: '0.8rem' }}>
        <div style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>{label}</div>
        {payload.map((p, i) => (
          <div key={i} style={{ color: p.color || 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {p.name}: {p.value}
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [actors, setActors] = useState([]);
  const [assessments, setAssessments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  function fetchAll() {
    setLoading(true);
    Promise.all([
      axios.get(`${API_BASE}/api/dashboard`).then(r => r.data).catch(() => null),
      axios.get(`${API_BASE}/api/actors?limit=5`).then(r => r.data).catch(() => []),
      axios.get(`${API_BASE}/api/analysis/assessments?limit=5`).then(r => r.data).catch(() => []),
    ]).then(([s, a, aa]) => {
      setStats(s);
      setActors(a);
      setAssessments(aa);
      setLastRefresh(new Date());
    }).finally(() => setLoading(false));
  }

  useEffect(() => { fetchAll(); }, []);

  // Build confidence distribution for pie chart from actors
  const confDist = Object.entries(
    actors.reduce((acc, a) => {
      const level = a.confidence_level || 'LOW';
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    }, {})
  ).map(([name, value]) => ({ name, value, color: CONFIDENCE_COLORS[name] || '#94a3b8' }));

  // Category distribution
  const catDist = actors.reduce((acc, a) => {
    const cat = (a.category || 'Unknown').split(' ').slice(0, 2).join(' ');
    acc[cat] = (acc[cat] || 0) + 1;
    return acc;
  }, {});
  const catChartData = Object.entries(catDist).map(([name, value]) => ({ name, value }));

  return (
    <div className="fade-in">
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0 }}>Command Center</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '0.9rem' }}>
            Global threat intelligence overview — Tor SOCKS5 darknet intelligence collection engine.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Updated {lastRefresh.toLocaleTimeString()}
          </div>
          <button onClick={fetchAll} className="btn btn-secondary btn-sm">
            <RefreshCw size={13} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Live CTI banner */}
      <div style={{ marginBottom: '20px', padding: '12px 16px', borderRadius: '8px', background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Shield size={16} color="#10b981" />
        <span style={{ fontSize: '0.82rem', color: '#6ee7b7', fontWeight: 500 }}>
          LIVE THREAT INTELLIGENCE PLATFORM — Automated Darknet Source Discovery via Tor SOCKS5 & deepdarkCTI Registry.
        </span>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-4" style={{ marginBottom: '24px', gap: '14px' }}>
        <KPICard title="Tracked Actors" value={stats?.actors} icon={Users} color="#3b82f6"
          subtitle="Active threat personas" onClick={() => navigate('/actors')} />
        <KPICard title="Correlated Handles" value={stats?.handles} icon={Hash} color="#06b6d4"
          subtitle="Cross-platform identifiers" />
        <KPICard title="PGP Identifiers" value={stats?.pgps} icon={Key} color="#a855f7"
          subtitle="Key-based correlations" />
        <KPICard title="Wallets" value={stats?.wallets} icon={Wallet} color="#10b981"
          subtitle="Cryptocurrency addresses" />
        <KPICard title="Monitored Services" value={stats?.services} icon={Server} color="#94a3b8"
          subtitle="Onion services" />
        <KPICard title="Relationships" value={stats?.relationships} icon={Network} color="#64748b"
          subtitle="Entity linkages" />
        <KPICard title="High-Confidence" value={stats?.high_confidence} icon={Shield} color="#f59e0b"
          subtitle="Score ≥ 85%" onClick={() => navigate('/persona-analysis')} />
        <KPICard title="Open Alerts" value={stats?.alerts} icon={AlertTriangle} color="#ef4444"
          subtitle="Awaiting review" onClick={() => navigate('/alerts')} />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-3" style={{ gap: '16px', marginBottom: '16px' }}>
        {/* Recent Actors */}
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="card-header" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Users size={16} color="var(--accent-primary)" />
              <span style={{ fontWeight: 600 }}>Top Threat Actors</span>
            </div>
            <button onClick={() => navigate('/actors')} className="btn btn-ghost btn-sm">
              View All <ArrowRight size={13} />
            </button>
          </div>
          <div>
            {loading ? (
              <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading actors...</div>
            ) : actors.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No actors found. <button onClick={() => navigate('/actors')} style={{ color: 'var(--accent-primary)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.85rem' }}>Run seed script</button>.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Actor</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Last Active</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {actors.map(a => {
                    const confColor = CONFIDENCE_COLORS[a.confidence_level] || '#94a3b8';
                    const confPct = Math.round((a.confidence || 0) * 100);
                    return (
                      <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/actors/${a.id}`)}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.875rem' }}>{a.actor_name}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '1px' }}>
                            {a.handle_count} handles · {a.pgp_count} PGP · {a.wallet_count} wallets
                          </div>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.78rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(239,68,68,0.1)', color: '#fca5a5', border: '1px solid rgba(239,68,68,0.2)' }}>
                            {a.category}
                          </span>
                        </td>
                        <td>
                          <span style={{
                            fontSize: '0.72rem', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', textTransform: 'uppercase',
                            background: a.status === 'ACTIVE' ? 'rgba(34,197,94,0.1)' : 'rgba(148,163,184,0.1)',
                            color: a.status === 'ACTIVE' ? '#86efac' : '#94a3b8',
                            border: a.status === 'ACTIVE' ? '1px solid rgba(34,197,94,0.25)' : '1px solid rgba(148,163,184,0.2)'
                          }}>{a.status}</span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ width: '60px', height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px' }}>
                              <div style={{ width: `${confPct}%`, height: '100%', background: confColor, borderRadius: '2px' }} />
                            </div>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: confColor }}>{confPct}%</span>
                          </div>
                        </td>
                        <td style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                          {a.last_seen ? a.last_seen.split('T')[0] : '—'}
                        </td>
                        <td><ExternalLink size={13} color="var(--text-muted)" /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Confidence Distribution Pie */}
        <div className="card">
          <div className="card-header">
            <TrendingUp size={16} color="var(--text-secondary)" />
            <span style={{ fontWeight: 600 }}>Confidence Distribution</span>
          </div>
          <div style={{ padding: '16px' }}>
            {confDist.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie data={confDist} cx="50%" cy="50%" innerRadius={45} outerRadius={70}
                      paddingAngle={3} dataKey="value" stroke="none">
                      {confDist.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '6px', fontSize: '0.8rem' }} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {confDist.map((d, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '2px', background: d.color }} />
                        <span style={{ color: 'var(--text-secondary)' }}>{d.name}</span>
                      </div>
                      <span style={{ fontFamily: 'var(--font-mono)', color: d.color }}>{d.value}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-3" style={{ gap: '16px' }}>
        {/* High-Confidence Assessments */}
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="card-header" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Shield size={16} color="#f59e0b" />
              <span style={{ fontWeight: 600 }}>Attribution Assessments</span>
            </div>
            <button onClick={() => navigate('/persona-analysis')} className="btn btn-ghost btn-sm">
              View All <ArrowRight size={13} />
            </button>
          </div>
          {assessments.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No assessments yet. Run persona analysis to generate attribution scores.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Actor A</th>
                  <th>Actor B</th>
                  <th>Score</th>
                  <th>Confidence</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {assessments.map(aa => {
                  const score = aa.score >= 1 ? Math.round(aa.score) : Math.round(aa.score * 100);
                  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#94a3b8';
                  return (
                    <tr key={aa.id} style={{ cursor: 'pointer' }} onClick={() => navigate('/persona-analysis')}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{aa.actor_a?.name}</td>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{aa.actor_b?.name}</td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1rem', color }}>{score}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>/100</span>
                      </td>
                      <td>
                        <span style={{ padding: '3px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700,
                          background: color + '18', color, border: `1px solid ${color}40` }}>
                          {aa.confidence_level}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        {aa.created_at ? aa.created_at.split('T')[0] : '—'}
                      </td>
                      <td><ExternalLink size={13} color="var(--text-muted)" /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">
            <Activity size={16} color="var(--text-secondary)" />
            <span style={{ fontWeight: 600 }}>Quick Actions</span>
          </div>
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              { label: 'Open ShadowFox Profile', icon: Users, path: '/actors/1', color: '#3b82f6' },
              { label: 'Run Persona Analysis', icon: Shield, path: '/persona-analysis', color: '#a855f7' },
              { label: 'View Graph Intelligence', icon: Network, path: '/graph', color: '#06b6d4' },
              { label: 'Review Alerts', icon: AlertTriangle, path: '/alerts', color: '#ef4444' },
              { label: 'Export Reports', icon: CheckCircle, path: '/reports', color: '#22c55e' },
              { label: 'Architecture Overview', icon: Globe, path: '/architecture', color: '#f59e0b' },
            ].map((action, i) => {
              const Icon = action.icon;
              return (
                <button
                  key={i}
                  onClick={() => navigate(action.path)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px',
                    borderRadius: '6px', cursor: 'pointer', width: '100%', textAlign: 'left',
                    background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)', fontSize: '0.82rem',
                    transition: 'all 0.12s', fontFamily: 'var(--font-sans)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = action.color + '10'; e.currentTarget.style.borderColor = action.color + '40'; e.currentTarget.style.color = 'var(--text-primary)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
                >
                  <Icon size={15} color={action.color} />
                  {action.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
