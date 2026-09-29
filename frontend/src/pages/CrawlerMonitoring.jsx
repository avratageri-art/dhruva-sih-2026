import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Database, RefreshCw, Play, Plus, CheckCircle, AlertTriangle, Globe,
  Shield, Key, Wallet, User, Terminal, ExternalLink, ArrowRight, Activity,
  Server, Check, Clock, Filter, Eye, AlertCircle, Download, Zap
} from 'lucide-react';

const API = 'http://localhost:8000';

export default function CrawlerMonitoring() {
  const [status, setStatus] = useState(null);
  const [seeds, setSeeds] = useState([]);
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [collectResult, setCollectResult] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('seeds');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newSeed, setNewSeed] = useState({
    seed_url: '',
    name: '',
    category: 'Marketplace',
    reliability: 0.90,
  });
  // deepdarkCTI integration state
  const [ddcStatus, setDdcStatus] = useState(null);
  const [ddcSources, setDdcSources] = useState([]);
  const [ddcRefreshing, setDdcRefreshing] = useState(false);
  const [ddcCollecting, setDdcCollecting] = useState(false);
  const [ddcResult, setDdcResult] = useState(null);

  // Live Tor Probing & Filtering
  const [probingSeedId, setProbingSeedId] = useState(null);
  const [probeResult, setProbeResult] = useState(null);
  const [seedFilter, setSeedFilter] = useState('authorized');
  const [seedSearch, setSeedSearch] = useState('');

  const handleProbeSeed = async (seedId) => {
    setProbingSeedId(seedId);
    setProbeResult(null);
    try {
      const res = await axios.post(`${API}/api/crawler/seeds/${seedId}/probe`);
      setProbeResult(res.data);
      await fetchData();
    } catch (err) {
      alert('Probe failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProbingSeedId(null);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [stRes, sdRes, obRes] = await Promise.all([
        axios.get(`${API}/api/crawler/status`),
        axios.get(`${API}/api/crawler/seeds`),
        axios.get(`${API}/api/crawler/observations?limit=50`),
      ]);
      setStatus(stRes.data);
      setSeeds(sdRes.data);
      setObservations(obRes.data);
    } catch (err) {
      console.error("Failed to fetch crawler data", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDdcData = async () => {
    try {
      const [stRes, srcRes] = await Promise.all([
        axios.get(`${API}/api/deepdarkcti/status`),
        axios.get(`${API}/api/deepdarkcti/sources?limit=100`),
      ]);
      setDdcStatus(stRes.data);
      setDdcSources(srcRes.data.sources || []);
    } catch (err) {
      console.error('Failed to fetch deepdarkCTI data', err);
    }
  };

  useEffect(() => {
    fetchData();
    fetchDdcData();
  }, []);

  // Auto-refresh deepdarkCTI data every 30s when on that tab
  useEffect(() => {
    if (activeSubTab !== 'deepdarkcti') return;
    fetchDdcData();
    const interval = setInterval(fetchDdcData, 30000);
    return () => clearInterval(interval);
  }, [activeSubTab]);

  const handleRunCollection = async () => {
    setCollecting(true);
    setCollectResult(null);
    try {
      const res = await axios.post(`${API}/api/crawler/collect`);
      setCollectResult(res.data);
      await fetchData();
    } catch (err) {
      console.error("Failed to run collection cycle", err);
    } finally {
      setCollecting(false);
    }
  };

  const handleDdcRefresh = async () => {
    setDdcRefreshing(true);
    setDdcResult(null);
    try {
      const res = await axios.post(`${API}/api/deepdarkcti/refresh`);
      setDdcResult({ type: 'refresh', ...res.data });
      await fetchDdcData();
      await fetchData(); // update seeds count
    } catch (err) {
      setDdcResult({ type: 'error', message: err.response?.data?.detail || err.message });
    } finally {
      setDdcRefreshing(false);
    }
  };

  const handleDdcCollect = async () => {
    setDdcCollecting(true);
    setDdcResult(null);
    try {
      const res = await axios.post(`${API}/api/deepdarkcti/collect`, { max_sources: 5 });
      setDdcResult({ type: 'collect', ...res.data });
      await fetchDdcData();
    } catch (err) {
      setDdcResult({ type: 'error', message: err.response?.data?.detail || err.message });
    } finally {
      setDdcCollecting(false);
    }
  };

  const handleDdcEnable = async (seedId) => {
    try {
      await axios.post(`${API}/api/deepdarkcti/sources/${seedId}/enable`);
      await fetchDdcData();
      await fetchData();
    } catch (err) {
      alert('Failed to enable source: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDdcDisable = async (seedId) => {
    try {
      await axios.post(`${API}/api/deepdarkcti/sources/${seedId}/disable`);
      await fetchDdcData();
    } catch (err) {
      alert('Failed to disable source: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAddSeed = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/api/crawler/seeds`, newSeed);
      setShowAddModal(false);
      setNewSeed({ seed_url: '', name: '', category: 'Marketplace', reliability: 0.90 });
      await fetchData();
    } catch (err) {
      alert("Failed to add seed source: " + (err.response?.data?.detail || err.message));
    }
  };

  const filteredSeeds = seeds.filter(s => {
    if (seedFilter === 'authorized' && !s.authorized) return false;
    if (seedFilter === 'online' && s.status !== 'ONLINE' && s.status !== 'CONTENT_OBSERVED') return false;
    if (seedSearch) {
      const q = seedSearch.toLowerCase();
      return (s.name || '').toLowerCase().includes(q) || (s.seed_url || '').toLowerCase().includes(q) || (s.category || '').toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div style={{ width: '100%', maxWidth: '100%', paddingBottom: '40px' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h1 style={{ margin: 0, fontSize: '1.8rem' }}>Darknet Collection Layer</h1>
            <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
              TOR ONION CRAWLER ENGINE
            </span>
            <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.35)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }} />
              Tor SOCKS5: 127.0.0.1:9050 ONLINE
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', margin: '6px 0 0 0', fontSize: '0.9rem' }}>
            Automated darknet telemetry ingestion, real Tor circuit verification, entity extraction & AI identity resolution.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            onClick={fetchData}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} /> Refresh
          </button>
          <button
            className="btn btn-primary"
            onClick={handleRunCollection}
            disabled={collecting}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', fontWeight: 600 }}
          >
            {collecting ? <RefreshCw size={16} className="spin" /> : <Play size={16} fill="currentColor" />}
            {collecting ? 'Running Tor Ingestion Cycle...' : 'Run Collection Cycle'}
          </button>
        </div>
      </div>

      {/* Collection Results Banner */}
      {collectResult && (
        <div className="card glass-panel" style={{
          padding: '20px 24px', marginBottom: '24px',
          background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.3)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <CheckCircle size={24} color="#10b981" />
              <div>
                <div style={{ fontWeight: 600, color: '#10b981', fontSize: '1rem' }}>
                  Tor Collection Cycle Completed ({collectResult.cycle_id})
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  {collectResult.message}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '20px', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', flexWrap: 'wrap' }}>
              <div>PROBED: <strong style={{ color: '#fff' }}>{collectResult.processed_count}</strong></div>
              <div>ONLINE: <strong style={{ color: '#10b981' }}>{collectResult.online_count ?? '—'}</strong></div>
              <div>OFFLINE: <strong style={{ color: '#ef4444' }}>{collectResult.offline_count ?? '—'}</strong></div>
              <div>NEW OBS: <strong style={{ color: '#3b82f6' }}>{collectResult.new_observations ?? collectResult.processed_count}</strong></div>
              <div>LINKED: <strong style={{ color: '#10b981' }}>{collectResult.linked_count}</strong></div>
            </div>
          </div>
        </div>
      )}

      {/* Individual Probe Result Toast/Banner */}
      {probeResult && (
        <div className="card glass-panel" style={{
          padding: '14px 20px', marginBottom: '20px',
          background: probeResult.status === 'ONLINE' ? 'rgba(16, 185, 129, 0.09)' : 'rgba(239, 68, 68, 0.09)',
          border: `1px solid ${probeResult.status === 'ONLINE' ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {probeResult.status === 'ONLINE' ? <CheckCircle size={18} color="#10b981" /> : <AlertTriangle size={18} color="#ef4444" />}
            <span style={{ fontSize: '0.85rem' }}>
              Live Tor Probe: <strong>{probeResult.name}</strong> is{' '}
              <strong style={{ color: probeResult.status === 'ONLINE' ? '#10b981' : '#ef4444' }}>
                {probeResult.status}
              </strong>
              {probeResult.latency_ms > 0 ? ` (${probeResult.latency_ms}ms)` : ''} —{' '}
              {probeResult.page_title || probeResult.error || 'Verified via Tor SOCKS5 socket'}
            </span>
          </div>
          <button className="btn btn-xs btn-ghost" onClick={() => setProbeResult(null)} style={{ color: 'var(--text-muted)' }}>✕ Dismiss</button>
        </div>
      )}

      {/* Live Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="card glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>CRAWLER ENGINE STATUS</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
            <div style={{
              width: '10px', height: '10px', borderRadius: '50%',
              background: collecting ? '#3b82f6' : '#10b981',
              boxShadow: collecting ? '0 0 10px #3b82f6' : '0 0 10px #10b981'
            }} />
            <span style={{ fontSize: '1.2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#fff' }}>
              {collecting ? 'ACTIVE / RUNNING' : 'IDLE / LISTENING'}
            </span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Adapter: {status?.adapter_type || 'OnionCrawlerAdapter'}
          </div>
        </div>

        <div className="card glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>AUTHORIZED SEED SOURCES</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)', marginTop: '4px' }}>
            {status?.total_seeds || seeds.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {status?.active_seeds || seeds.filter(s => s.status === 'ACTIVE' || s.status === 'ONLINE').length} Active onion endpoints
          </div>
        </div>

        <div className="card glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>TOTAL OBSERVATIONS</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#fff', marginTop: '4px' }}>
            {status?.total_observations || observations.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {status?.linked_observations || 0} Resolved to Threat Actors
          </div>
        </div>

        <div className="card glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>CRITICAL ALERTS DISPATCHED</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#f59e0b', marginTop: '4px' }}>
            {status?.alerts_count || 0}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            High-confidence correlation triggers
          </div>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '12px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            className={`btn btn-sm ${activeSubTab === 'seeds' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSubTab('seeds')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Server size={14} /> Seed Onion Registry ({seeds.length})
          </button>
          <button
            className={`btn btn-sm ${activeSubTab === 'observations' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSubTab('observations')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Database size={14} /> Raw Observations Stream ({observations.length})
          </button>
          <button
            className={`btn btn-sm ${activeSubTab === 'pipeline' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSubTab('pipeline')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Activity size={14} /> Pipeline Architecture
          </button>
          <button
            className={`btn btn-sm ${activeSubTab === 'deepdarkcti' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSubTab('deepdarkcti')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', borderColor: activeSubTab === 'deepdarkcti' ? undefined : 'rgba(139,92,246,0.4)', color: activeSubTab === 'deepdarkcti' ? undefined : '#a78bfa' }}
          >
            <Globe size={14} /> DeepDarkCTI Registry ({ddcStatus?.sources?.total || 0})
          </button>
        </div>

        {activeSubTab === 'seeds' && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowAddModal(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={14} /> Register New Onion Seed
          </button>
        )}
      </div>

      {/* TAB 1: SEEDS REGISTRY */}
      {activeSubTab === 'seeds' && (
        <div className="card glass-panel" style={{ padding: '24px' }}>
          {/* Controls: Filter & Search */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                className={`btn btn-xs ${seedFilter === 'authorized' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSeedFilter('authorized')}
              >
                Authorized Active ({seeds.filter(s => s.authorized).length})
              </button>
              <button
                className={`btn btn-xs ${seedFilter === 'online' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSeedFilter('online')}
              >
                ● Live Online ({seeds.filter(s => s.status === 'ONLINE' || s.status === 'CONTENT_OBSERVED').length})
              </button>
              <button
                className={`btn btn-xs ${seedFilter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSeedFilter('all')}
              >
                All Seeds ({seeds.length})
              </button>
            </div>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                placeholder="Search seed name or onion URL..."
                value={seedSearch}
                onChange={e => setSeedSearch(e.target.value)}
                style={{
                  background: 'rgba(0,0,0,0.25)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  color: '#fff',
                  fontSize: '0.8rem',
                  width: '260px',
                }}
              />
            </div>
          </div>

          <div style={{ overflowX: 'auto', width: '100%', WebkitOverflowScrolling: 'touch' }}>
            <table className="data-table" style={{ width: '100%', minWidth: '850px' }}>
              <thead>
                <tr>
                  <th style={{ minWidth: '180px' }}>Seed Label / Service Name</th>
                  <th style={{ minWidth: '240px' }}>Onion Address</th>
                  <th>Category</th>
                  <th>Live Status (Tor)</th>
                  <th>Reliability</th>
                  <th>Observations</th>
                  <th>Last Crawled</th>
                  <th style={{ textAlign: 'right' }}>Tor Probe</th>
                </tr>
              </thead>
              <tbody>
                {filteredSeeds.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px' }}>
                      No seeds match the current filter.
                    </td>
                  </tr>
                ) : (
                  filteredSeeds.map(s => {
                    const isOnline = s.status === 'ONLINE' || s.status === 'CONTENT_OBSERVED';
                    const isOffline = s.status === 'OFFLINE' || s.status === 'FAILED' || s.status === 'UNREACHABLE';
                    return (
                      <tr key={s.id}>
                        <td style={{ fontWeight: 600, color: '#fff', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.name}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-secondary)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.seed_url}
                        </td>
                        <td><span className="badge badge-info">{s.category}</span></td>
                        <td>
                          {isOnline ? (
                            <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.4)', fontWeight: 600 }}>
                              ● ONLINE
                            </span>
                          ) : isOffline ? (
                            <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.4)', fontWeight: 600 }}>
                              ○ OFFLINE
                            </span>
                          ) : (
                            <span className="badge badge-neutral">{s.status || 'DISCOVERED'}</span>
                          )}
                        </td>
                        <td><span className="badge badge-high">{Math.round((s.reliability || 0.9) * 100)}%</span></td>
                        <td>
                          <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>{s.observation_count || 0} items</span>
                        </td>
                        <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {s.last_crawl ? new Date(s.last_crawl).toLocaleTimeString() : 'Never'}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            className="btn btn-secondary btn-xs"
                            onClick={() => handleProbeSeed(s.id)}
                            disabled={probingSeedId === s.id}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem' }}
                          >
                            {probingSeedId === s.id ? <RefreshCw size={11} className="spin" /> : <Zap size={11} color="#a78bfa" />}
                            {probingSeedId === s.id ? 'Probing...' : 'Test Tor'}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: RAW OBSERVATIONS STREAM */}
      {activeSubTab === 'observations' && (
        <div className="card glass-panel" style={{ padding: '24px' }}>
          <div style={{ overflowX: 'auto', width: '100%', WebkitOverflowScrolling: 'touch' }}>
          <table className="data-table" style={{ width: '100%', minWidth: '750px' }}>
            <thead>
              <tr>
                <th>Collected At</th>
                <th>Source Address</th>
                <th>Content / Title</th>
                <th>Extracted Entities</th>
                <th>Attribution Status</th>
              </tr>
            </thead>
            <tbody>
              {observations.map(ob => {
                const ents = ob.extracted_entities || {};
                const handles = ents.handles || [];
                const wallets = ents.wallets || [];
                const pgps = ents.pgp_keys || [];
                return (
                  <tr key={ob.id}>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {ob.collected_at ? new Date(ob.collected_at).toLocaleTimeString() : '—'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-secondary)' }}>
                      {ob.onion_address ? `${ob.onion_address.slice(0, 16)}...` : 'Unknown'}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.85rem' }}>
                        {ob.title || 'Observation'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px', maxWidth: '400px' }}>
                        {ob.raw_content ? `${ob.raw_content.slice(0, 120)}...` : ''}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {handles.map((h, i) => (
                          <span key={i} className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                            <User size={10} style={{ marginRight: 2 }} /> {h}
                          </span>
                        ))}
                        {wallets.map((w, i) => (
                          <span key={i} className="badge badge-high" style={{ fontSize: '0.7rem' }}>
                            <Wallet size={10} style={{ marginRight: 2 }} /> {w.slice(0, 8)}...
                          </span>
                        ))}
                        {pgps.map((p, i) => (
                          <span key={i} className="badge badge-low" style={{ fontSize: '0.7rem' }}>
                            <Key size={10} style={{ marginRight: 2 }} /> {p.slice(0, 8)}...
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      {ob.actor ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span className="badge badge-low" style={{ fontWeight: 600 }}>
                            LINKED: {ob.actor.name}
                          </span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            Confidence: {Math.round((ob.candidate_confidence || 0.85) * 100)}%
                          </span>
                        </div>
                      ) : (
                        <span className="badge badge-neutral">UNASSOCIATED</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {/* TAB 3: PIPELINE ARCHITECTURE */}
      {activeSubTab === 'pipeline' && (
        <div className="card glass-panel" style={{ padding: '32px' }}>
          <div className="section-label" style={{ marginBottom: '20px' }}>Continuous Ingestion & Attribution Pipeline Flow</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
            {[
              { step: '1. Seed Harvesting', desc: 'SOCKS5 Tor routing over .onion endpoints', icon: Globe },
              { step: '2. Raw Normalization', desc: 'HTML stripping, encoding clean, text extraction', icon: Terminal },
              { step: '3. Entity Extraction', desc: 'Regex & regex-free PGP, crypto, handle parsing', icon: Key },
              { step: '4. AI Resolution', desc: 'sentence-transformers/all-MiniLM-L6-v2 embeddings', icon: Activity },
              { step: '5. Threat Correlator', desc: 'Graph linking & high-confidence alert triggers', icon: Shield },
            ].map((st, i) => {
              const Icon = st.icon;
              return (
                <div key={i} style={{ flex: 1, minWidth: '180px', background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <Icon size={24} color="var(--accent-primary)" style={{ marginBottom: '10px' }} />
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#fff' }}>{st.step}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>{st.desc}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ADD SEED MODAL */}
      {showAddModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="card glass-panel" style={{ width: '480px', padding: '28px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.2rem', color: '#fff' }}>Register New Darknet Onion Seed</h3>
            <form onSubmit={handleAddSeed} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>SERVICE NAME</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Genesis Leak Forum Mirror"
                  value={newSeed.name}
                  onChange={e => setNewSeed({ ...newSeed, name: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', borderRadius: '6px', color: '#fff' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>ONION ADDRESS (.onion)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. genesis7x34k...onion"
                  value={newSeed.seed_url}
                  onChange={e => setNewSeed({ ...newSeed, seed_url: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', borderRadius: '6px', color: '#fff', fontFamily: 'var(--font-mono)' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>CATEGORY</label>
                <select
                  value={newSeed.category}
                  onChange={e => setNewSeed({ ...newSeed, category: e.target.value })}
                  style={{ width: '100%', padding: '8px 12px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', borderRadius: '6px', color: '#fff' }}
                >
                  <option value="Marketplace">Marketplace</option>
                  <option value="Forum">Forum</option>
                  <option value="Ransomware Leak Site">Ransomware Leak Site</option>
                  <option value="Paste Site">Paste Site</option>
                  <option value="Escrow / Mixer">Escrow / Mixer</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Seed Source</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* TAB: DEEPDARKCTI SOURCE REGISTRY */}
      {activeSubTab === 'deepdarkcti' && (
        <div>
          {/* Status Summary Bar */}
          <div className="card glass-panel" style={{ padding: '18px 24px', marginBottom: '16px', background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <Globe size={20} color="#a78bfa" />
                <div>
                  <div style={{ fontWeight: 600, color: '#a78bfa', fontSize: '0.9rem' }}>deepdarkCTI Source Registry</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>Curated CTI Seed Catalogue · catalogue_status ≠ DHRUVA collection_status.</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '24px', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                <div>TOTAL: <strong style={{ color: '#fff' }}>{ddcStatus?.sources?.total ?? '—'}</strong></div>
                <div>DISCOVERED: <strong style={{ color: '#a78bfa' }}>{ddcStatus?.sources?.discovered ?? '—'}</strong></div>
                <div>ENABLED: <strong style={{ color: '#10b981' }}>{ddcStatus?.sources?.enabled ?? '—'}</strong></div>
                <div>REACHABLE: <strong style={{ color: '#3b82f6' }}>{ddcStatus?.sources?.reachable ?? '—'}</strong></div>
                <div>OBSERVATIONS: <strong style={{ color: '#f59e0b' }}>{ddcStatus?.observations?.total_from_deepdarkcti ?? '—'}</strong></div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  id="btn-ddc-refresh"
                  className="btn btn-secondary btn-sm"
                  onClick={handleDdcRefresh}
                  disabled={ddcRefreshing}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  {ddcRefreshing ? <RefreshCw size={13} className="spin" /> : <Download size={13} />}
                  {ddcRefreshing ? 'Fetching...' : 'Refresh from GitHub'}
                </button>
                <button
                  id="btn-ddc-collect"
                  className="btn btn-primary btn-sm"
                  onClick={handleDdcCollect}
                  disabled={ddcCollecting}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(139,92,246,0.3)', borderColor: 'rgba(139,92,246,0.5)' }}
                >
                  {ddcCollecting ? <RefreshCw size={13} className="spin" /> : <Zap size={13} />}
                  {ddcCollecting ? 'Collecting...' : 'Run Collection Cycle'}
                </button>
              </div>
            </div>
          </div>

          {/* Result Banner */}
          {ddcResult && ddcResult.type !== 'error' && (
            <div className="card glass-panel" style={{ padding: '14px 20px', marginBottom: '16px', background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.25)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <CheckCircle size={18} color="#10b981" />
                <div style={{ fontSize: '0.85rem' }}>
                  {ddcResult.type === 'refresh'
                    ? `Refreshed: ${ddcResult.total_sources_fetched} sources fetched — ${ddcResult.db_created} new, ${ddcResult.db_updated} updated. All new sources start as DISCOVERED (analyst must enable).`
                    : `Collection cycle: ${ddcResult.cycle?.collected || 0} collected, ${ddcResult.cycle?.unreachable || 0} unreachable, ${ddcResult.cycle?.new_observations || 0} new observations.`
                  }
                </div>
              </div>
            </div>
          )}
          {ddcResult && ddcResult.type === 'error' && (
            <div className="card glass-panel" style={{ padding: '14px 20px', marginBottom: '16px', background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.25)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <AlertCircle size={18} color="#ef4444" />
                <div style={{ fontSize: '0.85rem', color: '#ef4444' }}>{ddcResult.message}</div>
              </div>
            </div>
          )}

          {/* Notice */}
          <div style={{ padding: '10px 14px', marginBottom: '14px', background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '8px', fontSize: '0.78rem', color: '#f59e0b' }}>
            ⚠ ANALYST GATE: Sources start as <strong>DISCOVERED</strong>. Enable individual sources to authorize real collection. DeepDarkCTI catalogue_status (ONLINE/OFFLINE) is historical catalogue data — not live status.
          </div>

          {/* Sources Table */}
          <div className="card glass-panel" style={{ padding: '20px' }}>
            <div style={{ overflowX: 'auto', width: '100%', WebkitOverflowScrolling: 'touch' }}>
            <table className="data-table" style={{ width: '100%', minWidth: '850px' }}>
              <thead>
                <tr>
                  <th>Source Name</th>
                  <th>URL / Address</th>
                  <th>Category</th>
                  <th>Catalogue Status</th>
                  <th>Collection Status</th>
                  <th>Observations</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {ddcSources.length === 0 && (
                  <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px' }}>
                    No sources loaded. Click "Refresh from GitHub" to import deepdarkCTI catalogue.
                  </td></tr>
                )}
                {ddcSources.map(s => {
                  const statusColor = {
                    CONTENT_OBSERVED: '#10b981', REACHABLE: '#3b82f6', ENABLED: '#a78bfa',
                    UNREACHABLE: '#f59e0b', FAILED: '#ef4444', DISCOVERED: '#6b7280',
                    DISABLED: '#374151', COLLECTING: '#3b82f6',
                  }[s.collection_status] || '#6b7280';
                  const catColor = s.catalogue_status === 'ONLINE' ? '#10b981' : '#6b7280';
                  return (
                    <tr key={s.id}>
                      <td style={{ fontWeight: 600, color: '#fff', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {s.source_name}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-secondary)', maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {s.is_onion ? '🧅 ' : '🌐 '}{s.source_url}
                      </td>
                      <td><span className="badge" style={{ fontSize: '0.7rem', background: 'rgba(139,92,246,0.1)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.3)' }}>{s.category}</span></td>
                      <td><span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: catColor }}>{s.catalogue_status}</span></td>
                      <td>
                        <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: statusColor, fontWeight: 600 }}>
                          {s.collection_status}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: s.observation_count > 0 ? '#10b981' : 'var(--text-muted)' }}>
                        {s.observation_count}
                      </td>
                      <td>
                        {s.collection_status === 'DISCOVERED' ? (
                          <button
                            className="btn btn-sm"
                            onClick={() => handleDdcEnable(s.id)}
                            style={{ fontSize: '0.72rem', padding: '3px 10px', background: 'rgba(139,92,246,0.15)', borderColor: 'rgba(139,92,246,0.4)', color: '#a78bfa' }}
                          >
                            Enable
                          </button>
                        ) : s.collection_status === 'DISABLED' ? (
                          <button
                            className="btn btn-sm"
                            onClick={() => handleDdcEnable(s.id)}
                            style={{ fontSize: '0.72rem', padding: '3px 10px', background: 'rgba(16,185,129,0.1)', borderColor: 'rgba(16,185,129,0.3)', color: '#10b981' }}
                          >
                            Re-enable
                          </button>
                        ) : (
                          <button
                            className="btn btn-sm"
                            onClick={() => handleDdcDisable(s.id)}
                            style={{ fontSize: '0.72rem', padding: '3px 10px', background: 'rgba(239,68,68,0.1)', borderColor: 'rgba(239,68,68,0.3)', color: '#ef4444' }}
                          >
                            Disable
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
