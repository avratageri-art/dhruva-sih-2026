import React, { useState, useEffect } from 'react';
import { Server, Globe, Shield, Activity, RefreshCw, Hash, Wifi, AlertTriangle, Search, Zap, Link } from 'lucide-react';
import axios from 'axios';

const API = 'http://localhost:8000';

const statusColor = (status) => {
  if (status === 'ACTIVE') return 'var(--success)';
  if (status === 'OFFLINE') return 'var(--danger)';
  if (status === 'INACTIVE') return 'var(--text-muted)';
  return 'var(--text-muted)';
};

const statusBadge = (status) => {
  if (status === 'ACTIVE') return 'badge-low';
  if (status === 'OFFLINE') return 'badge-critical';
  return 'badge-neutral';
};

const indicatorTypeIcon = (type) => {
  switch (type) {
    case 'IP_ADDRESS': return <Wifi size={13} />;
    case 'HOSTING_ASN': return <Globe size={13} />;
    case 'TLS_CERT_HASH': return <Shield size={13} />;
    case 'SERVER_BANNER': return <Server size={13} />;
    case 'FAVICON_HASH': return <Hash size={13} />;
    default: return <Activity size={13} />;
  }
};

const indicatorTypeBadge = (type) => {
  switch (type) {
    case 'IP_ADDRESS': return 'badge-critical';
    case 'TLS_CERT_HASH': return 'badge-high';
    case 'HOSTING_ASN': return 'badge-medium';
    case 'SERVER_BANNER': return 'badge-info';
    default: return 'badge-neutral';
  }
};

function StatCard({ title, value, icon: Icon, color }) {
  return (
    <div className="glass-card" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="stat-label">{title}</div>
        <Icon size={18} color={color} />
      </div>
      <div className="stat-value" style={{ color, marginTop: '8px' }}>{value ?? '—'}</div>
    </div>
  );
}

