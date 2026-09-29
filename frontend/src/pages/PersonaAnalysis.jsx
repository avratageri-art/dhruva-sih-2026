import React, { useState, useEffect } from 'react';
import { Fingerprint, Zap, CheckCircle, XCircle, ChevronRight, RefreshCw, AlertTriangle, Cpu, Activity, Brain, GitMerge, Database } from 'lucide-react';
import axios from 'axios';

const API = 'http://localhost:8000';

// ── Score arc meter ─────────────────────────────────────────────────────────
function ScoreMeter({ score, aiPowered }) {
  const pct = Math.round(score);
  const color = pct >= 85 ? '#ef4444' : pct >= 65 ? '#f59e0b' : pct >= 45 ? '#3b82f6' : '#475569';
  const label = pct >= 85 ? 'VERY HIGH' : pct >= 65 ? 'HIGH' : pct >= 45 ? 'MEDIUM' : 'LOW';
  const labelClass = pct >= 85 ? 'badge-critical' : pct >= 65 ? 'badge-high' : pct >= 45 ? 'badge-medium' : 'badge-neutral';

  const r = 70, cx = 90, cy = 90;
  const startAngle = -210, totalDeg = 240;
  const arcDeg = (pct / 100) * totalDeg;
  const toRad = d => d * Math.PI / 180;
  const largeArc = arcDeg > 180 ? 1 : 0;
  const endDeg = startAngle + arcDeg;

  const sx = cx + r * Math.cos(toRad(startAngle));
  const sy = cy + r * Math.sin(toRad(startAngle));
  const ex = cx + r * Math.cos(toRad(endDeg));
  const ey = cy + r * Math.sin(toRad(endDeg));

  const bsx = cx + r * Math.cos(toRad(startAngle));
  const bsy = cy + r * Math.sin(toRad(startAngle));
  const bex = cx + r * Math.cos(toRad(startAngle + totalDeg));
  const bey = cy + r * Math.sin(toRad(startAngle + totalDeg));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
      <svg width="180" height="180" style={{ overflow: 'visible' }}>
        {/* Background arc */}
        <path d={`M ${bsx},${bsy} A ${r},${r} 0 1,1 ${bex},${bey}`}
              fill="none" stroke="var(--border-subtle)" strokeWidth="10" strokeLinecap="round" />
        {/* Score arc */}
        {pct > 0 && (
          <path d={`M ${sx},${sy} A ${r},${r} 0 ${largeArc},1 ${ex},${ey}`}
                fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
                style={{ transition: 'all 0.8s cubic-bezier(0.4,0,0.2,1)' }} />
        )}
        {/* Glow */}
        {pct > 0 && (
          <path d={`M ${sx},${sy} A ${r},${r} 0 ${largeArc},1 ${ex},${ey}`}
                fill="none" stroke={color} strokeWidth="20" strokeLinecap="round"
                opacity="0.15" />
        )}
        <text x={cx} y={cy - 8} textAnchor="middle" fill={color}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '30px', fontWeight: 700 }}>
          {pct}%
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fill="var(--text-muted)"
              style={{ fontFamily: 'var(--font-sans)', fontSize: '11px' }}>
          attribution score
        </text>
      </svg>
      <span className={`badge ${labelClass}`} style={{ fontSize: '0.72rem', padding: '4px 12px' }}>
        {label} CONFIDENCE
      </span>
      {aiPowered !== undefined && (
        <span style={{
          fontSize: '0.68rem', padding: '2px 10px', borderRadius: '4px',
          background: aiPowered ? 'rgba(34,197,94,0.12)' : 'rgba(245,158,11,0.12)',
          color: aiPowered ? '#22c55e' : '#f59e0b',
          display: 'flex', alignItems: 'center', gap: '5px',
        }}>
          <Cpu size={10} />
          {aiPowered ? 'all-MiniLM-L6-v2 active' : 'heuristic fallback'}
        </span>
      )}
    </div>
  );
}

