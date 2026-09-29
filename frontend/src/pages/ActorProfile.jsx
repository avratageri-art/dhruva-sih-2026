import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import {
  User, Shield, Key, Wallet, Globe, Server, Activity, Network, Clock,
  FileText, Database, AlertTriangle, ExternalLink, Copy, Check, Search,
  Terminal, BarChart2, Cpu, CheckCircle, ArrowRight, Share2, Layers,
  ChevronRight, Lock, Eye, AlertCircle, RefreshCw, Filter
} from 'lucide-react';

const API = 'http://localhost:8000';

const confidenceColor = (level) => {
  if (level === 'CRITICAL' || level === 'VERY HIGH') return '#ef4444';
  if (level === 'HIGH') return '#f59e0b';
  if (level === 'MEDIUM' || level === 'MODERATE') return '#3b82f6';
  return '#94a3b8';
};

const confidenceBadgeClass = (level) => {
  if (level === 'CRITICAL' || level === 'VERY HIGH') return 'badge-critical';
  if (level === 'HIGH') return 'badge-high';
  if (level === 'MEDIUM' || level === 'MODERATE') return 'badge-medium';
  return 'badge-neutral';
};

export default function ActorProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [copiedText, setCopiedText] = useState(null);
  const [postSearch, setPostSearch] = useState('');

  const fetchActorData = () => {
    setLoading(true);
    axios.get(`${API}/api/actors/${id}`)
      .then(res => {
        setData(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load actor profile", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchActorData();
  }, [id]);

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2000);
  };

  if (loading) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <RefreshCw size={36} className="spin" style={{ display: 'block', margin: '0 auto 16px', color: 'var(--accent-primary)' }} />
        <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
          Loading Threat Intelligence Profile...
        </div>
        <div style={{ fontSize: '0.85rem' }}>Extracting forensic anchors, AI embeddings & cross-platform telemetry</div>
      </div>
    );
  }

  if (!data || !data.header) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <AlertTriangle size={48} color="#ef4444" style={{ display: 'block', margin: '0 auto 16px' }} />
        <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>Threat Actor Not Found</div>
        <p style={{ color: 'var(--text-muted)', margin: '12px 0 24px' }}>No actor matched ID #{id} in the database.</p>
        <button className="btn btn-primary" onClick={() => navigate('/actors')}>Return to Actor Directory</button>
      </div>
    );
  }

  const { header, overview, handles, pgp_identifiers, wallets, posts, platforms, onion_services, infrastructure, behaviour, persona_ai, evidence, attribution, timeline, relationships, collection_history } = data;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: User, count: null },
    { id: 'handles', label: 'Handles', icon: User, count: header.counts.handles },
    { id: 'pgp', label: 'PGP Keys', icon: Key, count: header.counts.pgps },
    { id: 'wallets', label: 'Wallets', icon: Wallet, count: header.counts.wallets },
    { id: 'posts', label: 'Posts & Comms', icon: Terminal, count: header.counts.posts },
    { id: 'platforms', label: 'Platforms', icon: Globe, count: header.counts.platforms },
    { id: 'onions', label: 'Onion Services', icon: Shield, count: header.counts.onion_services },
    { id: 'infrastructure', label: 'Infrastructure', icon: Server, count: header.counts.infrastructure },
    { id: 'behaviour', label: 'Behaviour', icon: BarChart2, count: null },
    { id: 'persona_ai', label: 'Persona / AI', icon: Cpu, count: persona_ai.length },
    { id: 'evidence', label: 'Evidence', icon: CheckCircle, count: header.counts.evidence },
    { id: 'attribution', label: 'Attribution', icon: Activity, count: `${attribution.final_attribution_score}%` },
    { id: 'timeline', label: 'Timeline', icon: Clock, count: timeline.length },
    { id: 'relationships', label: 'Relationships', icon: Network, count: header.counts.relationships },
    { id: 'collection', label: 'Collection History', icon: Database, count: header.counts.observations },
  ];

  const filteredPosts = posts.filter(p => 
    p.content.toLowerCase().includes(postSearch.toLowerCase()) ||
    p.platform.toLowerCase().includes(postSearch.toLowerCase()) ||
    p.handle.toLowerCase().includes(postSearch.toLowerCase())
  );

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
        <Link to="/actors" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>Threat Actors</Link>
        <ChevronRight size={14} />
        <span style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{header.actor_name}</span>
        <span style={{ marginLeft: 'auto' }} className="badge badge-neutral">ID #{header.id}</span>
      </div>

      {/* Header Profile Card */}
      <div className="card glass-panel" style={{ padding: '28px 32px', marginBottom: '24px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '20px' }}>
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <div style={{
              width: '64px', height: '64px', borderRadius: '14px',
              background: 'rgba(59, 130, 246, 0.12)', border: `2px solid ${confidenceColor(header.confidence_level)}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: `0 0 20px rgba(59, 130, 246, 0.2)`
            }}>
              <Shield size={32} color={confidenceColor(header.confidence_level)} />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <h1 style={{ margin: 0, fontSize: '1.8rem', fontFamily: 'var(--font-mono)', letterSpacing: '-0.02em', color: '#fff' }}>
                  {header.actor_name}
                </h1>
                <span className={`badge ${confidenceBadgeClass(header.confidence_level)}`} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                  {header.confidence_level} RISK ({Math.round((header.confidence || 0.85) * 100)}%)
                </span>
                <span className="badge badge-neutral" style={{ border: '1px solid rgba(255,255,255,0.1)' }}>
                  {header.status}
                </span>
                <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.3)', fontSize: '0.7rem' }}>
                  {header.environment_label}
                </span>
              </div>

              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '6px', maxWidth: '800px' }}>
                {header.description}
              </div>

              <div style={{ display: 'flex', gap: '24px', marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                <span>CATEGORY: <strong style={{ color: 'var(--text-primary)' }}>{header.category}</strong></span>
                <span>FIRST SEEN: <strong style={{ color: 'var(--text-primary)' }}>{header.first_seen ? new Date(header.first_seen).toLocaleDateString() : '—'}</strong></span>
                <span>LAST SEEN: <strong style={{ color: 'var(--text-primary)' }}>{header.last_seen ? new Date(header.last_seen).toLocaleDateString() : '—'}</strong></span>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              className="btn btn-primary"
              onClick={() => navigate(`/graph?actorId=${header.id}`)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 18px', fontWeight: 600 }}
            >
              <Network size={16} /> Open in Graph Intelligence
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => copyToClipboard(window.location.href, 'profile_url')}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {copiedText === 'profile_url' ? <Check size={14} color="#10b981" /> : <Share2 size={14} />}
              {copiedText === 'profile_url' ? 'Link Copied' : 'Share'}
            </button>
          </div>
        </div>

        {/* 10 Forensic Counters */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
          gap: '12px', marginTop: '24px', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.06)'
        }}>
          {[
            { label: 'Handles', val: header.counts.handles, tab: 'handles' },
            { label: 'PGP Keys', val: header.counts.pgps, tab: 'pgp' },
            { label: 'Wallets', val: header.counts.wallets, tab: 'wallets' },
            { label: 'Posts', val: header.counts.posts, tab: 'posts' },
            { label: 'Platforms', val: header.counts.platforms, tab: 'platforms' },
            { label: 'Onion Mirrors', val: header.counts.onion_services, tab: 'onions' },
            { label: 'Infrastructure', val: header.counts.infrastructure, tab: 'infrastructure' },
            { label: 'Relationships', val: header.counts.relationships, tab: 'relationships' },
            { label: 'Evidence Pts', val: header.counts.evidence, tab: 'evidence' },
            { label: 'Observations', val: header.counts.observations, tab: 'collection' },
          ].map((c, i) => (
            <div
              key={i}
              onClick={() => setActiveTab(c.tab)}
              style={{
                background: activeTab === c.tab ? 'rgba(59, 130, 246, 0.15)' : 'rgba(0,0,0,0.2)',
                border: activeTab === c.tab ? '1px solid var(--accent-primary)' : '1px solid rgba(255,255,255,0.05)',
                borderRadius: '8px', padding: '10px', textAlign: 'center', cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ fontSize: '1.3rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {c.val}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '2px' }}>
                {c.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 15-Tab Navigation Bar */}
      <div style={{
        display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '12px', marginBottom: '24px',
        borderBottom: '1px solid rgba(255,255,255,0.08)'
      }}>
        {tabs.map(t => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 16px',
                borderRadius: '8px', whiteSpace: 'nowrap', fontSize: '0.85rem', cursor: 'pointer',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#fff' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-primary)' : 'rgba(255,255,255,0.03)',
                border: isActive ? '1px solid var(--accent-primary)' : '1px solid rgba(255,255,255,0.06)',
                transition: 'all 0.15s ease'
              }}
            >
              <Icon size={15} />
              {t.label}
              {t.count !== null && (
                <span style={{
                  fontSize: '0.7rem', padding: '2px 6px', borderRadius: '10px',
                  background: isActive ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.08)',
                  color: isActive ? '#fff' : 'var(--text-muted)'
                }}>
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="tab-content">
        {/* 1. OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div className="card glass-panel" style={{ padding: '24px' }}>
              <div className="section-label" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={16} color="var(--accent-primary)" /> Primary Identity Anchors
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PRIMARY OPERATIONAL HANDLE</div>
                  <div style={{ fontSize: '1.1rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-primary)', marginTop: '4px' }}>
                    {overview.key_anchors.primary_handle}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PRIMARY PGP CRYPTOGRAPHIC ANCHOR</div>
                  <div style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--success)', marginTop: '4px', wordBreak: 'break-all' }}>
                    {overview.key_anchors.primary_pgp}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PRIMARY EXTORTION / ESCROW WALLET</div>
                  <div style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--warning)', marginTop: '4px', wordBreak: 'break-all' }}>
                    {overview.key_anchors.primary_wallet}
                  </div>
                </div>
              </div>
            </div>

            <div className="card glass-panel" style={{ padding: '24px' }}>
              <div className="section-label" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} color="#f59e0b" /> Assessment Summary & Telemetry
              </div>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, fontSize: '0.9rem' }}>
                {overview.recent_activity}
              </p>
              <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Attribution Engine Score</span>
                  <span style={{ fontWeight: 600, color: confidenceColor(header.confidence_level) }}>{Math.round(header.confidence * 100)}%</span>
                </div>
                <div className="confidence-bar" style={{ height: '8px' }}>
                  <div className="confidence-bar-fill" style={{ width: `${Math.round(header.confidence * 100)}%`, background: confidenceColor(header.confidence_level) }} />
                </div>
              </div>
              <div style={{ marginTop: '24px', padding: '14px', background: 'rgba(59, 130, 246, 0.05)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-primary)', marginBottom: '4px' }}>AI Model Verification</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  All-MiniLM-L6-v2 generated embeddings continuously correlate observed darknet text against threat actor cluster centroids.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 2. HANDLES TAB */}
        {activeTab === 'handles' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '16px' }}>Observed Threat Actor Handles</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Handle</th>
                  <th>Platform</th>
                  <th>Activity Window</th>
                  <th>Posts</th>
                  <th>Confidence</th>
                  <th>Source Provenance</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {handles.map(h => (
                  <tr key={h.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-primary)' }}>
                      {h.handle}
                    </td>
                    <td><span className="badge badge-info">{h.platform}</span></td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {h.first_seen ? new Date(h.first_seen).toLocaleDateString() : '—'} to {h.last_seen ? new Date(h.last_seen).toLocaleDateString() : '—'}
                    </td>
                    <td><span className="badge badge-neutral">{h.post_count} posts</span></td>
                    <td><span className="badge badge-high">{Math.round(h.confidence * 100)}%</span></td>
                    <td>
                      <span title={h.source.name} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {h.source.name} ({Math.round(h.source.reliability * 100)}% rel)
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => copyToClipboard(h.handle, `h_${h.id}`)}>
                        {copiedText === `h_${h.id}` ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 3. PGP TAB */}
        {activeTab === 'pgp' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {pgp_identifiers.map(p => (
              <div key={p.id} className="card glass-panel" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Key size={18} color="var(--success)" />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {p.fingerprint}
                    </span>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={() => copyToClipboard(p.fingerprint, `p_${p.id}`)}>
                    {copiedText === `p_${p.id}` ? <Check size={12} color="#10b981" /> : <Copy size={12} />} Copy Fingerprint
                  </button>
                </div>
                <div style={{ display: 'flex', gap: '20px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span>Source: <strong style={{ color: 'var(--text-secondary)' }}>{p.source.name}</strong></span>
                  <span>Observed Platforms: <strong style={{ color: 'var(--text-secondary)' }}>{p.associated_platforms.join(', ')}</strong></span>
                  <span>Cryptographic Anchor Confidence: <strong style={{ color: 'var(--success)' }}>98%</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 4. WALLETS TAB */}
        {activeTab === 'wallets' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '16px' }}>Tracked Cryptocurrency Wallets & Extortion Trails</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Blockchain</th>
                  <th>Address</th>
                  <th>Confidence</th>
                  <th>Notes</th>
                  <th>Source</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map(w => (
                  <tr key={w.id}>
                    <td><span className="badge badge-high">{w.blockchain}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                      {w.address}
                    </td>
                    <td><span className="badge badge-high">{Math.round(w.confidence * 100)}%</span></td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{w.notes}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{w.source.name}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => copyToClipboard(w.address, `w_${w.id}`)}>
                        {copiedText === `w_${w.id}` ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 5. POSTS & COMMS TAB */}
        {activeTab === 'posts' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div className="section-label">Observed Darknet Communications & Forum Posts ({filteredPosts.length})</div>
              <div style={{ position: 'relative', width: '280px' }}>
                <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Filter communications..."
                  value={postSearch}
                  onChange={e => setPostSearch(e.target.value)}
                  style={{
                    width: '100%', padding: '6px 12px 6px 32px', background: 'rgba(0,0,0,0.2)',
                    border: '1px solid var(--border-color)', borderRadius: '6px', color: '#fff', fontSize: '0.82rem'
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {filteredPosts.map(p => (
                <div key={p.id} style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.78rem' }}>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <span className="badge badge-info">{p.platform}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-primary)' }}>{p.handle}</span>
                      <span className="badge badge-neutral">{p.category}</span>
                    </div>
                    <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {p.timestamp ? new Date(p.timestamp).toLocaleString() : '—'}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {p.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. PLATFORMS TAB */}
        {activeTab === 'platforms' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            {platforms.map((plat, i) => (
              <div key={i} className="card glass-panel" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                  <Globe size={20} color="var(--accent-primary)" />
                  <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#fff' }}>{plat.platform}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Active Handles:</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)' }}>{plat.handles.join(', ')}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Collected Posts:</span>
                    <span>{plat.post_count} posts</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Reliability:</span>
                    <span>{Math.round(plat.source.reliability * 100)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 7. ONION SERVICES TAB */}
        {activeTab === 'onions' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '16px' }}>Correlated Tor Hidden Services</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Hidden Service Address</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Server Banner</th>
                  <th>TLS Cipher</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {onion_services.map(o => (
                  <tr key={o.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--accent-secondary)' }}>
                      {o.address}
                    </td>
                    <td>{o.title}</td>
                    <td><span className="badge badge-low">{o.status}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{o.server_signature}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{o.tls_cipher}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => copyToClipboard(o.address, `o_${o.id}`)}>
                        {copiedText === `o_${o.id}` ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 8. INFRASTRUCTURE TAB */}
        {activeTab === 'infrastructure' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '16px' }}>Correlated Infrastructure & Network Footprint</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Indicator / Value</th>
                  <th>Correlation</th>
                  <th>Evidence Notes</th>
                </tr>
              </thead>
              <tbody>
                {infrastructure.map((inf, i) => (
                  <tr key={i}>
                    <td><span className="badge badge-info">{inf.type}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)' }}>{inf.value}</td>
                    <td><span className="badge badge-high">{Math.round(inf.correlation_score * 100)}%</span></td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{inf.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 9. BEHAVIOURAL TAB */}
        {activeTab === 'behaviour' && (
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
            <div className="card glass-panel" style={{ padding: '24px' }}>
              <div className="section-label" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BarChart2 size={16} color="var(--accent-primary)" /> 24-Hour Diurnal Activity Distribution (UTC)
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end', height: '180px', gap: '6px', padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
                {behaviour.hourly_distribution.map((cnt, hour) => {
                  const maxCnt = Math.max(...behaviour.hourly_distribution, 1);
                  const hPct = Math.round((cnt / maxCnt) * 100);
                  const isPeak = behaviour.peak_hours.includes(hour);
                  return (
                    <div key={hour} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                      <div
                        title={`Hour ${hour}:00 UTC — ${cnt} posts`}
                        style={{
                          width: '100%', height: `${Math.max(hPct, 6)}%`,
                          background: isPeak ? 'var(--accent-primary)' : 'rgba(255,255,255,0.15)',
                          borderRadius: '3px 3px 0 0', transition: 'height 0.3s'
                        }}
                      />
                      <span style={{ fontSize: '0.65rem', color: isPeak ? 'var(--accent-primary)' : 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                        {hour}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div style={{ marginTop: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Peak Operational Window: <strong style={{ color: 'var(--accent-primary)' }}>{behaviour.peak_hours.map(h => `${h}:00`).join(', ')} UTC</strong>
              </div>
            </div>

            <div className="card glass-panel" style={{ padding: '24px' }}>
              <div className="section-label" style={{ marginBottom: '16px' }}>Behavioral Metrics</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.82rem' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)' }}>Estimated Timezone:</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>{behaviour.active_timezone_estimate}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)' }}>Posting Velocity:</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>{behaviour.posting_frequency}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)' }}>Average Message Length:</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>{behaviour.avg_post_length_words} words ({behaviour.avg_post_length_chars} chars)</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)' }}>Burst Activity Detected:</div>
                  <div style={{ fontWeight: 600, color: behaviour.burst_activity_detected ? '#f59e0b' : '#10b981', marginTop: '2px' }}>
                    {behaviour.burst_activity_detected ? 'YES (Rapid successive communications)' : 'NO'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 10. PERSONA / AI TAB */}
        {activeTab === 'persona_ai' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="card glass-panel" style={{ padding: '20px', background: 'rgba(59, 130, 246, 0.05)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Cpu size={24} color="var(--accent-primary)" />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', color: '#fff' }}>
                    Pretrained AI Model: sentence-transformers/all-MiniLM-L6-v2
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Active 384-dimensional dense semantic embedding pipeline. Calculates real cosine text similarity across forum dumps.
                  </div>
                </div>
              </div>
            </div>

            <div className="section-label">Evaluated Threat Actor Persona Linkages</div>
            {persona_ai.map(p => (
              <div key={p.id} className="card glass-panel" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '1.1rem', fontWeight: 600, color: '#fff' }}>Target: {p.target_actor_name}</span>
                    <span className={`badge ${confidenceBadgeClass(p.confidence_level)}`}>{p.confidence_level} ({p.score}%)</span>
                  </div>
                  <button className="btn btn-primary btn-sm" onClick={() => navigate(`/graph?actorId=${header.id}`)}>
                    Inspect Edge in Graph
                  </button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>SEMANTIC SIMILARITY</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-primary)' }}>{Math.round(p.semantic_similarity * 100)}%</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>STYLOMETRIC NLP</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#10b981' }}>{Math.round(p.stylometric_similarity * 100)}%</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>BEHAVIOURAL HISTOGRAM</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f59e0b' }}>{Math.round(p.behavioural_similarity * 100)}%</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>HANDLE OVERLAP</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#8b5cf6' }}>{Math.round(p.handle_overlap * 100)}%</div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>GRAPH JACCARD</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#ec4899' }}>{Math.round(p.graph_correlation * 100)}%</div>
                  </div>
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {p.explanation}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 11. FORENSIC EVIDENCE TAB */}
        {activeTab === 'evidence' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '16px' }}>Forensic Evidence Ledger</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Identifier / Value</th>
                  <th>Platform</th>
                  <th>Confidence</th>
                  <th>Source Provenance</th>
                  <th>Forensic Notes</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((ev, i) => (
                  <tr key={i}>
                    <td><span className="badge badge-info">{ev.type}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)' }}>{ev.identifier}</td>
                    <td>{ev.platform}</td>
                    <td><span className="badge badge-high">{Math.round(ev.confidence * 100)}%</span></td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{ev.source}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{ev.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 12. ATTRIBUTION TAB */}
        {activeTab === 'attribution' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div className="card glass-panel" style={{ padding: '24px' }}>
              <div className="section-label" style={{ marginBottom: '16px' }}>Attribution Math Breakdown</div>
              <div style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)', marginBottom: '20px', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '6px' }}>
                {attribution.formula}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {Object.entries(attribution.weights).map(([k, v]) => (
                  <div key={k}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                      <span style={{ textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')} ({Math.round(v.weight * 100)}% weight)</span>
                      <strong style={{ fontFamily: 'var(--font-mono)' }}>+{v.points} pts (raw: {v.raw})</strong>
                    </div>
                    <div className="confidence-bar" style={{ height: '6px' }}>
                      <div className="confidence-bar-fill" style={{ width: `${Math.round(v.raw * 100)}%`, background: 'var(--accent-primary)' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card glass-panel" style={{ padding: '24px' }}>
              <div className="section-label" style={{ marginBottom: '16px' }}>Forensic Corroboration & Penalties</div>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--success)', marginBottom: '8px' }}>POSITIVE EVIDENCE:</div>
                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {attribution.positive_evidence.map((pe, i) => <li key={i}>{pe}</li>)}
                </ul>
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ef4444', marginBottom: '8px' }}>NEGATIVE EVIDENCE DEDUCTIONS:</div>
                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {attribution.negative_evidence.map((ne, i) => <li key={i}>{ne}</li>)}
                </ul>
              </div>
              <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Status:</span>
                <span className="badge badge-high">{attribution.analyst_review_status}</span>
              </div>
            </div>
          </div>
        )}

        {/* 13. TIMELINE TAB */}
        {activeTab === 'timeline' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '20px' }}>Chronological Intelligence Timeline</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', position: 'relative', paddingLeft: '20px' }}>
              <div style={{ position: 'absolute', left: '6px', top: '10px', bottom: '10px', width: '2px', background: 'var(--border-color)' }} />
              {timeline.map((ev, i) => (
                <div key={i} style={{ position: 'relative', display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--accent-primary)', position: 'absolute', left: '-20px', top: '4px' }} />
                  <div>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '0.78rem' }}>
                      <span className="badge badge-neutral">{ev.type}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{ev.date ? new Date(ev.date).toLocaleDateString() : '—'}</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{ev.platform}</span>
                    </div>
                    <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', marginTop: '4px' }}>
                      {ev.summary}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 14. RELATIONSHIPS TAB */}
        {activeTab === 'relationships' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '16px' }}>Entity Relationships & Cross-Actor Links</div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Relationship</th>
                  <th>Target Entity</th>
                  <th>Type</th>
                  <th>Confidence</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {relationships.map(r => (
                  <tr key={r.id}>
                    <td><span className="badge badge-info">{r.relationship_type}</span></td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{r.target_name}</td>
                    <td><span className="badge badge-neutral">{r.target_type}</span></td>
                    <td><span className="badge badge-high">{Math.round(r.confidence * 100)}%</span></td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/graph?actorId=${header.id}`)}>
                        <Network size={12} style={{ marginRight: 4 }} /> View in Graph
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 15. COLLECTION HISTORY TAB */}
        {activeTab === 'collection' && (
          <div className="card glass-panel" style={{ padding: '24px' }}>
            <div className="section-label" style={{ marginBottom: '16px' }}>Collection History & Crawler Observations</div>
            {collection_history.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                No direct crawler observations recorded for this actor yet.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Service</th>
                    <th>Collected At</th>
                    <th>Status</th>
                    <th>Content Snippet</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {collection_history.map(c => (
                    <tr key={c.id}>
                      <td style={{ fontWeight: 600 }}>{c.source}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-secondary)' }}>{c.service}</td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{c.collected_at ? new Date(c.collected_at).toLocaleString() : '—'}</td>
                      <td><span className={`badge ${c.status === 'LINKED' ? 'badge-low' : 'badge-high'}`}>{c.status}</span></td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{c.content_snippet}</td>
                      <td><span className="badge badge-high">{Math.round((c.candidate_confidence || 0.8) * 100)}%</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
