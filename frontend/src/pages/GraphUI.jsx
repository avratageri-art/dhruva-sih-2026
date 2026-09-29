import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import {
  Search, Filter, Maximize, Minimize, Crosshair, RefreshCw, Layers,
  Compass, Shield, User, Key, Wallet, Globe, Server, Hash, Database,
  ArrowRight, CheckCircle2, AlertTriangle, X, Copy, Check, ExternalLink,
  ChevronRight, Info, Eye, Sparkles
} from 'lucide-react';

const API_BASE = window.location.port === '3000' ? '' : 'http://localhost:8000';

// ── Semantic Entity Configurations ──────────────────────────────────────────
const ENTITY_CONFIG = {
  Actor: {
    shape: 'ellipse',
    color: '#ef4444',
    bg: '#dc2626',
    border: '#f87171',
    size: 52,
    icon: User,
    label: 'Threat Actor',
  },
  Handle: {
    shape: 'round-rectangle',
    color: '#06b6d4',
    bg: '#0891b2',
    border: '#22d3ee',
    size: 38,
    icon: Hash,
    label: 'Handle / Alias',
  },
  PGP: {
    shape: 'hexagon',
    color: '#a855f7',
    bg: '#9333ea',
    border: '#c084fc',
    size: 40,
    icon: Key,
    label: 'PGP Key',
  },
  Wallet: {
    shape: 'round-rectangle',
    color: '#10b981',
    bg: '#059669',
    border: '#34d399',
    size: 38,
    icon: Wallet,
    label: 'Crypto Wallet',
  },
  Platform: {
    shape: 'round-rectangle',
    color: '#f59e0b',
    bg: '#d97706',
    border: '#fbbf24',
    size: 42,
    icon: Globe,
    label: 'Platform / Forum',
  },
  OnionService: {
    shape: 'diamond',
    color: '#14b8a6',
    bg: '#0d9488',
    border: '#2dd4bf',
    size: 42,
    icon: Server,
    label: 'Onion Hidden Service',
  },
  Domain: {
    shape: 'round-rectangle',
    color: '#3b82f6',
    bg: '#2563eb',
    border: '#60a5fa',
    size: 38,
    icon: Globe,
    label: 'Clearnet Domain',
  },
  Infrastructure: {
    shape: 'triangle',
    color: '#eab308',
    bg: '#ca8a04',
    border: '#fde047',
    size: 38,
    icon: Database,
    label: 'Infrastructure Indicator',
  },
  Source: {
    shape: 'ellipse',
    color: '#64748b',
    bg: '#475569',
    border: '#94a3b8',
    size: 30,
    icon: Info,
    label: 'OSINT Source',
  },
};

// ── Cytoscape Stylesheet Factory ────────────────────────────────────────────
function createStylesheet() {
  return [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'color': '#cbd5e1',
        'font-family': 'Inter, system-ui, -apple-system, sans-serif',
        'font-size': '11px',
        'font-weight': 600,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 7,
        'text-wrap': 'wrap',
        'text-max-width': '95px',
        'text-background-opacity': 0.75,
        'text-background-color': '#070b13',
        'text-background-padding': '3px',
        'text-background-shape': 'roundrectangle',
        'border-width': 2,
        'border-color': 'rgba(255, 255, 255, 0.25)',
        'transition-property': 'background-color, border-color, border-width, width, height, opacity',
        'transition-duration': '0.25s',
      },
    },
    // Primary Focused Actor
    {
      selector: 'node[?is_primary]',
      style: {
        'border-width': 4,
        'border-color': '#ff003c',
        'border-opacity': 1.0,
        'font-size': '13px',
        'font-weight': 700,
        'color': '#ffffff',
        'text-background-color': '#280710',
        'width': 58,
        'height': 58,
      },
    },
    // Entity Types
    ...Object.entries(ENTITY_CONFIG).map(([type, cfg]) => ({
      selector: `node[type = "${type}"]`,
      style: {
        'shape': cfg.shape,
        'background-color': cfg.bg,
        'border-color': cfg.border,
        'width': cfg.size,
        'height': cfg.size,
      },
    })),
    // Selected Node State
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#38bdf8',
        'border-opacity': 1,
        'text-background-color': '#0c4a6e',
        'color': '#ffffff',
      },
    },
    // Base Edge — Clean, thin line, zero permanent text clutter
    {
      selector: 'edge',
      style: {
        'width': 1.6,
        'line-color': 'rgba(148, 163, 184, 0.25)',
        'target-arrow-color': 'rgba(148, 163, 184, 0.4)',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.85,
        'curve-style': 'bezier',
        'label': '',
        'transition-property': 'line-color, width, target-arrow-color',
        'transition-duration': '0.2s',
      },
    },
    // Attribution & Same-Actor Edges (Distinguished)
    {
      selector: 'edge[?is_attribution]',
      style: {
        'width': 2.8,
        'line-color': '#f59e0b',
        'target-arrow-color': '#f59e0b',
        'line-style': 'dashed',
        'line-dash-pattern': [6, 3],
        'arrow-scale': 1.1,
      },
    },
    // High-Confidence Edges
    {
      selector: 'edge[confidence >= 0.85]',
      style: {
        'line-color': 'rgba(168, 85, 247, 0.45)',
        'target-arrow-color': 'rgba(168, 85, 247, 0.65)',
      },
    },
    // Selected Edge
    {
      selector: 'edge:selected',
      style: {
        'width': 3.5,
        'line-color': '#38bdf8',
        'target-arrow-color': '#38bdf8',
        'z-index': 999,
      },
    },
    // Dimmed state during focus mode
    {
      selector: '.dimmed',
      style: {
        'opacity': 0.15,
      },
    },
    {
      selector: '.highlighted',
      style: {
        'opacity': 1.0,
      },
    },
  ];
}

