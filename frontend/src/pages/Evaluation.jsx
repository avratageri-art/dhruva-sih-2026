import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { AlertTriangle, BarChart3, ShieldCheck } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const pct = value => `${Math.round((value || 0) * 1000) / 10}%`;

export default function Evaluation() {
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get('/api/analysis/evaluation').then(response => setResults(response.data)).catch(err => setError(err.message));
  }, []);

  if (error) return <div className="glass-card" style={{ padding: 20, color: 'var(--warning)' }}><AlertTriangle size={16} /> {error}</div>;
  if (!results) return <div style={{ color: 'var(--text-muted)' }}>Loading evaluation results…</div>;

  const comparison = [
    ['Similarity baseline', results.baseline],
    ['Reliability engine', results.reliability_engine],
  ];
  const curve = results.precision_coverage_curve.map(row => ({ ...row, coveragePct: row.coverage * 100, precisionPct: row.precision * 100 }));

  return (
    <div className="fade-in">
      <h1 style={{ marginBottom: 6 }}>Reliability Evaluation</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>Seed {results.benchmark.seed} · {results.benchmark.cases} synthetic adversarial pairs</p>
      <div className="glass-card" style={{ padding: 14, margin: '18px 0', borderLeft: '3px solid var(--warning)', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
        Synthetic failure-mode test only; these numbers do not estimate real-world attribution accuracy.
      </div>

      <div className="grid grid-cols-2" style={{ marginBottom: 20 }}>
        {comparison.map(([name, row]) => <div key={name} className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 14 }}><ShieldCheck size={16} color="var(--accent-primary)" /><strong>{name}</strong></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
            {[['Precision', row.precision], ['Recall', row.recall], ['Coverage', row.coverage], ['False links', row.false_link_rate]].map(([label, value]) => <div key={label}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.67rem' }}>{label}</div><div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem' }}>{pct(value)}</div>
            </div>)}
          </div>
        </div>)}
      </div>

      <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
        <div className="section-label" style={{ marginBottom: 12 }}><BarChart3 size={14} /> Failure-family breakdown</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}><thead><tr style={{ textAlign: 'left', color: 'var(--text-muted)' }}>
          {['Family', 'Cases', 'Baseline false links', 'Engine false links', 'Engine supported', 'Dominant reason'].map(value => <th key={value} style={{ padding: 8, borderBottom: '1px solid var(--border-subtle)' }}>{value}</th>)}
        </tr></thead><tbody>{Object.entries(results.per_family).map(([family, row]) => <tr key={family} style={{ color: 'var(--text-secondary)' }}>
          <td style={{ padding: 8 }}>{family.replaceAll('_', ' ')}</td><td>{row.count}</td><td style={{ color: '#ef4444' }}>{row.baseline_false_links}</td><td style={{ color: '#22c55e' }}>{row.engine_false_links}</td><td>{row.engine_supported}</td><td>{row.dominant_reason || '—'}</td>
        </tr>)}</tbody></table>
      </div>

      <div className="glass-card" style={{ padding: 20, height: 310 }}>
        <div className="section-label" style={{ marginBottom: 10 }}>Precision versus coverage</div>
        <ResponsiveContainer width="100%" height="90%"><LineChart data={curve}><CartesianGrid stroke="rgba(255,255,255,.08)" /><XAxis dataKey="coveragePct" unit="%" /><YAxis domain={[0,100]} unit="%" /><Tooltip /><Line type="monotone" dataKey="precisionPct" name="Precision" stroke="#22c55e" strokeWidth={3} /></LineChart></ResponsiveContainer>
      </div>
    </div>
  );
}
