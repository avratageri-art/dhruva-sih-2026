import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Users, Search, ChevronDown, ChevronRight, Key, Wallet, User, Globe, Shield, RefreshCw, ExternalLink } from 'lucide-react';
import axios from 'axios';

const API = 'http://localhost:8000';

const confidenceColor = (level) => {
  if (level === 'VERY HIGH' || level === 'CRITICAL') return 'var(--danger)';
  if (level === 'HIGH') return '#f59e0b';
  if (level === 'MODERATE' || level === 'MEDIUM') return 'var(--accent-primary)';
  return 'var(--text-muted)';
};

const confidenceBadgeClass = (level) => {
  if (level === 'VERY HIGH' || level === 'CRITICAL') return 'badge-critical';
  if (level === 'HIGH') return 'badge-high';
  if (level === 'MODERATE' || level === 'MEDIUM') return 'badge-medium';
  return 'badge-neutral';
};

const statusBadge = (status) => {
  if (status === 'ACTIVE') return 'badge-low';
  if (status === 'INACTIVE') return 'badge-neutral';
  if (status === 'SUSPECTED') return 'badge-medium';
  return 'badge-neutral';
};

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 85 ? 'var(--danger)' : pct >= 70 ? '#f59e0b' : pct >= 50 ? 'var(--accent-primary)' : 'var(--text-muted)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <div className="confidence-bar" style={{ flex: 1, height: '5px' }}>
        <div className="confidence-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color, minWidth: '38px' }}>
        {pct}%
      </span>
    </div>
  );
}

function ActorRow({ actor, onExpand, expanded }) {
  return (
    <>
      <tr
        style={{ cursor: 'pointer', borderBottom: '1px solid var(--border-subtle)',
                 background: expanded ? 'rgba(59,130,246,0.04)' : 'transparent' }}
        className="actor-row"
      >
        <td onClick={() => onExpand(actor.id)} style={{ padding: '14px 16px', width: '30px' }}>
          {expanded
            ? <ChevronDown size={15} color="var(--text-muted)" />
            : <ChevronRight size={15} color="var(--text-muted)" />}
        </td>
        <td style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-elevated)',
                          border: `2px solid ${confidenceColor(actor.confidence_level)}`,
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <User size={15} color={confidenceColor(actor.confidence_level)} />
            </div>
            <div>
              <Link
                to={`/actors/${actor.id}`}
                style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)', fontSize: '0.9rem', textDecoration: 'none' }}
                onClick={e => e.stopPropagation()}
              >
                {actor.actor_name}
              </Link>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                {actor.category}
              </div>
            </div>
          </div>
        </td>
        <td style={{ padding: '14px 16px' }}>
          <span className={`badge ${statusBadge(actor.status)}`}>{actor.status}</span>
        </td>
        <td style={{ padding: '14px 16px' }}>
          <div style={{ width: '160px' }}>
            <ConfidenceBar value={actor.confidence} />
          </div>
        </td>
        <td style={{ padding: '14px 16px' }}>
          <span className={`badge ${confidenceBadgeClass(actor.confidence_level)}`}>
            {actor.confidence_level}
          </span>
        </td>
        <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
          <div style={{ display: 'flex', gap: '12px', color: 'var(--text-secondary)' }}>
            <span title="Handles"><User size={13} style={{ display: 'inline', marginRight: 3 }} />{actor.handle_count}</span>
            <span title="PGP Keys"><Key size={13} style={{ display: 'inline', marginRight: 3 }} />{actor.pgp_count}</span>
            <span title="Wallets"><Wallet size={13} style={{ display: 'inline', marginRight: 3 }} />{actor.wallet_count}</span>
          </div>
        </td>
        <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {actor.last_seen ? new Date(actor.last_seen).toLocaleDateString() : '—'}
        </td>
      </tr>
      {expanded && <ActorDetailRow actorId={actor.id} />}
    </>
  );
}

