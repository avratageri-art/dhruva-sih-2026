import React, { useState, useEffect } from 'react';
import { Server, Database, Cpu, Globe, Network, HardDrive, CheckCircle, XCircle, Clock } from 'lucide-react';
import axios from 'axios';

const LAYERS = [
  {
    id: 'collection',
    name: 'Data Collection Layer',
    color: '#3b82f6',
    components: [
      { name: 'Source Adapter (Ransomwatch)', type: 'OSINT Feed', status: 'ACTIVE', note: 'Live ransomware group telemetry' },
      { name: 'Forum Scraper (Synthetic)', type: 'Web Scraper', status: 'DEMO', note: 'Simulated darknet forum data' },
      { name: 'Paste Monitor', type: 'OSINT Feed', status: 'DEMO', note: 'Pastebin & darknet paste sites' },
    ],
    icon: Globe,
    description: 'Ingests raw intelligence from authorized OSINT feeds and simulated data sources.',
  },
  {
    id: 'processing',
    name: 'Processing & Extraction Layer',
    color: '#8b5cf6',
    components: [
      { name: 'Entity Extractor', type: 'AI Module', status: 'ACTIVE', note: 'Regex + spaCy NER' },
      { name: 'Stylometry Engine', type: 'AI Module', status: 'ACTIVE', note: 'MiniLM-L6-v2 + lexical features' },
      { name: 'Behaviour Profiler', type: 'AI Module', status: 'ACTIVE', note: 'Temporal pattern analysis' },
      { name: 'Entity Resolution', type: 'AI Module', status: 'ACTIVE', note: 'Fuzzy handle matching' },
    ],
    icon: Cpu,
    description: 'Processes raw text with AI/ML pipelines to extract structured intelligence.',
  },
  {
    id: 'storage',
    name: 'Storage Layer',
    color: '#10b981',
    components: [
      { name: 'SQLite / PostgreSQL', type: 'Relational DB', status: 'ACTIVE', note: 'Actors, handles, posts, indicators' },
      { name: 'Neo4j Graph DB', type: 'Graph DB', status: 'ACTIVE', note: 'Entity relationship graph & network traversal' },
      { name: 'MLflow Tracking', type: 'ML Registry', status: 'DEMO', note: 'Model metrics & versioning' },
    ],
    icon: Database,
    description: 'Stores structured intelligence and model artifacts with full auditability.',
  },
  {
    id: 'analysis',
    name: 'Analysis & Attribution Layer',
    color: '#f59e0b',
    components: [
      { name: 'Attribution Engine', type: 'AI Module', status: 'ACTIVE', note: 'Weighted multi-vector fusion' },
      { name: 'Graph Correlation', type: 'Algorithm', status: 'ACTIVE', note: 'Network analysis & bridge detection' },
      { name: 'Risk Scoring', type: 'Algorithm', status: 'ACTIVE', note: 'Confidence calibration' },
    ],
    icon: Network,
    description: 'Fuses all evidence vectors into explainable attribution confidence assessments.',
  },
  {
    id: 'presentation',
    name: 'Presentation Layer',
    color: '#ef4444',
    components: [
      { name: 'React + Vite Frontend', type: 'Web App', status: 'ACTIVE', note: 'Dark-mode analyst dashboard' },
      { name: 'FastAPI REST API', type: 'Backend', status: 'ACTIVE', note: 'OpenAPI 3.0 documented' },
      { name: 'Cytoscape.js Graph', type: 'Visualization', status: 'ACTIVE', note: 'Interactive entity network' },
      { name: 'PDF / STIX Export', type: 'Export', status: 'PLANNED', note: 'Report generation' },
    ],
    icon: HardDrive,
    description: 'Full-stack web dashboard and API for analysts to query and visualise intelligence.',
  },
];

const STATUS_CONFIG = {
  ACTIVE:  { class: 'badge-low',      icon: CheckCircle, color: 'var(--success)' },
  DEMO:    { class: 'badge-medium',   icon: Clock,       color: 'var(--warning)' },
  PARTIAL: { class: 'badge-medium',   icon: Clock,       color: 'var(--warning)' },
  PLANNED: { class: 'badge-neutral',  icon: Clock,       color: 'var(--text-muted)' },
};