// ── Subsystem evidence bar ──────────────────────────────────────────────────
const SUBSYSTEM_META = {
  semantic_similarity:    { label: 'Semantic Similarity',   icon: Brain,    desc: 'sentence-transformers cosine', weight: 35 },
  stylometric_similarity: { label: 'Stylometric Analysis',  icon: Activity, desc: '9-feature NLP vector',         weight: 25 },
  behavioural_similarity: { label: 'Behavioural Analysis',  icon: Activity, desc: '24-bin temporal histogram',    weight: 20 },
  handle_overlap:         { label: 'Handle Overlap',        icon: GitMerge, desc: 'Jaro-Winkler similarity',     weight: 15 },
  graph_correlation:      { label: 'Graph Correlation',     icon: Database, desc: 'Jaccard infrastructure',       weight: 5  },
};

function EvidenceBar({ field, value }) {
  const meta = SUBSYSTEM_META[field] || { label: field, desc: '', weight: 0 };
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 70 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#94a3b8';
  const Icon = meta.icon || Activity;
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          <Icon size={13} color="var(--accent-primary)" />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{meta.label}</span>
          <span style={{
            fontSize: '0.62rem', padding: '1px 6px', borderRadius: '3px',
            background: 'rgba(99,102,241,0.12)', color: 'var(--accent-primary)',
          }}>w={meta.weight}%</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 600, color }}>
          {pct}%
        </span>
      </div>
      <div className="confidence-bar" style={{ height: '5px' }}>
        <div className="confidence-bar-fill"
             style={{ width: `${pct}%`, background: color, transition: 'width 0.7s ease' }} />
      </div>
      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{meta.desc}</span>
    </div>
  );
}

