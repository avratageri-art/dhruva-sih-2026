import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  FileText, Download, FileJson, Table, FileCode, Shield,
  User, Key, Wallet, Clock, Network, AlertTriangle, CheckCircle,
  X, ChevronDown, ChevronRight, Info, Search, Filter
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function Section({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', padding: '14px 20px', background: 'none', border: 'none',
          cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}
      >
        <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>{title}</span>
        {open ? <ChevronDown size={15} color="var(--text-muted)" /> : <ChevronRight size={15} color="var(--text-muted)" />}
      </button>
      {open && <div style={{ padding: '0 20px 16px' }}>{children}</div>}
    </div>
  );
}

function ConfBar({ value, max = 100 }) {
  const pct = Math.round((value / max) * 100);
  const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#94a3b8';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      <div style={{ flex: 1, height: '5px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '3px' }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color, minWidth: '35px' }}>{pct}%</span>
    </div>
  );
}

export default function Reports() {
  const [actors, setActors] = useState([]);
  const [selectedActor, setSelectedActor] = useState(null);
  const [profile, setProfile] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [exportFormat, setExportFormat] = useState(null);
  const [searchQ, setSearchQ] = useState('');

  useEffect(() => {
    axios.get(`${API_BASE}/api/actors?limit=25`)
      .then(r => {
        setActors(r.data);
        const sf = r.data.find(a => a.actor_name === 'ShadowFox') || r.data[0];
        if (sf) loadProfile(sf);
      })
      .catch(() => {});
  }, []);

  function loadProfile(actor) {
    setSelectedActor(actor);
    setLoading(true);
    setProfile(null);
    setAssessment(null);

    axios.get(`${API_BASE}/api/actors/${actor.id}`)
      .then(r => {
        setProfile(r.data);
        if (r.data.attribution_assessments?.length) {
          setAssessment(r.data.attribution_assessments[0]);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  function exportCSV() {
    if (!profile) return;
    const rows = [
      ['Field', 'Value'],
      ['Actor Name', profile.actor_name],
      ['Category', profile.category],
      ['Status', profile.status],
      ['Confidence', profile.confidence],
      ['First Seen', profile.first_seen],
      ['Last Seen', profile.last_seen],
      ...profile.handles.map(h => ['Handle', `${h.handle} (${h.platform})`]),
      ...profile.pgp_identifiers.map(p => ['PGP Fingerprint', p.fingerprint]),
      ...profile.wallets.map(w => ['Wallet', `${w.address} (${w.blockchain})`]),
    ];
    const csv = rows.map(r => r.map(v => `"${String(v || '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `dhruva_${profile.actor_name}_report.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  function exportJSON() {
    if (!profile) return;
    const report = {
      meta: { generated: new Date().toISOString(), source: 'DHRUVA', classification: 'ANALYTICAL ASSESSMENT — EVIDENCE REQUIRES REVIEW' },
      actor: profile,
      assessment: assessment,
      disclaimer: 'Analytical assessment only. Requires independent verification. Does not constitute legal attribution.',
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `dhruva_${profile.actor_name}.json`; a.click();
    URL.revokeObjectURL(url);
  }

  function exportSTIX() {
    if (!profile) return;
    const stix = {
      type: 'bundle',
      id: `bundle--${crypto.randomUUID()}`,
      objects: [
        {
          type: 'threat-actor',
          id: `threat-actor--${crypto.randomUUID()}`,
          spec_version: '2.1',
          created: new Date().toISOString(),
          modified: new Date().toISOString(),
          name: profile.actor_name,
          description: profile.description || '',
          threat_actor_types: [profile.category?.toLowerCase().replace(' ', '-') || 'unknown'],
          labels: ['threat-intelligence'],
          confidence: Math.round((profile.confidence || 0) * 100),
        },
        ...profile.handles.map(h => ({
          type: 'identity',
          id: `identity--${crypto.randomUUID()}`,
          spec_version: '2.1',
          created: h.first_seen || new Date().toISOString(),
          modified: h.last_seen || new Date().toISOString(),
          name: h.handle,
          identity_class: 'alias',
          labels: ['threat-intelligence'],
        })),
        ...profile.pgp_identifiers.map(p => ({
          type: 'indicator',
          id: `indicator--${crypto.randomUUID()}`,
          spec_version: '2.1',
          created: p.first_seen || new Date().toISOString(),
          modified: p.last_seen || new Date().toISOString(),
          name: `PGP: ${p.fingerprint}`,
          pattern: `[pgp-key:fingerprint = '${p.fingerprint}']`,
          pattern_type: 'stix',
          valid_from: p.first_seen || new Date().toISOString(),
          labels: ['threat-intelligence'],
        })),
      ],
    };
    const blob = new Blob([JSON.stringify(stix, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `dhruva_${profile.actor_name}_stix21.json`; a.click();
    URL.revokeObjectURL(url);
  }

  const filteredActors = actors.filter(a => !searchQ || a.actor_name.toLowerCase().includes(searchQ.toLowerCase()));

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0 }}>Intelligence Reports</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '0.9rem' }}>
            Generate exportable attribution reports. CSV · JSON · STIX 2.1
          </p>
        </div>
        <div style={{
          padding: '8px 16px', borderRadius: '6px', fontSize: '0.75rem',
          background: 'rgba(16,185,129,0.1)', color: '#6ee7b7',
          border: '1px solid rgba(16,185,129,0.3)', fontWeight: 600
        }}>
          LIVE CTI DOSSIER
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: '20px', alignItems: 'start' }}>
        {/* Actor selector */}
        <div className="card">
          <div className="card-header" style={{ padding: '14px 16px' }}>
            <User size={16} color="var(--accent-primary)" />
            <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>Select Actor</span>
          </div>
          <div style={{ padding: '8px 8px 8px' }}>
            <div style={{ position: 'relative', marginBottom: '8px' }}>
              <Search size={13} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input value={searchQ} onChange={e => setSearchQ(e.target.value)} placeholder="Search..." className="form-input" style={{ paddingLeft: '30px', fontSize: '0.8rem' }} />
            </div>
            {filteredActors.map(a => (
              <button
                key={a.id}
                onClick={() => loadProfile(a)}
                style={{
                  width: '100%', textAlign: 'left', padding: '8px 12px', borderRadius: '5px',
                  cursor: 'pointer', marginBottom: '2px',
                  background: selectedActor?.id === a.id ? 'rgba(59,130,246,0.12)' : 'transparent',
                  border: selectedActor?.id === a.id ? '1px solid rgba(59,130,246,0.3)' : '1px solid transparent',
                  color: selectedActor?.id === a.id ? '#93c5fd' : 'var(--text-secondary)',
                  fontSize: '0.85rem', fontFamily: 'var(--font-sans)',
                }}
              >
                {a.actor_name}
              </button>
            ))}
          </div>
        </div>

        {/* Report content */}
        {loading ? (
          <div className="card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading intelligence report...
          </div>
        ) : !profile ? (
          <div className="card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Select an actor to generate a report.
          </div>
        ) : (
          <div className="card">
            {/* Report Header */}
            <div style={{ padding: '20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  DHRUVA INTELLIGENCE REPORT — {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                </div>
                <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{profile.actor_name}</h2>
                <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ padding: '3px 10px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700, background: 'rgba(239,68,68,0.12)', color: '#fca5a5', border: '1px solid rgba(239,68,68,0.3)' }}>
                    {profile.category}
                  </span>
                  <span style={{ padding: '3px 10px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700, background: 'rgba(34,197,94,0.12)', color: '#86efac', border: '1px solid rgba(34,197,94,0.3)' }}>
                    {profile.status}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Confidence: <span style={{ color: '#22c55e', fontFamily: 'var(--font-mono)' }}>{Math.round((profile.confidence || 0) * 100)}%</span>
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button onClick={exportCSV} className="btn btn-secondary btn-sm"><Table size={13} /> CSV</button>
                <button onClick={exportJSON} className="btn btn-secondary btn-sm"><FileJson size={13} /> JSON</button>
                <button onClick={exportSTIX} className="btn btn-secondary btn-sm"><FileCode size={13} /> STIX 2.1</button>
              </div>
            </div>

            {/* Disclaimer */}
            <div style={{ margin: '16px 20px', padding: '10px 14px', borderRadius: '6px', background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)', fontSize: '0.78rem', color: '#6ee7b7', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
              <Info size={13} style={{ flexShrink: 0, marginTop: '1px' }} />
              Analytical assessment only. Requires independent verification. Does not constitute legal attribution. Verified threat intelligence.
            </div>

            {/* Executive Summary */}
            <Section title="Executive Summary">
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: '1.7' }}>
                {profile.description || `Threat actor persona ${profile.actor_name} has been observed across multiple dark web forums and services. The persona demonstrates consistent operational security practices and a distinct stylometric profile.`}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginTop: '14px' }}>
                {[
                  { label: 'First Seen', value: profile.first_seen?.split('T')[0] || '—' },
                  { label: 'Last Seen', value: profile.last_seen?.split('T')[0] || '—' },
                  { label: 'Handles', value: profile.handles?.length || 0 },
                  { label: 'Platforms', value: profile.platforms?.length || 0 },
                ].map((s, i) => (
                  <div key={i} style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>{s.label}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-primary)' }}>{s.value}</div>
                  </div>
                ))}
              </div>
            </Section>

            {/* Identifiers */}
            <Section title="Identifiers">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Handles */}
                <div>
                  <div className="section-label" style={{ marginBottom: '8px' }}>Handles / Aliases</div>
                  {profile.handles?.length ? profile.handles.map(h => (
                    <div key={h.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderRadius: '5px', background: 'rgba(6,182,212,0.06)', border: '1px solid rgba(6,182,212,0.2)', marginBottom: '6px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: '#22d3ee' }}>{h.handle}</span>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{h.platform}</span>
                    </div>
                  )) : <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No handles observed.</div>}
                </div>

                {/* PGP */}
                <div>
                  <div className="section-label" style={{ marginBottom: '8px' }}>PGP Fingerprints</div>
                  {profile.pgp_identifiers?.length ? profile.pgp_identifiers.map(p => (
                    <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderRadius: '5px', background: 'rgba(168,85,247,0.06)', border: '1px solid rgba(168,85,247,0.2)', marginBottom: '6px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#c084fc' }}>{p.fingerprint}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.first_seen?.split('T')[0]}</span>
                    </div>
                  )) : <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No PGP identifiers observed.</div>}
                </div>

                {/* Wallets */}
                <div>
                  <div className="section-label" style={{ marginBottom: '8px' }}>Cryptocurrency Wallets</div>
                  {profile.wallets?.length ? profile.wallets.map(w => (
                    <div key={w.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderRadius: '5px', background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.2)', marginBottom: '6px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#34d399', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '70%' }}>{w.address}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', flexShrink: 0 }}>{w.blockchain}</span>
                    </div>
                  )) : <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No wallets observed.</div>}
                </div>
              </div>
            </Section>

            {/* Attribution Assessment */}
            {assessment && (
              <Section title="Attribution Assessment">
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2.2rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: assessment.score >= 80 ? '#22c55e' : assessment.score >= 60 ? '#f59e0b' : '#94a3b8' }}>
                      {assessment.score >= 1 ? Math.round(assessment.score) : Math.round(assessment.score * 100)}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>/ 100</div>
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '1rem', color: assessment.score >= 80 ? '#22c55e' : '#f59e0b' }}>
                      {assessment.confidence_level}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Attribution Confidence</div>
                  </div>
                </div>

                {/* Positive evidence */}
                {assessment.evidence && (
                  <div style={{ marginBottom: '12px' }}>
                    <div className="section-label" style={{ marginBottom: '8px', color: '#22c55e' }}>Positive Evidence</div>
                    {Object.entries(assessment.evidence).filter(([, v]) => v.type === 'positive').map(([key, ev]) => (
                      <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', borderRadius: '5px', background: 'rgba(34,197,94,0.05)', border: '1px solid rgba(34,197,94,0.15)', marginBottom: '5px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <CheckCircle size={13} color="#22c55e" />
                          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{ev.description}</span>
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#22c55e', fontWeight: 700, flexShrink: 0, marginLeft: '8px' }}>+{ev.score}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Negative evidence */}
                {assessment.negative_evidence && Object.entries(assessment.negative_evidence).length > 0 && (
                  <div>
                    <div className="section-label" style={{ marginBottom: '8px', color: '#f59e0b' }}>Negative / Conflicting Evidence</div>
                    {Object.entries(assessment.negative_evidence).map(([key, desc]) => (
                      <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', borderRadius: '5px', background: 'rgba(245,158,11,0.05)', border: '1px solid rgba(245,158,11,0.15)', marginBottom: '5px' }}>
                        <AlertTriangle size={13} color="#f59e0b" />
                        <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{desc}</span>
                      </div>
                    ))}
                  </div>
                )}

                {assessment.explanation && (
                  <div style={{ marginTop: '12px', padding: '12px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                    {assessment.explanation}
                  </div>
                )}
              </Section>
            )}

            {/* Limitations */}
            <Section title="Limitations &amp; Caveats" defaultOpen={false}>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: '1.7' }}>
                <p>• Attribution assessments are based on analytical correlation of observable intelligence and do not constitute legal identification.</p>
                <p style={{ marginTop: '8px' }}>• Stylometric and behavioural similarity does not prove identity — only analytical likeness within the observed data.</p>
                <p style={{ marginTop: '8px' }}>• Darknet intelligence aggregated via live Tor SOCKS5 crawler and deepdarkCTI seed catalogue.</p>
                <p style={{ marginTop: '8px' }}>• Production deployment requires appropriate legal authorization and independent analyst review.</p>
                <p style={{ marginTop: '8px' }}>• Tor anonymity is not assumed to be defeated through this platform's analytical methods.</p>
              </div>
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}