// ─── Live SSL Scanner Panel ────────────────────────────────────────────────
function SSLScannerPanel() {
  const [host, setHost] = useState('');
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [fingerprints, setFingerprints] = useState(null);
  const [fpLoading, setFpLoading] = useState(false);
  const [recommendedTargets, setRecommendedTargets] = useState([]);

  useEffect(() => {
    // Load recommended scan targets
    axios.get(`${API}/api/infra/scan-targets`)
      .then(r => setRecommendedTargets(r.data.targets || []))
      .catch(() => {});
    // Load existing fingerprints
    fetchFingerprints();
  }, []);

  const fetchFingerprints = () => {
    setFpLoading(true);
    axios.get(`${API}/api/infra/fingerprints`)
      .then(r => setFingerprints(r.data))
      .catch(() => {})
      .finally(() => setFpLoading(false));
  };

  const runScan = async (targetHost) => {
    const h = (targetHost || host).trim();
    if (!h) return;
    setScanning(true);
    setResult(null);
    setError(null);
    try {
      const resp = await axios.post(`${API}/api/infra/scan`, { host: h, port: 443 });
      setResult(resp.data);
      fetchFingerprints(); // refresh fingerprint registry
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Scanner Input */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '14px' }}>
          <Shield size={18} color="var(--accent-primary)" />
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Live SSL/TLS Certificate Inspector</h3>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', margin: '0 0 14px 0' }}>
          Performs real-time SSL cert inspection + HTTP banner grabbing. Detects shared infrastructure by fingerprinting TLS certs across actor domains.
        </p>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            className="form-input"
            type="text"
            placeholder="Enter hostname (e.g. google.com, cloudflare.com)"
            value={host}
            onChange={e => setHost(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && runScan()}
            style={{ flex: 1 }}
          />
          <button
            className="btn btn-primary"
            onClick={() => runScan()}
            disabled={scanning || !host.trim()}
            style={{ display: 'flex', gap: '8px', alignItems: 'center', minWidth: '120px' }}
          >
            {scanning ? <><RefreshCw size={14} className="spin" /> Scanning...</> : <><Zap size={14} /> Scan Host</>}
          </button>
        </div>

        {/* Quick targets */}
        {recommendedTargets.length > 0 && (
          <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Quick scan:</span>
            {recommendedTargets.slice(0, 5).map(t => (
              <button
                key={t.host}
                onClick={() => { setHost(t.host); runScan(t.host); }}
                style={{
                  background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                  borderRadius: '4px', padding: '3px 10px', fontSize: '0.75rem',
                  color: 'var(--accent-primary)', cursor: 'pointer'
                }}
              >
                {t.host}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Scan Result */}
      {error && (
        <div className="glass-card" style={{ padding: '16px', borderLeft: '3px solid var(--danger)' }}>
          <span style={{ color: 'var(--danger)' }}><AlertTriangle size={14} style={{ marginRight: 8 }} />Scan Error: {error}</span>
        </div>
      )}

      {result && (
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem' }}>{result.host}</h3>
              <span className={`badge ${result.reachable ? 'badge-low' : 'badge-critical'}`} style={{ marginTop: '4px', display: 'inline-block' }}>
                {result.reachable ? 'REACHABLE' : 'UNREACHABLE'}
              </span>
              {result.infrastructure_overlap && (
                <span className="badge badge-critical" style={{ marginLeft: '6px' }}>
                  <Link size={10} style={{ marginRight: 4 }} />SHARED INFRA DETECTED
                </span>
              )}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {result.scanned_at ? new Date(result.scanned_at).toLocaleTimeString() : ''}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* SSL Info */}
            {result.ssl && !result.ssl.error && (
              <div style={{ background: 'var(--bg-secondary)', borderRadius: '8px', padding: '14px' }}>
                <div style={{ fontWeight: 600, marginBottom: '10px', fontSize: '0.85rem', color: 'var(--accent-primary)' }}>
                  <Shield size={13} style={{ marginRight: 6 }} />SSL/TLS Certificate
                </div>
                {[
                  ['Subject CN', result.ssl.subject_cn],
                  ['Issuer', result.ssl.issuer_org || result.ssl.issuer_cn],
                  ['Protocol', result.ssl.protocol],
                  ['Valid From', result.ssl.valid_from],
                  ['Valid To', result.ssl.valid_to],
                  ['SHA-256 FP', result.ssl.fingerprint_sha256 ? result.ssl.fingerprint_sha256.slice(0, 32) + '...' : null],
                ].filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '5px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                    <span className="mono" style={{ color: 'var(--text-primary)', textAlign: 'right', maxWidth: '55%', overflow: 'hidden', textOverflow: 'ellipsis' }}>{v}</span>
                  </div>
                ))}
                {(result.ssl.san_domains || []).length > 0 && (
                  <div style={{ marginTop: '8px', fontSize: '0.76rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>SANs: </span>
                    {result.ssl.san_domains.slice(0, 5).join(', ')}
                    {result.ssl.san_domains.length > 5 && <span style={{ color: 'var(--text-muted)' }}> +{result.ssl.san_domains.length - 5} more</span>}
                  </div>
                )}
              </div>
            )}

            {/* Banner Info */}
            {result.banner && !result.banner.error && (
              <div style={{ background: 'var(--bg-secondary)', borderRadius: '8px', padding: '14px' }}>
                <div style={{ fontWeight: 600, marginBottom: '10px', fontSize: '0.85rem', color: 'var(--warning)' }}>
                  <Server size={13} style={{ marginRight: 6 }} />HTTP Banner
                </div>
                {[
                  ['Status', result.banner.status_code],
                  ['Server', result.banner.server],
                  ['X-Powered-By', result.banner.x_powered_by],
                  ['Content-Type', result.banner.content_type?.split(';')[0]],
                  ['Page Title', result.banner.title],
                ].filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '5px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                    <span className="mono" style={{ color: 'var(--text-primary)', textAlign: 'right', maxWidth: '55%', overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Indicators */}
          {result.indicators?.length > 0 && (
            <div style={{ marginTop: '14px' }}>
              <div style={{ fontWeight: 600, fontSize: '0.82rem', marginBottom: '8px', color: 'var(--text-secondary)' }}>Extracted Indicators</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {result.indicators.map((ind, i) => (
                  <span key={i} className={`badge ${indicatorTypeBadge(ind.type)}`} title={ind.value}>
                    {indicatorTypeIcon(ind.type)} {ind.type}: {ind.value.length > 30 ? ind.value.slice(0, 30) + '...' : ind.value}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Shared infrastructure warning */}
          {result.shared_with?.length > 0 && (
            <div style={{ marginTop: '14px', background: 'rgba(220,53,69,0.1)', border: '1px solid var(--danger)', borderRadius: '8px', padding: '12px' }}>
              <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: '6px', fontSize: '0.85rem' }}>
                <AlertTriangle size={13} style={{ marginRight: 6 }} />Shared Infrastructure Detected
              </div>
              {result.shared_with.map((s, i) => (
                <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Actor {s.actor_name} (ID #{s.actor_id}) shares {s.shared_via} — Confidence: {Math.round(s.confidence * 100)}%
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Fingerprint Registry */}
      {fingerprints && fingerprints.total_fingerprints > 0 && (
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Hash size={16} color="var(--warning)" /> Fingerprint Registry
            </h3>
            <span className="badge badge-info">{fingerprints.total_fingerprints} fingerprint(s) | {fingerprints.shared_fingerprints} shared</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {(fingerprints.fingerprints || []).map((fp, i) => (
              <div key={i} style={{
                background: fp.is_shared ? 'rgba(220,53,69,0.07)' : 'var(--bg-secondary)',
                border: `1px solid ${fp.is_shared ? 'var(--danger)' : 'var(--border)'}`,
                borderRadius: '6px', padding: '10px 14px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center'
              }}>
                <div>
                  <span className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{fp.fingerprint.slice(0, 32)}...</span>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '3px' }}>
                    Hosts: {fp.hosts.join(', ')}
                  </div>
                </div>
                <span className={`badge ${fp.is_shared ? 'badge-critical' : 'badge-neutral'}`}>
                  {fp.is_shared ? '⚠ SHARED' : 'UNIQUE'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Infrastructure() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('scanner');
  const [search, setSearch] = useState('');

  const fetchData = () => {
    setLoading(true);
    axios.get(`${API}/api/analysis/infrastructure`)
      .then(r => { setData(r.data); setLoading(false); })
      .catch((err) => {
        console.error("Failed to fetch infrastructure", err);
        setData({
          stats: { total_services: 0, active_services: 0, total_indicators: 0, total_domains: 0 },
          onion_services: [],
          indicators: [],
          domains: [],
        });
        setLoading(false);
      });
  };

  useEffect(() => { fetchData(); }, []);

  const filteredServices = (data?.onion_services || []).filter(s =>
    !search || s.title?.toLowerCase().includes(search.toLowerCase()) || s.address?.includes(search)
  );
  const filteredIndicators = (data?.indicators || []).filter(i =>
    !search || i.value?.toLowerCase().includes(search.toLowerCase()) || i.type?.includes(search.toUpperCase())
  );

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' }}>
        <div>
          <h1 style={{ margin: 0 }}>Infrastructure Intelligence</h1>
          <p style={{ color: 'var(--text-secondary)', margin: '6px 0 0 0' }}>
            Real-time SSL fingerprinting, onion services, and actor infrastructure correlation.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={fetchData} style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4" style={{ marginBottom: '24px' }}>
        <StatCard title="Onion Services" value={data?.stats?.total_services} icon={Globe} color="var(--accent-primary)" />
        <StatCard title="Active Services" value={data?.stats?.active_services} icon={Activity} color="var(--success)" />
        <StatCard title="Indicators" value={data?.stats?.total_indicators} icon={Shield} color="var(--warning)" />
        <StatCard title="Domains Tracked" value={data?.stats?.total_domains} icon={Server} color="var(--text-primary)" />
      </div>

      {/* Tabs */}
      <div className="glass-card" style={{ padding: '12px 20px', marginBottom: '20px', display: 'flex', gap: '16px', alignItems: 'center' }}>
        {activeTab !== 'scanner' && (
          <input
            className="form-input"
            type="text"
            placeholder="Search..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ maxWidth: '300px' }}
          />
        )}
        <div className="tabs" style={{ margin: 0, border: 'none' }}>
          {[
            ['scanner', '🔍 Live SSL Scanner'],
            ['services', 'Onion Services'],
            ['indicators', 'Indicators'],
            ['domains', 'Domains'],
          ].map(([key, label]) => (
            <button key={key} className={`tab ${activeTab === key ? 'active' : ''}`} onClick={() => setActiveTab(key)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Scanner Tab */}
      {activeTab === 'scanner' && <SSLScannerPanel />}

      {/* Onion Services Tab */}
      {activeTab === 'services' && !loading && (
        <div className="card" style={{ overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Status</th><th>Service</th><th>Onion Address</th><th>Type</th><th>First Seen</th><th>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {filteredServices.length === 0 ? (
                <tr><td colSpan={6} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No services found</td></tr>
              ) : filteredServices.map(s => (
                <tr key={s.id}>
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor(s.status), boxShadow: s.status === 'ACTIVE' ? `0 0 6px ${statusColor(s.status)}` : 'none' }} />
                      <span className={`badge ${statusBadge(s.status)}`}>{s.status}</span>
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.title}</div>
                    {s.metadata?.type && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{s.metadata.type.replace('_', ' ')}</span>}
                  </td>
                  <td style={{ padding: '14px 16px' }}><span className="mono" style={{ fontSize: '0.72rem' }}>{s.address?.slice(0, 24)}...</span></td>
                  <td style={{ padding: '14px 16px' }}>
                    {s.metadata?.listings && <span className="badge badge-info">{s.metadata.listings.toLocaleString()} listings</span>}
                    {s.metadata?.members && <span className="badge badge-info">{s.metadata.members.toLocaleString()} members</span>}
                    {!s.metadata?.listings && !s.metadata?.members && <span className="badge badge-neutral">—</span>}
                  </td>
                  <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{s.first_seen ? new Date(s.first_seen).toLocaleDateString() : '—'}</td>
                  <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{s.last_seen ? new Date(s.last_seen).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Indicators Tab */}
      {activeTab === 'indicators' && !loading && (
        <div className="card" style={{ overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr><th>Type</th><th>Value</th><th>Confidence</th><th>Linked Service</th><th>Observed</th></tr>
            </thead>
            <tbody>
              {filteredIndicators.length === 0 ? (
                <tr><td colSpan={5} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No indicators found</td></tr>
              ) : filteredIndicators.map(i => (
                <tr key={i.id}>
                  <td style={{ padding: '14px 16px' }}>
                    <span className={`badge ${indicatorTypeBadge(i.type)}`} style={{ display: 'flex', gap: '5px', alignItems: 'center', width: 'fit-content' }}>
                      {indicatorTypeIcon(i.type)} {i.type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px' }}><span className="mono">{i.value?.length > 40 ? i.value.slice(0, 40) + '...' : i.value}</span></td>
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '140px' }}>
                      <div className="confidence-bar" style={{ flex: 1 }}>
                        <div className="confidence-bar-fill" style={{ width: `${Math.round((i.confidence || 0) * 100)}%`, background: i.confidence >= 0.85 ? 'var(--danger)' : i.confidence >= 0.7 ? 'var(--warning)' : 'var(--accent-primary)' }} />
                      </div>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{Math.round((i.confidence || 0) * 100)}%</span>
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>#{i.service_id || '—'}</td>
                  <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{i.observed_at ? new Date(i.observed_at).toLocaleDateString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Domains Tab */}
      {activeTab === 'domains' && !loading && (
        <div className="card" style={{ overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr><th>Domain</th><th>Linked Actor</th></tr>
            </thead>
            <tbody>
              {(data?.domains || []).filter(d => !search || d.domain?.includes(search)).length === 0 ? (
                <tr><td colSpan={2} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No domains found</td></tr>
              ) : (data?.domains || []).filter(d => !search || d.domain?.includes(search)).map(d => (
                <tr key={d.id}>
                  <td style={{ padding: '14px 16px' }}><span className="mono">{d.domain}</span></td>
                  <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Actor #{d.actor_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && activeTab !== 'scanner' && (
        <div className="glass-card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading infrastructure data...</div>
      )}
    </div>
  );
}