const GraphUI = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const cyRef = useRef(null);
  const containerRef = useRef(null);

  // ── Data & Fetch State ────────────────────────────────────────────────────
  const [elements, setElements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState('Synthesizing threat intelligence graph...');
  const [error, setError] = useState(null);
  const [backendStats, setBackendStats] = useState(null);

  // ── Mode & Actors State ───────────────────────────────────────────────────
  const urlActorId = searchParams.get('actorId') ? parseInt(searchParams.get('actorId')) : null;
  const [graphMode, setGraphMode] = useState(urlActorId ? 'ACTOR_FOCUS' : 'GLOBAL');
  const [focusedActorId, setFocusedActorId] = useState(urlActorId || 1);
  const [multiActorIds, setMultiActorIds] = useState([1, 2]);
  const [actorsList, setActorsList] = useState([]);

  // Sync state if actorId URL search parameter changes
  useEffect(() => {
    if (urlActorId) {
      setGraphMode('ACTOR_FOCUS');
      setFocusedActorId(urlActorId);
    }
  }, [urlActorId]);

  // ── Investigation & Navigation State ──────────────────────────────────────
  const [depth, setDepth] = useState(2);
  const [layoutName, setLayoutName] = useState('cose');
  const [focusActorMode, setFocusActorMode] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  // ── Selection & Inspect State ─────────────────────────────────────────────
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [copiedText, setCopiedText] = useState(null);

  // ── Search & Filter State ─────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMatches, setSearchMatches] = useState([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);

  const [entityFilters, setEntityFilters] = useState({
    Actor: true,
    Handle: true,
    PGP: true,
    Wallet: true,
    Platform: true,
    OnionService: true,
    Domain: true,
    Infrastructure: true,
    Source: true,
  });

  const [relFilters, setRelFilters] = useState({
    Identifiers: true,
    Platforms: true,
    Infrastructure: true,
    Attribution: true,
  });

  const [confidenceFilter, setConfidenceFilter] = useState(0.0);

  // ── Fetch Actors List on Mount ────────────────────────────────────────────
  useEffect(() => {
    axios.get(`${API_BASE}/api/actors`)
      .then(res => {
        if (Array.isArray(res.data)) {
          setActorsList(res.data);
        }
      })
      .catch(err => console.error("Failed to load actors list:", err));
  }, []);

  // ── Load Graph Data ───────────────────────────────────────────────────────
  const fetchGraph = useCallback(async (overrideActorId, overrideDepth, overrideConf) => {
    setLoading(true);
    setLoadingMsg('Traversing threat intelligence graph & attribution links...');
    setError(null);
    try {
      const targetActor = overrideActorId !== undefined ? overrideActorId : focusedActorId;
      const targetDepth = overrideDepth !== undefined ? overrideDepth : depth;
      const targetConf = overrideConf !== undefined ? overrideConf : confidenceFilter;

      const params = { depth: targetDepth, confidence_min: targetConf };

      if (graphMode === 'ACTOR_FOCUS' && targetActor) {
        params.actor_id = targetActor;
      } else if (graphMode === 'MULTI_ACTOR' && multiActorIds.length > 0) {
        params.actor_ids = multiActorIds.join(',');
      }

      const res = await axios.get(`${API_BASE}/api/graph`, { params });
      let parsedElements = [];
      if (res.data) {
        if (res.data.elements && Array.isArray(res.data.elements)) {
          parsedElements = res.data.elements;
        } else if (Array.isArray(res.data)) {
          parsedElements = res.data;
        } else if (res.data.nodes || res.data.edges) {
          parsedElements = [
            ...(res.data.nodes || []),
            ...(res.data.edges || [])
          ];
        }
        if (res.data.stats) {
          setBackendStats(res.data.stats);
        }
      }
      setElements(parsedElements);
    } catch (err) {
      console.error('Failed to load graph data:', err);
      setError('Relationship graph unavailable. Ensure backend API is online.');
    } finally {
      setLoading(false);
    }
  }, [graphMode, focusedActorId, multiActorIds, depth, confidenceFilter]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // ── Layout Generator ──────────────────────────────────────────────────────
  const layoutConfig = useMemo(() => {
    if (layoutName === 'concentric') {
      return {
        name: 'concentric',
        concentric: function (node) {
          const d = node.data();
          if (d.is_primary) return 100;
          if (d.type === 'Actor') return 90;
          if (d.hop === 1 || ['Handle', 'PGP', 'Wallet'].includes(d.type)) return 60;
          if (['Platform', 'OnionService'].includes(d.type)) return 40;
          return 20;
        },
        levelWidth: () => 1,
        minNodeSpacing: 65,
        spacingFactor: 1.4,
        avoidOverlap: true,
        nodeDimensionsIncludeLabels: true,
        animate: true,
        animationDuration: 450,
      };
    }

    if (layoutName === 'cose') {
      return {
        name: 'cose',
        animate: false,
        fit: true,
        padding: 50,
        randomize: true,
        componentSpacing: 100,
        nodeRepulsion: () => 9000,
        nodeOverlap: 25,
        idealEdgeLength: (edge) => edge.data('is_attribution') ? 160 : 110,
        edgeElasticity: () => 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 400,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      };
    }

    // Breadthfirst (Hierarchical DAG)
    return {
      name: 'breadthfirst',
      directed: true,
      roots: focusedActorId ? [`#actor_${focusedActorId}`] : undefined,
      padding: 50,
      spacingFactor: 1.5,
      avoidOverlap: true,
      nodeDimensionsIncludeLabels: true,
      animate: true,
      animationDuration: 450,
    };
  }, [layoutName, focusedActorId]);

  // ── Setup Cytoscape Events & Binding ──────────────────────────────────────
  const handleCy = useCallback((cy) => {
    cyRef.current = cy;
    try {
      cy.resize();
    } catch (e) {
      // ignore
    }

    // Node click
    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data();
      setSelectedNode(nodeData);
      setSelectedEdge(null);
    });

    // Edge click
    cy.on('tap', 'edge', (evt) => {
      const edgeData = evt.target.data();
      setSelectedEdge(edgeData);
      setSelectedNode(null);
    });

    // Background click -> unselect
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
        setSelectedEdge(null);
      }
    });

    // Edge hover
    cy.on('mouseover', 'edge', (evt) => {
      const edge = evt.target;
      edge.addClass('hovered');
      setHoveredEdge({
        ...edge.data(),
        renderedPosition: evt.renderedPosition,
      });
    });

    cy.on('mouseout', 'edge', (evt) => {
      evt.target.removeClass('hovered');
      setHoveredEdge(null);
    });
  }, []);

  // ── Focus Actor Mode Dimming ──────────────────────────────────────────────
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;

    if (focusActorMode && focusedActorId) {
      const primaryNode = cy.$(`#actor_${focusedActorId}`);
      if (primaryNode.length > 0) {
        const neighborhood = primaryNode.neighborhood().add(primaryNode);
        cy.elements().removeClass('highlighted dimmed');
        cy.elements().difference(neighborhood).addClass('dimmed');
        neighborhood.addClass('highlighted');
      }
    } else {
      cy.elements().removeClass('highlighted dimmed');
    }
  }, [focusActorMode, focusedActorId, elements]);

  // ── Auto-Layout & Sizing Fix: Prevent nodes from stacking at (0, 0) ───────
  useEffect(() => {
    if (!cyRef.current || elements.length === 0) return;
    const cy = cyRef.current;
    const timer = setTimeout(() => {
      try {
        cy.resize();
        const l = cy.layout(layoutConfig);
        l.run();
        cy.fit(undefined, 50);
      } catch (e) {
        console.debug("Layout execution:", e);
      }
    }, 120);
    return () => clearTimeout(timer);
  }, [elements, layoutConfig]);

  // ── Filtered Elements Calculation ───────────────────────────────────────
  const filteredElements = useMemo(() => {
    if (!elements || elements.length === 0) return [];

    const visibleNodeIds = new Set();
    const nodes = [];

    // Filter nodes by entity type
    for (const el of elements) {
      if (!el.data?.source) {
        const type = el.data?.type;
        if (entityFilters[type] !== false) {
          visibleNodeIds.add(el.data.id);
          nodes.push(el);
        }
      }
    }

    // Filter edges: both endpoints must be visible, confidence and rel type must match
    const edges = [];
    for (const el of elements) {
      if (el.data?.source && el.data?.target) {
        if (!visibleNodeIds.has(el.data.source) || !visibleNodeIds.has(el.data.target)) {
          continue;
        }
        if (el.data.confidence !== undefined && el.data.confidence < confidenceFilter) {
          continue;
        }

        const isAttr = el.data.is_attribution || el.data.rel_type === 'POSSIBLY_SAME_ACTOR' || el.data.type === 'POSSIBLY_SAME_ACTOR';
        const isPlatform = el.data.rel_type === 'APPEARS_ON' || el.data.type === 'APPEARS_ON';
        const isInfra = ['HAS_INFRASTRUCTURE', 'ASSOCIATED_WITH_DOMAIN', 'HOSTED_ON'].includes(el.data.rel_type || el.data.type);
        const isIdent = ['USES_HANDLE', 'USES_PGP', 'ASSOCIATED_WITH_WALLET'].includes(el.data.rel_type || el.data.type);

        if (isAttr && !relFilters.Attribution) continue;
        if (isPlatform && !relFilters.Platforms) continue;
        if (isInfra && !relFilters.Infrastructure) continue;
        if (isIdent && !relFilters.Identifiers) continue;

        edges.push(el);
      }
    }

    return [...nodes, ...edges];
  }, [elements, entityFilters, relFilters, confidenceFilter]);

  // ── Search Autocomplete Logic ─────────────────────────────────────────────
  useEffect(() => {
    const nodes = filteredElements.filter(e => !e.data?.source);
    if (!searchQuery.trim() || nodes.length === 0) {
      setSearchMatches([]);
      setShowSearchDropdown(false);
      return;
    }

    const q = searchQuery.toLowerCase();
    const matches = nodes
      .map(n => n.data)
      .filter(d => (
        (d.label && d.label.toLowerCase().includes(q)) ||
        (d.full_value && d.full_value.toLowerCase().includes(q)) ||
        (d.type && d.type.toLowerCase().includes(q))
      ))
      .slice(0, 8);

    setSearchMatches(matches);
    setShowSearchDropdown(matches.length > 0);
  }, [searchQuery, filteredElements]);

  const selectSearchItem = (item) => {
    setShowSearchDropdown(false);
    setSearchQuery(item.label);
    if (!cyRef.current) return;
    const cy = cyRef.current;

    const node = cy.$(`#${item.id}`);
    if (node.length > 0) {
      cy.elements().unselect();
      node.select();
      setSelectedNode(item);
      setSelectedEdge(null);
      cy.animate({
        center: { eles: node },
        zoom: 1.25,
        duration: 450,
      });
    }
  };

  // ── Toolbar Actions ───────────────────────────────────────────────────────
  const handleFit = () => {
    if (cyRef.current) cyRef.current.fit(null, 50);
  };

  const handleCenter = () => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    if (selectedNode) {
      const node = cy.$(`#${selectedNode.id}`);
      if (node.length > 0) cy.center(node);
    } else if (focusedActorId) {
      const root = cy.$(`#actor_${focusedActorId}`);
      if (root.length > 0) cy.center(root);
    } else {
      cy.center();
    }
  };

  const handleResetLayout = () => {
    if (cyRef.current) {
      const l = cyRef.current.layout(layoutConfig);
      l.run();
    }
  };

  const toggleFullscreen = () => {
    setFullscreen(prev => !prev);
  };

  // Close details on escape
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setSelectedNode(null);
        setSelectedEdge(null);
        setFilterDrawerOpen(false);
        if (fullscreen) setFullscreen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [fullscreen]);

  const copyToClipboard = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  // Window resize handler to maintain cytoscape canvas dimensions
  useEffect(() => {
    const handleResize = () => {
      if (cyRef.current) {
        try {
          cyRef.current.resize();
        } catch (e) {}
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Re-run layout on element changes
  useEffect(() => {
    if (!cyRef.current || filteredElements.length === 0) return;
    const timer = setTimeout(() => {
      try {
        const cy = cyRef.current;
        cy.resize();
        const l = cy.layout(layoutConfig);
        l.run();
        cy.fit(null, 50);
      } catch (err) {
        console.warn('Cytoscape layout update error:', err);
      }
    }, 150);
    return () => clearTimeout(timer);
  }, [filteredElements, layoutName, layoutConfig]);

  // ── Render ────────────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    const nodes = filteredElements.filter(e => !e.data?.source);
    const edges = filteredElements.filter(e => e.data?.source);
    return {
      total_nodes: nodes.length,
      total_relationships: edges.length,
      actors: nodes.filter(n => n.data?.type === 'Actor').length,
      handles: nodes.filter(n => n.data?.type === 'Handle').length,
      wallets: nodes.filter(n => n.data?.type === 'Wallet').length,
      pgps: nodes.filter(n => n.data?.type === 'PGP').length,
      onion_services: nodes.filter(n => n.data?.type === 'OnionService').length,
      high_confidence_links: edges.filter(e => (e.data?.confidence || 0) >= 0.75).length,
    };
  }, [filteredElements]);
  const stylesheet = useMemo(() => createStylesheet(), []);

  return (
    <div
      ref={containerRef}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: fullscreen ? '100vh' : 'calc(100vh - 120px)',
        minHeight: fullscreen ? '100vh' : '650px',
        position: fullscreen ? 'fixed' : 'relative',
        inset: fullscreen ? 0 : 'auto',
        zIndex: fullscreen ? 99999 : 'auto',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        overflow: 'hidden',
      }}
    >
      {/* ── Top Header & Investigation Bar ───────────────────────────────── */}
      <div style={{ padding: fullscreen ? '14px 20px' : '0 0 14px 0', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ margin: 0, fontSize: '1.45rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
                Graph Intelligence
              </h1>
              {graphMode === 'GLOBAL' && (
                <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Globe size={12} /> GLOBAL GRAPH MODE ({stats.total_nodes} NODES)
                </span>
              )}
              {graphMode === 'ACTOR_FOCUS' && (
                <span className="badge badge-critical" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Shield size={12} /> FOCUS: Actor #{focusedActorId}
                </span>
              )}
              {graphMode === 'MULTI_ACTOR' && (
                <span className="badge badge-high" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Layers size={12} /> MULTI-ACTOR COMPARISON ({multiActorIds.length} ACTORS)
                </span>
              )}
            </div>
            <p style={{ color: 'var(--text-muted)', margin: '4px 0 0 0', fontSize: '0.84rem' }}>
              {graphMode === 'GLOBAL'
                ? 'Displaying global cross-actor network, shared infrastructure bridges & multi-hop threat clusters.'
                : `Focus investigation around selected threat actor across ${depth} hops.`}
            </p>
          </div>

          {/* ── Action Toolbar ───────────────────────────────────────────── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {/* Sync Button */}
            <button
              onClick={fetchGraph}
              disabled={loading}
              className="glass-card"
              style={{
                padding: '7px 11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.78rem',
                cursor: 'pointer',
                background: 'transparent',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
              title="Sync graph data"
            >
              <RefreshCw size={14} className={loading ? "spin" : ""} />
              Sync
            </button>

            {/* Mode Switcher Pill */}
            <div style={{
              display: 'flex',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '3px',
              gap: '2px',
            }}>
              <button
                onClick={() => { setGraphMode('GLOBAL'); setSearchParams({}); }}
                style={{
                  background: graphMode === 'GLOBAL' ? 'var(--accent-primary)' : 'transparent',
                  color: graphMode === 'GLOBAL' ? '#fff' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Global Graph
              </button>
              <button
                onClick={() => { setGraphMode('ACTOR_FOCUS'); }}
                style={{
                  background: graphMode === 'ACTOR_FOCUS' ? 'var(--accent-primary)' : 'transparent',
                  color: graphMode === 'ACTOR_FOCUS' ? '#fff' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Actor Focus
              </button>
              <button
                onClick={() => { setGraphMode('MULTI_ACTOR'); }}
                style={{
                  background: graphMode === 'MULTI_ACTOR' ? 'var(--accent-primary)' : 'transparent',
                  color: graphMode === 'MULTI_ACTOR' ? '#fff' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Compare Actors
              </button>
            </div>

            {/* Target Actor Selector when in Focus Mode */}
            {graphMode === 'ACTOR_FOCUS' && (
              <select
                value={focusedActorId}
                onChange={(e) => {
                  const aid = parseInt(e.target.value);
                  setFocusedActorId(aid);
                  setSearchParams({ actorId: aid });
                }}
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  color: '#fff',
                  fontSize: '0.78rem',
                  padding: '5px 8px',
                  cursor: 'pointer',
                }}
              >
                {actorsList.map(a => (
                  <option key={a.id} value={a.id} style={{ background: '#0d131f' }}>
                    {a.actor_name}
                  </option>
                ))}
              </select>
            )}

            {/* Multi-actor quick toggles */}
            {graphMode === 'MULTI_ACTOR' && (
              <div style={{ display: 'flex', gap: '4px' }}>
                {actorsList.slice(0, 4).map(a => {
                  const isSel = multiActorIds.includes(a.id);
                  return (
                    <button
                      key={a.id}
                      onClick={() => {
                        if (isSel) {
                          if (multiActorIds.length > 1) setMultiActorIds(multiActorIds.filter(x => x !== a.id));
                        } else {
                          setMultiActorIds([...multiActorIds, a.id]);
                        }
                      }}
                      style={{
                        background: isSel ? 'rgba(59, 130, 246, 0.25)' : 'rgba(255,255,255,0.04)',
                        border: isSel ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                        color: isSel ? '#fff' : 'var(--text-muted)',
                        borderRadius: '4px',
                        padding: '3px 7px',
                        fontSize: '0.72rem',
                        cursor: 'pointer',
                      }}
                    >
                      {isSel ? '✓ ' : '+ '}{a.actor_name}
                    </button>
                  );
                })}
              </div>
            )}
            {/* Search Input */}
            <div style={{ position: 'relative' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '6px 12px',
                width: '210px',
              }}>
                <Search size={14} color="var(--text-muted)" />
                <input
                  type="text"
                  placeholder="Search entities..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onFocus={() => { if (searchMatches.length > 0) setShowSearchDropdown(true); }}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    outline: 'none',
                    color: '#fff',
                    fontSize: '0.82rem',
                    width: '100%',
                  }}
                />
                {searchQuery && (
                  <X size={13} style={{ cursor: 'pointer' }} onClick={() => setSearchQuery('')} />
                )}
              </div>

              {/* Autocomplete Dropdown */}
              {showSearchDropdown && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  marginTop: '4px',
                  background: '#0d131f',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: '0 10px 25px -5px rgba(0,0,0,0.6)',
                  zIndex: 1000,
                  maxHeight: '260px',
                  overflowY: 'auto',
                }}>
                  {searchMatches.map((item) => {
                    const cfg = ENTITY_CONFIG[item.type] || ENTITY_CONFIG.Actor;
                    const Icon = cfg.icon;
                    return (
                      <div
                        key={item.id}
                        onClick={() => selectSearchItem(item)}
                        style={{
                          padding: '8px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          cursor: 'pointer',
                          borderBottom: '1px solid rgba(255,255,255,0.04)',
                          fontSize: '0.8rem',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: cfg.color }} />
                        <Icon size={13} color={cfg.color} />
                        <span style={{ fontWeight: 600, color: '#fff' }}>{item.label}</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                          {item.type}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Depth Selector */}
            <div style={{
              display: 'flex',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '3px',
              gap: '2px',
            }}>
              {[1, 2, 3].map((d) => (
                <button
                  key={d}
                  onClick={() => setDepth(d)}
                  style={{
                    background: depth === d ? 'var(--accent-primary)' : 'transparent',
                    color: depth === d ? '#fff' : 'var(--text-muted)',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 9px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  title={`Traverse ${d} hops from primary actor`}
                >
                  {d} {d === 1 ? 'hop' : 'hops'}
                </button>
              ))}
            </div>

            {/* Layout Selector */}
            <div style={{
              display: 'flex',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '3px',
              gap: '2px',
            }}>
              {[
                { id: 'concentric', label: 'Concentric' },
                { id: 'cose', label: 'Force (CoSE)' },
                { id: 'breadthfirst', label: 'DAG Tree' },
              ].map((l) => (
                <button
                  key={l.id}
                  onClick={() => setLayoutName(l.id)}
                  style={{
                    background: layoutName === l.id ? 'rgba(99,102,241,0.25)' : 'transparent',
                    color: layoutName === l.id ? '#a5b4fc' : 'var(--text-muted)',
                    border: layoutName === l.id ? '1px solid rgba(99,102,241,0.4)' : '1px solid transparent',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  {l.label}
                </button>
              ))}
            </div>

            {/* Focus Actor Toggle */}
            <button
              onClick={() => setFocusActorMode(prev => !prev)}
              className="glass-card"
              style={{
                padding: '7px 11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.78rem',
                cursor: 'pointer',
                background: focusActorMode ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                borderColor: focusActorMode ? '#ef4444' : 'var(--border-subtle)',
                color: focusActorMode ? '#f87171' : 'var(--text-secondary)',
              }}
              title="Highlight selected actor and 1-hop neighborhood"
            >
              <Crosshair size={14} />
              Focus Mode
            </button>

            {/* Filters Button */}
            <button
              onClick={() => setFilterDrawerOpen(prev => !prev)}
              className="glass-card"
              style={{
                padding: '7px 11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.78rem',
                cursor: 'pointer',
                background: filterDrawerOpen ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                borderColor: filterDrawerOpen ? 'var(--accent-primary)' : 'var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
            >
              <Filter size={14} />
              Filters
            </button>

            {/* Quick Canvas Buttons */}
            <button
              onClick={handleFit}
              className="glass-card"
              style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', cursor: 'pointer', background: 'transparent' }}
              title="Fit to view"
            >
              <Compass size={14} />
            </button>

            <button
              onClick={handleCenter}
              className="glass-card"
              style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', cursor: 'pointer', background: 'transparent' }}
              title="Center selected node"
            >
              <Crosshair size={14} />
            </button>

            <button
              onClick={handleResetLayout}
              className="glass-card"
              style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', cursor: 'pointer', background: 'transparent' }}
              title="Reset layout algorithm"
            >
              <RefreshCw size={14} />
            </button>

            <button
              onClick={toggleFullscreen}
              className="glass-card"
              style={{
                padding: '7px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                cursor: 'pointer',
                background: 'var(--accent-primary)',
                border: 'none',
                color: '#fff',
                fontWeight: 600,
                fontSize: '0.78rem',
              }}
            >
              {fullscreen ? <Minimize size={14} /> : <Maximize size={14} />}
              {fullscreen ? 'Exit' : 'Fullscreen'}
            </button>
          </div>
        </div>

        {/* ── Live Statistics Pills ────────────────────────────────────────── */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          marginTop: '10px',
          fontSize: '0.76rem',
          color: 'var(--text-secondary)',
          flexWrap: 'wrap',
        }}>
          <span><strong>{stats.total_nodes || elements.filter(e => !e.data.source).length}</strong> Nodes</span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span><strong>{stats.total_relationships || elements.filter(e => e.data.source).length}</strong> Relationships</span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span style={{ color: '#f87171' }}><strong>{stats.actors || 0}</strong> Actors</span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span style={{ color: '#38bdf8' }}><strong>{stats.handles || 0}</strong> Handles</span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span style={{ color: '#34d399' }}><strong>{stats.wallets || 0}</strong> Wallets</span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span style={{ color: '#c084fc' }}><strong>{stats.pgps || 0}</strong> PGP</span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span style={{ color: '#2dd4bf' }}><strong>{stats.onion_services || 0}</strong> Onions</span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span style={{ color: '#fbbf24' }}><strong>{stats.high_confidence_links || 0}</strong> High-Conf Links</span>
        </div>
      </div>

      {/* ── Main Graph Canvas & Overlays ─────────────────────────────────── */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', minHeight: '520px', width: '100%' }}>
        {/* Loading Spinner */}
        {loading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(8, 12, 20, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            gap: '12px',
          }}>
            <RefreshCw size={28} className="spin" color="var(--accent-primary)" />
            <span style={{ fontSize: '0.9rem', color: '#fff', fontWeight: 500 }}>{loadingMsg}</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 40,
            gap: '12px',
          }}>
            <AlertTriangle size={32} color="#ef4444" />
            <span style={{ color: '#f87171', fontSize: '0.95rem' }}>{error}</span>
            <button
              onClick={() => fetchGraph()}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                background: 'var(--accent-primary)',
                border: 'none',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredElements.length === 0 && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 30,
            gap: '10px',
          }}>
            <Database size={36} color="var(--text-muted)" />
            <span style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>NO RELATIONSHIPS FOUND</span>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Adjust your filters or select another threat actor investigation.
            </span>
          </div>
        )}

        {/* Cytoscape Canvas */}
        <CytoscapeComponent
          key={`${graphMode}-${focusedActorId}-${depth}`}
          elements={filteredElements}
          cy={handleCy}
          style={{
            width: '100%',
            height: '100%',
            minHeight: '520px',
            background: 'radial-gradient(circle, rgba(255,255,255,0.06) 1.2px, #080c14 1.2px)',
            backgroundSize: '24px 24px',
          }}
          stylesheet={stylesheet}
          layout={layoutConfig}
          minZoom={0.15}
          maxZoom={3.5}
        />

        {/* ── Hover Edge Tooltip ─────────────────────────────────────────── */}
        {hoveredEdge && (
          <div style={{
            position: 'absolute',
            top: (hoveredEdge.renderedPosition?.y || 0) + 12,
            left: (hoveredEdge.renderedPosition?.x || 0) + 12,
            background: 'rgba(13, 19, 31, 0.95)',
            border: '1px solid var(--border-medium)',
            borderRadius: '6px',
            padding: '6px 12px',
            fontSize: '0.74rem',
            color: '#fff',
            pointerEvents: 'none',
            zIndex: 80,
            boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
            backdropFilter: 'blur(8px)',
          }}>
            <div style={{ fontWeight: 700, color: hoveredEdge.is_attribution ? '#fbbf24' : '#38bdf8' }}>
              {hoveredEdge.label || hoveredEdge.type}
            </div>
            <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
              Confidence: {Math.round(hoveredEdge.confidence * 100)}% • {hoveredEdge.source_platform || 'Forensic telemetry'}
            </div>
          </div>
        )}

        {/* ── Floating Legend Overlay ────────────────────────────────────── */}
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(10, 15, 26, 0.88)',
          border: '1px solid var(--border-subtle)',
          backdropFilter: 'blur(10px)',
          boxShadow: '0 8px 25px rgba(0,0,0,0.4)',
          zIndex: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          fontSize: '0.74rem',
        }}>
          <div style={{ fontWeight: 700, color: '#fff', marginBottom: '2px', letterSpacing: '0.04em' }}>
            GRAPH LEGEND
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 14px' }}>
            {Object.entries(ENTITY_CONFIG).map(([type, cfg]) => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: cfg.shape === 'ellipse' ? '50%' : cfg.shape === 'diamond' ? '0' : '2px',
                  transform: cfg.shape === 'diamond' ? 'rotate(45deg)' : 'none',
                  background: cfg.color,
                }} />
                <span style={{ color: 'var(--text-secondary)' }}>{type}</span>
              </div>
            ))}
          </div>
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '6px', marginTop: '2px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
              <div style={{ width: 14, height: 2, background: '#f59e0b', borderTop: '1px dashed #f59e0b' }} />
              <span style={{ color: '#fbbf24' }}>Attribution (AI Match)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: 14, height: 2, background: 'rgba(148, 163, 184, 0.4)' }} />
              <span style={{ color: 'var(--text-muted)' }}>Identifier / Infra link</span>
            </div>
          </div>
        </div>

        {/* ── Right-Side Filter Drawer ───────────────────────────────────── */}
        {filterDrawerOpen && (
          <div style={{
            position: 'absolute',
            top: 0,
            right: 0,
            bottom: 0,
            width: '280px',
            background: 'rgba(10, 15, 26, 0.96)',
            borderLeft: '1px solid var(--border-medium)',
            backdropFilter: 'blur(16px)',
            zIndex: 70,
            display: 'flex',
            flexDirection: 'column',
            padding: '20px',
            overflowY: 'auto',
            boxShadow: '-10px 0 30px rgba(0,0,0,0.6)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#fff' }}>Filter Graph</span>
              <button
                onClick={() => setFilterDrawerOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Entity Types */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '10px' }}>
                Entity Types
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {Object.keys(entityFilters).map((type) => (
                  <label key={type} style={{ display: 'flex', alignItems: 'center', gap: '9px', fontSize: '0.82rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={entityFilters[type]}
                      onChange={(e) => setEntityFilters(prev => ({ ...prev, [type]: e.target.checked }))}
                    />
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: ENTITY_CONFIG[type]?.color || '#fff' }} />
                    <span style={{ color: entityFilters[type] ? '#fff' : 'var(--text-muted)' }}>{type}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Relationship Categories */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '10px' }}>
                Relationships
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {Object.keys(relFilters).map((cat) => (
                  <label key={cat} style={{ display: 'flex', alignItems: 'center', gap: '9px', fontSize: '0.82rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={relFilters[cat]}
                      onChange={(e) => setRelFilters(prev => ({ ...prev, [cat]: e.target.checked }))}
                    />
                    <span style={{ color: relFilters[cat] ? '#fff' : 'var(--text-muted)' }}>{cat}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Confidence Threshold */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '8px' }}>
                Confidence Threshold
              </div>
              <select
                value={confidenceFilter}
                onChange={(e) => setConfidenceFilter(parseFloat(e.target.value))}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.82rem',
                }}
              >
                <option value={0.0}>All Links (0%)</option>
                <option value={0.50}>Moderate (≥ 50%)</option>
                <option value={0.70}>High (≥ 70%)</option>
                <option value={0.85}>Very High (≥ 85%)</option>
              </select>
            </div>

            {/* Reset Filters */}
            <button
              onClick={() => {
                setEntityFilters(Object.keys(entityFilters).reduce((acc, k) => ({ ...acc, [k]: true }), {}));
                setRelFilters({ Identifiers: true, Platforms: true, Infrastructure: true, Attribution: true });
                setConfidenceFilter(0.0);
              }}
              style={{
                marginTop: 'auto',
                padding: '8px',
                borderRadius: '6px',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              Reset All Filters
            </button>
          </div>
        )}

        {/* ── Right-Side Node Entity Details Panel ────────────────────────── */}
        {selectedNode && (
          <div style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            bottom: '16px',
            width: '340px',
            background: 'rgba(10, 15, 26, 0.96)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            backdropFilter: 'blur(20px)',
            zIndex: 60,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            overflow: 'hidden',
          }}>
            {/* Panel Header */}
            <div style={{
              padding: '16px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
            }}>
              <div>
                <span style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: `${ENTITY_CONFIG[selectedNode.type]?.color || '#3b82f6'}20`,
                  color: ENTITY_CONFIG[selectedNode.type]?.color || '#3b82f6',
                  textTransform: 'uppercase',
                }}>
                  {selectedNode.type}
                </span>
                <h3 style={{ margin: '6px 0 0 0', fontSize: '1.15rem', fontWeight: 700, color: '#fff', wordBreak: 'break-all' }}>
                  {selectedNode.label}
                </h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Panel Body */}
            <div style={{ padding: '16px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Confidence Score (if available) */}
              {selectedNode.confidence !== undefined && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Confidence Assessment</span>
                    <span style={{ fontWeight: 700, color: '#38bdf8' }}>{Math.round(selectedNode.confidence * 100)}%</span>
                  </div>
                  <div className="confidence-bar">
                    <div className="confidence-bar-fill" style={{ width: `${selectedNode.confidence * 100}%` }} />
                  </div>
                </div>
              )}

              {/* Full Value with Copy */}
              {selectedNode.full_value && (
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Full Identifier</div>
                  <div style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.78rem',
                    color: '#cbd5e1',
                    wordBreak: 'break-all',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '6px',
                  }}>
                    <span>{selectedNode.full_value}</span>
                    <button
                      onClick={() => copyToClipboard(selectedNode.full_value)}
                      style={{ background: 'transparent', border: 'none', color: copiedText === selectedNode.full_value ? '#34d399' : 'var(--text-muted)', cursor: 'pointer' }}
                      title="Copy full identifier"
                    >
                      {copiedText === selectedNode.full_value ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                </div>
              )}

              {/* Entity Attributes */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
                {selectedNode.category && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Category</span>
                    <span style={{ color: '#fff', fontWeight: 500 }}>{selectedNode.category}</span>
                  </div>
                )}
                {selectedNode.status && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Status</span>
                    <span className="badge badge-low" style={{ fontSize: '0.7rem' }}>{selectedNode.status}</span>
                  </div>
                )}
                {selectedNode.blockchain && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Blockchain</span>
                    <span style={{ color: '#34d399', fontWeight: 600 }}>{selectedNode.blockchain}</span>
                  </div>
                )}
                {selectedNode.platform && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Platform</span>
                    <span style={{ color: '#fbbf24', fontWeight: 500 }}>{selectedNode.platform}</span>
                  </div>
                )}
                {selectedNode.actor_name && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Affiliated Actor</span>
                    <span style={{ color: '#f87171', fontWeight: 600 }}>{selectedNode.actor_name}</span>
                  </div>
                )}
                {selectedNode.first_seen && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>First Observed</span>
                    <span style={{ color: '#cbd5e1' }}>{selectedNode.first_seen.slice(0, 10)}</span>
                  </div>
                )}
                {selectedNode.last_seen && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Last Observed</span>
                    <span style={{ color: '#cbd5e1' }}>{selectedNode.last_seen.slice(0, 10)}</span>
                  </div>
                )}
              </div>

              {/* Description (if actor) */}
              {selectedNode.description && (
                <div style={{ marginTop: '6px' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Profile Notes</div>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
                    {selectedNode.description}
                  </p>
                </div>
              )}
            </div>

            {/* Panel Actions */}
            <div style={{
              padding: '14px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}>
              {selectedNode.type === 'Actor' ? (
                <>
                  <button
                    onClick={() => navigate(`/actors/${selectedNode.raw_id}`)}
                    style={{
                      padding: '9px 12px',
                      borderRadius: '6px',
                      background: 'var(--accent-primary)',
                      border: 'none',
                      color: '#fff',
                      fontWeight: 600,
                      fontSize: '0.82rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '7px',
                    }}
                  >
                    <Shield size={14} /> Open Full 15-Tab Dossier
                  </button>
                  <button
                    onClick={() => {
                      setGraphMode('ACTOR_FOCUS');
                      setFocusedActorId(selectedNode.raw_id);
                      setSearchParams({ actorId: selectedNode.raw_id });
                      setSelectedNode(null);
                    }}
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      background: 'rgba(255,255,255,0.08)',
                      border: '1px solid var(--border-subtle)',
                      color: '#fff',
                      fontWeight: 500,
                      fontSize: '0.82rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                    }}
                  >
                    <Crosshair size={14} /> Focus Graph on {selectedNode.label}
                  </button>
                  <button
                    onClick={() => navigate('/persona-analysis')}
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      background: 'transparent',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--text-secondary)',
                      fontSize: '0.82rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                    }}
                  >
                    <Sparkles size={14} /> Run Persona Analysis
                  </button>
                </>
              ) : (
                <button
                  onClick={() => {
                    if (cyRef.current) {
                      const node = cyRef.current.$(`#${selectedNode.id}`);
                      if (node.length > 0) cyRef.current.center(node);
                    }
                  }}
                  style={{
                    padding: '8px',
                    borderRadius: '6px',
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                  }}
                >
                  Center on Canvas
                </button>
              )}
            </div>
          </div>
        )}

        {/* ── Right-Side Relationship Details Panel ───────────────────────── */}
        {selectedEdge && (
          <div style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            bottom: '16px',
            width: '350px',
            background: 'rgba(10, 15, 26, 0.96)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            backdropFilter: 'blur(20px)',
            zIndex: 60,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            overflow: 'hidden',
          }}>
            {/* Edge Header */}
            <div style={{
              padding: '16px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
            }}>
              <div>
                <span style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: selectedEdge.is_attribution ? 'rgba(245, 158, 11, 0.18)' : 'rgba(56, 189, 248, 0.18)',
                  color: selectedEdge.is_attribution ? '#fbbf24' : '#38bdf8',
                  textTransform: 'uppercase',
                }}>
                  {selectedEdge.type}
                </span>
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px', color: '#fff', fontWeight: 700 }}>
                  <span>{selectedEdge.source.replace(/^actor_|^handle_|^wallet_|^pgp_|^onion_|^domain_/, '')}</span>
                  <ArrowRight size={14} color="var(--text-muted)" />
                  <span>{selectedEdge.target.replace(/^actor_|^handle_|^wallet_|^pgp_|^onion_|^domain_/, '')}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedEdge(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Edge Body */}
            <div style={{ padding: '16px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Confidence Score */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Attribution Confidence</span>
                  <span style={{ fontWeight: 700, color: selectedEdge.is_attribution ? '#fbbf24' : '#38bdf8' }}>
                    {Math.round(selectedEdge.confidence * 100)}% [{selectedEdge.confidence_level || 'HIGH'}]
                  </span>
                </div>
                <div className="confidence-bar">
                  <div
                    className="confidence-bar-fill"
                    style={{
                      width: `${selectedEdge.confidence * 100}%`,
                      background: selectedEdge.is_attribution ? 'linear-gradient(90deg, #f59e0b, #ef4444)' : undefined,
                    }}
                  />
                </div>
              </div>

              {/* Telemetry Source */}
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '0.78rem' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginBottom: '2px' }}>Intelligence Origin</div>
                <div style={{ color: '#fff', fontWeight: 500 }}>{selectedEdge.source_platform || 'Forensic Multi-Source'}</div>
              </div>

              {/* Positive Evidence Points */}
              {selectedEdge.positive_evidence && selectedEdge.positive_evidence.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: '#34d399', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <CheckCircle2 size={13} /> Positive Evidence
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {selectedEdge.positive_evidence.map((ev, idx) => (
                      <div
                        key={idx}
                        style={{
                          fontSize: '0.76rem',
                          background: 'rgba(52, 211, 153, 0.08)',
                          borderLeft: '2px solid #34d399',
                          padding: '6px 8px',
                          color: '#e2e8f0',
                        }}
                      >
                        {ev}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Negative Evidence Points */}
              {selectedEdge.negative_evidence && selectedEdge.negative_evidence.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: '#f87171', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <AlertTriangle size={13} /> Discrepancies / Negative Signals
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {selectedEdge.negative_evidence.map((nev, idx) => (
                      <div
                        key={idx}
                        style={{
                          fontSize: '0.76rem',
                          background: 'rgba(239, 68, 68, 0.08)',
                          borderLeft: '2px solid #ef4444',
                          padding: '6px 8px',
                          color: '#fca5a5',
                        }}
                      >
                        {nev}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Explanation Note */}
              {selectedEdge.explanation && (
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Forensic AI Rationale</div>
                  <div style={{
                    fontSize: '0.76rem',
                    color: 'var(--text-secondary)',
                    lineHeight: '1.4',
                    background: 'rgba(255,255,255,0.02)',
                    padding: '8px',
                    borderRadius: '4px',
                  }}>
                    {selectedEdge.explanation}
                  </div>
                </div>
              )}
            </div>

            {/* Edge Action Buttons */}
            <div style={{
              padding: '14px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}>
              {selectedEdge.is_attribution && (
                <button
                  onClick={() => navigate('/persona-analysis')}
                  style={{
                    padding: '8px',
                    borderRadius: '6px',
                    background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
                    border: 'none',
                    color: '#fff',
                    fontWeight: 600,
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                  }}
                >
                  <Sparkles size={14} /> Compare Personas in AI Pipeline
                </button>
              )}
              <button
                onClick={() => {
                  if (cyRef.current) {
                    const edge = cyRef.current.$(`#${selectedEdge.id}`);
                    if (edge.length > 0) cyRef.current.center(edge);
                  }
                }}
                style={{
                  padding: '8px',
                  borderRadius: '6px',
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid var(--border-subtle)',
                  color: '#fff',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                }}
              >
                Focus Edge on Canvas
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GraphUI;