// ── Full assessment result card ─────────────────────────────────────────────
function AssessmentCard({ assessment }) {
  if (!assessment) return null;
  const evidence = assessment.evidence || {};

  const negSignals = [];
  if (assessment.explanation?.toLowerCase().includes('timezone')) negSignals.push('Significant timezone offset detected');
  if (assessment.explanation?.toLowerCase().includes('different platforms')) negSignals.push('Low cross-platform handle similarity');

  const posSignals = [];
  if ((evidence.semantic_similarity || 0) > 0.5) posSignals.push(`Semantic embedding cosine: ${Math.round((evidence.semantic_similarity || 0) * 100)}%`);
  if ((evidence.handle_overlap || 0) > 0.3) posSignals.push('Handle naming pattern overlap detected');
  if ((evidence.behavioural_similarity || 0) > 0.5) posSignals.push('Temporal activity patterns correlated');
  if ((evidence.graph_correlation || 0) > 0) posSignals.push('Shared infrastructure indicators found');

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '20px' }}>
      {/* Left: Meter */}
      <div className="glass-card" style={{ padding: '30px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
        <ScoreMeter score={assessment.score} aiPowered={evidence.ai_powered} />
        <div style={{
          padding: '10px 14px', background: 'rgba(99,102,241,0.06)',
          borderRadius: '8px', border: '1px solid rgba(99,102,241,0.15)',
          width: '100%',
        }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Model</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--accent-primary)', wordBreak: 'break-all' }}>
            {evidence.model || 'all-MiniLM-L6-v2'}
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Texts compared: {evidence.texts_compared || '—'}
          </div>
        </div>
      </div>

      {/* Right: Evidence */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* AI subsystem scores */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Cpu size={14} color="var(--accent-primary)" />
            <span className="section-label" style={{ margin: 0 }}>AI Pipeline Scores</span>
            <span style={{
              fontSize: '0.62rem', padding: '2px 7px', borderRadius: '4px',
              background: 'rgba(34,197,94,0.1)', color: '#22c55e',
            }}>LIVE MODEL OUTPUT</span>
          </div>
          {Object.entries(SUBSYSTEM_META).map(([key]) => (
            <EvidenceBar key={key} field={key} value={evidence[key] || 0} />
          ))}
        </div>

        {/* Signals */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div className="section-label" style={{ marginBottom: '12px' }}>Attribution Signals</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
            {posSignals.map((s, i) => (
              <div key={i} className="evidence-item">
                <CheckCircle size={13} color="var(--success)" style={{ flexShrink: 0 }} />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{s}</span>
              </div>
            ))}
            {negSignals.map((s, i) => (
              <div key={i} className="evidence-item">
                <XCircle size={13} color="var(--warning)" style={{ flexShrink: 0 }} />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{s}</span>
              </div>
            ))}
            {posSignals.length === 0 && negSignals.length === 0 && (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No notable signals.</span>
            )}
          </div>
        </div>

        {/* Explanation */}
        <div className="glass-card" style={{ padding: '16px' }}>
          <div className="section-label" style={{ marginBottom: '8px' }}>Engine Explanation</div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.65, margin: 0, fontFamily: 'var(--font-mono)' }}>
            {assessment.explanation}
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function PersonaAnalysis() {
  const [actors, setActors] = useState([]);
  const [actorA, setActorA] = useState('');
  const [actorB, setActorB] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recentAssessments, setRecentAssessments] = useState([]);
  const [modelStatus, setModelStatus] = useState(null);

  useEffect(() => {
    axios.get(`${API}/api/actors`)
      .then(r => setActors(r.data.map(a => ({ id: a.id, actor_name: a.actor_name, confidence: a.confidence }))))
      .catch(() => {});

    axios.get(`${API}/api/analysis/assessments`)
      .then(r => setRecentAssessments(r.data.slice(0, 6)))
      .catch(() => {});

    axios.get(`${API}/api/model-status`)
      .then(r => setModelStatus(r.data))
      .catch(() => {});
  }, []);

  const runAnalysis = async () => {
    if (!actorA || !actorB || actorA === actorB) {
      setError('Please select two different actors to compare.');
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const r = await axios.post(`${API}/api/analysis/assess?actor_a_id=${actorA}&actor_b_id=${actorB}`);
      setResult(r.data);
      // Refresh recent list
      const ra = await axios.get(`${API}/api/analysis/assessments`);
      setRecentAssessments(ra.data.slice(0, 6));
      // Refresh model status to confirm it loaded
      const ms = await axios.get(`${API}/api/model-status`);
      setModelStatus(ms.data);
    } catch (e) {
      setError(`Analysis failed: ${e?.response?.data?.detail || e.message}`);
    }
    setLoading(false);
  };

  const nameForId = id => actors.find(a => a.id == id)?.actor_name || `Actor #${id}`;

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0 }}>Persona Analysis</h1>
        <p style={{ color: 'var(--text-secondary)', margin: '6px 0 0 0' }}>
          Real AI attribution powered by <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88em', color: 'var(--accent-primary)' }}>sentence-transformers/all-MiniLM-L6-v2</code>,
          classical stylometry, temporal behaviour analysis and Jaro-Winkler entity resolution.
        </p>
      </div>

      {/* Model status banner */}
      {modelStatus && (
        <div className="glass-card" style={{
          padding: '14px 20px', marginBottom: '20px',
          display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap',
          borderLeft: `3px solid ${modelStatus.model_loaded ? '#22c55e' : '#f59e0b'}`,
        }}>
          <Cpu size={16} color={modelStatus.model_loaded ? '#22c55e' : '#f59e0b'} />
          <div style={{ flex: 1 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)' }}>
              {modelStatus.model_name}
            </span>
            <span style={{
              marginLeft: '10px', fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px',
              background: modelStatus.model_loaded ? 'rgba(34,197,94,0.12)' : 'rgba(245,158,11,0.12)',
              color: modelStatus.model_loaded ? '#22c55e' : '#f59e0b',
            }}>
              {modelStatus.status?.toUpperCase().replace('_', ' ')}
            </span>
          </div>
          {modelStatus.pipeline?.map((p, i) => (
            <div key={i} style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textAlign: 'center' }}>
              <div style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{Math.round(p.weight * 100)}%</div>
              <div>{p.name}</div>
            </div>
          ))}
        </div>
      )}

      {/* Actor selector */}
      <div className="glass-card" style={{ padding: '24px', marginBottom: '24px' }}>
        <div className="section-label" style={{ marginBottom: '16px' }}>Select Actors to Compare</div>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Actor A
            </label>
            <select className="form-select" style={{ width: '100%' }} value={actorA} onChange={e => setActorA(e.target.value)}>
              <option value="">Select actor...</option>
              {actors.map(a => <option key={a.id} value={a.id}>{a.actor_name}</option>)}
            </select>
          </div>

          <div style={{ padding: '8px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
            <ChevronRight size={20} />
          </div>

          <div style={{ flex: 1, minWidth: '200px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Actor B
            </label>
            <select className="form-select" style={{ width: '100%' }} value={actorB} onChange={e => setActorB(e.target.value)}>
              <option value="">Select actor...</option>
              {actors.map(a => <option key={a.id} value={a.id}>{a.actor_name}</option>)}
            </select>
          </div>

          <button
            className="btn btn-primary"
            onClick={runAnalysis}
            disabled={loading || !actorA || !actorB}
            style={{ padding: '10px 28px', display: 'flex', gap: '8px', alignItems: 'center' }}
          >
            {loading ? <RefreshCw size={16} className="spin" /> : <Zap size={16} />}
            {loading ? 'Running AI Pipeline…' : 'Run Attribution Analysis'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '12px', display: 'flex', gap: '8px', alignItems: 'center', color: 'var(--warning)', fontSize: '0.85rem' }}>
            <AlertTriangle size={15} /> {error}
          </div>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="glass-card" style={{ padding: '40px', textAlign: 'center', marginBottom: '24px' }}>
          <RefreshCw size={28} className="spin" color="var(--accent-primary)" style={{ margin: '0 auto 16px' }} />
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Loading <code style={{ color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>all-MiniLM-L6-v2</code>,
            generating embeddings and computing attribution score…
          </div>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Fingerprint size={20} color="var(--accent-primary)" />
            <h2 style={{ margin: 0 }}>
              {result.actor_a?.name || nameForId(actorA)} ↔ {result.actor_b?.name || nameForId(actorB)}
            </h2>
          </div>
          <AssessmentCard assessment={result} />
        </div>
      )}

      {/* Recent assessments */}
      <div>
        <h3 style={{ marginBottom: '16px' }}>Recent Assessments</h3>
        {recentAssessments.length === 0 ? (
          <div className="glass-card" style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No assessments yet. Run an analysis above to generate attribution scores.
          </div>
        ) : (
          <div className="grid grid-cols-3">
            {recentAssessments.map(aa => {
              const score = aa.score;
              const color = score >= 85 ? '#ef4444' : score >= 65 ? '#f59e0b' : '#3b82f6';
              const badgeClass = score >= 85 ? 'badge-critical' : score >= 65 ? 'badge-high' : 'badge-medium';
              const ev = aa.evidence || {};
              return (
                <div key={aa.id} className="glass-card" style={{ padding: '18px', cursor: 'pointer' }}
                     onClick={() => { setActorA(aa.actor_a?.id); setActorB(aa.actor_b?.id); setResult(aa); }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <span className={`badge ${badgeClass}`}>{aa.confidence_level}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color }}>
                      {score}%
                    </span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)', marginBottom: '8px' }}>
                    {aa.actor_a?.name} ↔ {aa.actor_b?.name}
                  </div>
                  <div className="confidence-bar" style={{ height: '4px', marginBottom: '10px' }}>
                    <div className="confidence-bar-fill" style={{ width: `${score}%`, background: color }} />
                  </div>
                  {/* Mini subsystem bars */}
                  {ev.semantic_similarity !== undefined && (
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {[
                        { k: 'SEM', v: ev.semantic_similarity },
                        { k: 'STY', v: ev.stylometric_similarity },
                        { k: 'BEH', v: ev.behavioural_similarity },
                      ].map(({ k, v }) => (
                        <span key={k} style={{
                          fontSize: '0.65rem', padding: '2px 6px', borderRadius: '3px',
                          background: 'rgba(99,102,241,0.1)', color: 'var(--accent-primary)',
                          fontFamily: 'var(--font-mono)',
                        }}>
                          {k}: {Math.round((v || 0) * 100)}%
                        </span>
                      ))}
                      {ev.model_loaded && (
                        <span style={{
                          fontSize: '0.65rem', padding: '2px 6px', borderRadius: '3px',
                          background: 'rgba(34,197,94,0.1)', color: '#22c55e',
                        }}>AI ✓</span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