function LayerCard({ layer, isSelected, onClick }) {
  const Icon = layer.icon;
  const active = layer.components.filter(c => c.status === 'ACTIVE').length;
  return (
    <div
      className="glass-card"
      onClick={onClick}
      style={{
        padding: '18px 20px', cursor: 'pointer',
        borderColor: isSelected ? layer.color : 'var(--border-subtle)',
        boxShadow: isSelected ? `0 0 16px ${layer.color}22` : 'none',
        transition: 'all 0.2s ease',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
        <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)',
                      background: `${layer.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon size={18} color={layer.color} />
        </div>
        <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)' }}>{layer.name}</div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          {layer.components.length} components
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: layer.color }}>
          {active}/{layer.components.length} active
        </span>
      </div>
      <div className="confidence-bar" style={{ marginTop: '8px' }}>
        <div className="confidence-bar-fill"
             style={{ width: `${(active / layer.components.length) * 100}%`, background: layer.color }} />
      </div>
    </div>
  );
}

export default function Architecture() {
  const [selected, setSelected] = useState(LAYERS[0]);
  const [apiStatus, setApiStatus] = useState(null);

  useEffect(() => {
    axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/`)
      .then(r => setApiStatus({ online: true, ...r.data }))
      .catch(() => setApiStatus({ online: false }));
  }, []);

  const totalComponents = LAYERS.reduce((sum, l) => sum + l.components.length, 0);
  const activeComponents = LAYERS.reduce((sum, l) => sum + l.components.filter(c => c.status === 'ACTIVE').length, 0);

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' }}>
        <div>
          <h1 style={{ margin: 0 }}>System Architecture</h1>
          <p style={{ color: 'var(--text-secondary)', margin: '6px 0 0 0' }}>
            DHRUVA modular pipeline — {activeComponents}/{totalComponents} components operational.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center',
                      padding: '8px 16px', background: 'var(--bg-elevated)',
                      borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%',
                        background: apiStatus?.online ? 'var(--success)' : 'var(--danger)',
                        boxShadow: apiStatus?.online ? '0 0 8px var(--success)' : 'none' }} />
          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            API: {apiStatus?.online ? 'Online' : apiStatus === null ? 'Checking...' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Architecture flow diagram */}
      <div className="glass-card" style={{ padding: '24px', marginBottom: '24px', overflowX: 'auto' }}>
        <div className="section-label" style={{ marginBottom: '20px' }}>Data Flow Diagram</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0', minWidth: '700px' }}>
          {LAYERS.map((layer, i) => {
            const Icon = layer.icon;
            return (
              <React.Fragment key={layer.id}>
                <div
                  onClick={() => setSelected(layer)}
                  style={{
                    flex: 1, padding: '16px', borderRadius: 'var(--radius-md)',
                    background: selected.id === layer.id ? `${layer.color}18` : 'var(--bg-elevated)',
                    border: `1px solid ${selected.id === layer.id ? layer.color : 'var(--border-subtle)'}`,
                    textAlign: 'center', cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <Icon size={22} color={layer.color} style={{ display: 'block', margin: '0 auto 8px' }} />
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                    {layer.name.replace(' Layer', '')}
                  </div>
                  <div style={{ marginTop: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: layer.color }}>
                    {layer.components.filter(c => c.status === 'ACTIVE').length}/{layer.components.length}
                  </div>
                </div>
                {i < LAYERS.length - 1 && (
                  <div style={{ padding: '0 4px', color: 'var(--border-default)', flexShrink: 0, fontSize: '1.2rem' }}>
                    →
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '20px' }}>
        {/* Layer list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {LAYERS.map(layer => (
            <LayerCard key={layer.id} layer={layer} isSelected={selected.id === layer.id}
                       onClick={() => setSelected(layer)} />
          ))}
        </div>

        {/* Detail panel */}
        {selected && (
          <div>
            <div className="glass-card" style={{ padding: '24px', marginBottom: '16px', borderColor: selected.color }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                <selected.icon size={22} color={selected.color} />
                <h2 style={{ margin: 0 }}>{selected.name}</h2>
              </div>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>{selected.description}</p>
            </div>

            <div className="card" style={{ overflow: 'hidden' }}>
              <div className="card-header">
                <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Components</div>
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Component</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.components.map((comp, i) => {
                    const cfg = STATUS_CONFIG[comp.status] || STATUS_CONFIG.DEMO;
                    const StatusIcon = cfg.icon;
                    return (
                      <tr key={i}>
                        <td style={{ padding: '14px 16px', fontWeight: 500, color: 'var(--text-primary)' }}>
                          {comp.name}
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <span className="badge badge-info">{comp.type}</span>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <span className={`badge ${cfg.class}`} style={{ display: 'flex', gap: '5px', alignItems: 'center', width: 'fit-content' }}>
                            <StatusIcon size={11} /> {comp.status}
                          </span>
                        </td>
                        <td style={{ padding: '14px 16px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {comp.note}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Tech Stack */}
      <div className="glass-card" style={{ padding: '24px', marginTop: '20px' }}>
        <div className="section-label" style={{ marginBottom: '16px' }}>Technology Stack</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          {[
            { label: 'Frontend', items: ['React 18', 'Vite', 'Cytoscape.js', 'Recharts'] },
            { label: 'Backend', items: ['FastAPI', 'SQLAlchemy', 'Pydantic v2', 'Uvicorn'] },
            { label: 'AI / ML', items: ['Sentence Transformers', 'spaCy', 'scikit-learn', 'MLflow'] },
            { label: 'Infrastructure', items: ['SQLite / PostgreSQL', 'Neo4j', 'Docker Compose', 'Alembic'] },
          ].map(group => (
            <div key={group.label}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)',
                            textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>
                {group.label}
              </div>
              {group.items.map(item => (
                <div key={item} className="evidence-item" style={{ padding: '4px 0' }}>
                  <CheckCircle size={12} color="var(--accent-primary)" />
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{item}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