function ActorDetailRow({ actorId }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/api/actors/${actorId}`)
      .then(r => { setDetail(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [actorId]);

  if (loading) {
    return (
      <tr><td colSpan={7} style={{ padding: '20px', background: 'var(--bg-surface)' }}>
        <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          Loading actor intelligence...
        </div>
      </td></tr>
    );
  }

  if (!detail) return null;

  return (
    <tr style={{ background: 'var(--bg-surface)' }}>
      <td colSpan={7} style={{ padding: '0', borderBottom: '2px solid var(--border-accent)' }}>
        <div style={{ padding: '24px 32px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px' }}>
          {/* Description */}
          <div>
            <div className="section-label" style={{ marginBottom: '10px' }}>Actor Profile</div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.6 }}>
              {detail.description || 'No description available.'}
            </p>
            {detail.platforms?.length > 0 && (
              <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {detail.platforms.map(p => (
                  <span key={p} className="badge badge-info"><Globe size={10} style={{ marginRight: 3 }} />{p}</span>
                ))}
              </div>
            )}
          </div>

          {/* Identifiers */}
          <div>
            <div className="section-label" style={{ marginBottom: '10px' }}>Identifiers</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {detail.handles?.map(h => (
                <div key={h.id} className="evidence-item" style={{ padding: '6px 0' }}>
                  <User size={13} color="var(--accent-primary)" />
                  <div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)' }}>{h.handle}</span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: '8px' }}>{h.platform}</span>
                  </div>
                </div>
              ))}
              {detail.pgp_identifiers?.slice(0, 2).map(p => (
                <div key={p.id} className="evidence-item" style={{ padding: '6px 0' }}>
                  <Key size={13} color="var(--success)" />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {p.fingerprint.slice(0, 24)}...
                  </span>
                </div>
              ))}
              {detail.wallets?.slice(0, 2).map(w => (
                <div key={w.id} className="evidence-item" style={{ padding: '6px 0' }}>
                  <Wallet size={13} color="var(--warning)" />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    [{w.blockchain}] {w.address.slice(0, 18)}...
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Posts */}
          <div>
            <div className="section-label" style={{ marginBottom: '10px' }}>Recent Intelligence</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {detail.recent_posts?.slice(0, 3).map(p => (
                <div key={p.id} style={{ padding: '10px', background: 'var(--bg-elevated)',
                                         borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>{p.platform}</span>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {p.timestamp ? new Date(p.timestamp).toLocaleDateString() : ''}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                    {p.content.length > 90 ? p.content.slice(0, 90) + '...' : p.content}
                  </p>
                </div>
              ))}
              {(!detail.recent_posts || detail.recent_posts.length === 0) && (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No posts recorded.</p>
              )}
            </div>
          </div>
        </div>

        {/* Action Bar */}
        <div style={{ padding: '12px 32px', background: 'rgba(0,0,0,0.2)', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Full intelligence dossier available with 15 investigative tabs, AI attribution math & crawler telemetry.
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <Link to={`/actors/${actorId}`} className="btn btn-primary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Shield size={14} /> Open Full 15-Tab Intelligence Profile
            </Link>
            <Link to={`/graph?actorId=${actorId}`} className="btn btn-secondary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ExternalLink size={14} /> Open in Graph
            </Link>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function Actors() {
  const [actors, setActors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [filter, setFilter] = useState({ status: '', category: '' });

  const fetchActors = () => {
    setLoading(true);
    const params = {};
    if (search) params.search = search;
    if (filter.status) params.status = filter.status;
    if (filter.category) params.category = filter.category;

    axios.get(`${API}/api/actors`, { params })
      .then(r => { setActors(r.data); setLoading(false); })
      .catch(() => {
        // Demo fallback data
        setActors([
          { id: 1, actor_name: 'ShadowFox', category: 'Ransomware Operator', status: 'ACTIVE', confidence: 0.94,
            confidence_level: 'VERY HIGH', handle_count: 4, pgp_count: 2, wallet_count: 3, last_seen: '2024-01-15T10:00:00' },
          { id: 2, actor_name: 'ZeroByte', category: 'Exploit Developer', status: 'ACTIVE', confidence: 0.87,
            confidence_level: 'HIGH', handle_count: 3, pgp_count: 1, wallet_count: 2, last_seen: '2024-01-10T10:00:00' },
          { id: 3, actor_name: 'CrimsonAdmin', category: 'Data Broker', status: 'ACTIVE', confidence: 0.82,
            confidence_level: 'HIGH', handle_count: 3, pgp_count: 2, wallet_count: 3, last_seen: '2024-01-12T10:00:00' },
        ]);
        setLoading(false);
      });
  };

  useEffect(() => { fetchActors(); }, []);

  const handleExpand = (id) => setExpandedId(prev => prev === id ? null : id);

  const filtered = actors.filter(a =>
    (!search || a.actor_name.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' }}>
        <div>
          <h1 style={{ margin: 0 }}>Threat Actors</h1>
          <p style={{ color: 'var(--text-secondary)', margin: '6px 0 0 0' }}>
            {actors.length} tracked actors · Click any row to expand intelligence
          </p>
        </div>
        <button className="btn btn-secondary" onClick={fetchActors} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="glass-card" style={{ padding: '16px 20px', marginBottom: '20px', display: 'flex', gap: '16px', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '360px' }}>
          <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            className="form-input"
            type="text"
            placeholder="Search actors..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ paddingLeft: '36px' }}
          />
        </div>
        <select className="form-select" value={filter.status} onChange={e => setFilter(f => ({ ...f, status: e.target.value }))} style={{ width: '140px' }}>
          <option value="">All Status</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
          <option value="SUSPECTED">Suspected</option>
        </select>
        <select className="form-select" value={filter.category} onChange={e => setFilter(f => ({ ...f, category: e.target.value }))} style={{ width: '200px' }}>
          <option value="">All Categories</option>
          <option value="Ransomware Operator">Ransomware</option>
          <option value="Exploit Developer">Exploit Dev</option>
          <option value="Data Broker">Data Broker</option>
          <option value="Access Broker">Access Broker</option>
          <option value="DDoS-for-Hire">DDoS</option>
          <option value="Hacktivist">Hacktivist</option>
        </select>
        <button className="btn btn-primary btn-sm" onClick={fetchActors}>Apply</button>
      </div>

      {/* Table */}
      <div className="card" style={{ overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '30px' }}></th>
              <th>Actor</th>
              <th>Status</th>
              <th style={{ minWidth: '200px' }}>Attribution Confidence</th>
              <th>Level</th>
              <th>Identifiers</th>
              <th>Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div className="spin" style={{ display: 'inline-block', marginRight: '10px' }}>⟳</div>
                Loading actor intelligence...
              </td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={7} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Users size={32} style={{ display: 'block', margin: '0 auto 10px' }} />
                No actors found
              </td></tr>
            ) : filtered.map(actor => (
              <ActorRow
                key={actor.id}
                actor={actor}
                expanded={expandedId === actor.id}
                onExpand={handleExpand}
              />
            ))}
          </tbody>
        </table>
      </div>

      <style>{`
        .actor-row:hover td { background: rgba(59,130,246,0.03) !important; }
      `}</style>
    </div>
  );
}
