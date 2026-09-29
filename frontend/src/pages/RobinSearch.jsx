import React, { useState, useEffect, useRef } from 'react';
import {
  Search, Wifi, WifiOff, Globe, Shield, Hash, Activity,
  Clock, CheckCircle, AlertCircle, Loader, Database,
  Download, Link, User, Mail, Bitcoin, Key, ChevronDown,
  ChevronRight, ChevronUp, RefreshCw, Zap, Eye, Server, Radio,
  Copy, Check, ExternalLink, FileText, Layers, Filter, Sliders, List
} from 'lucide-react';
import axios from 'axios';

const API = 'http://localhost:8000';

// ── Copy Button Helper ────────────────────────────────────────────────────────
function CopyButton({ text, label = 'Copy', minimal = false }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = (e) => {
    e.stopPropagation();
    if (!text) return;
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (minimal) {
    return (
      <button
        type="button"
        onClick={handleCopy}
        title={copied ? 'Copied to clipboard!' : 'Copy to clipboard'}
        style={{
          background: copied ? 'rgba(16,185,129,0.25)' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${copied ? 'var(--success)' : 'rgba(255,255,255,0.15)'}`,
          color: copied ? 'var(--success)' : 'var(--text-muted)',
          borderRadius: '4px',
          padding: '2px 6px',
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '3px',
          fontSize: '0.7rem',
          transition: 'all 0.15s ease',
        }}
      >
        {copied ? <Check size={11} /> : <Copy size={11} />}
        {copied && <span>Copied!</span>}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copied ? 'Copied to clipboard!' : 'Copy to clipboard'}
      style={{
        background: copied ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.06)',
        border: `1px solid ${copied ? 'var(--success)' : 'rgba(255,255,255,0.15)'}`,
        color: copied ? 'var(--success)' : 'var(--text-secondary)',
        borderRadius: '6px',
        padding: '4px 10px',
        fontSize: '0.75rem',
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        transition: 'all 0.15s ease',
      }}
    >
      {copied ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
      <span>{copied ? 'Copied!' : label}</span>
    </button>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const map = {
    queued:    { cls: 'badge-neutral',  label: 'Queued' },
    searching: { cls: 'badge-info',     label: 'Searching…' },
    scraping:  { cls: 'badge-medium',   label: 'Scraping…' },
    done:      { cls: 'badge-low',      label: 'Done' },
    error:     { cls: 'badge-critical', label: 'Error' },
  };
  const s = map[status] || { cls: 'badge-neutral', label: status };
  return <span className={`badge ${s.cls}`}>{s.label}</span>;
}

// ── Intelligence Taxonomy & Categorization Definition ─────────────────────────
const ENTITY_CATEGORIES = [
  {
    id: 'financial',
    label: 'Financial & Cryptocurrency Identifiers',
    shortLabel: 'Financial & Crypto',
    icon: Bitcoin,
    themeColor: '#f59e0b',
    whatAreThey: 'Blockchain payment addresses detected in scraped dark web pages and extortion notes. Threat actors, darknet markets, and ransomware syndicates publish these addresses to receive ransom extortion payouts, escrow deposits, and illicit payments.',
    types: [
      {
        key: 'btc_wallets',
        name: 'Bitcoin (BTC) Wallets',
        icon: Bitcoin,
        color: '#f59e0b',
        bgColor: 'rgba(245, 158, 11, 0.12)',
        borderColor: 'rgba(245, 158, 11, 0.35)',
        whatIsThis: 'Public Bitcoin blockchain addresses. Transparent and traceable across public ledgers, enabling transaction graph mapping and cluster attribution.',
      },
      {
        key: 'xmr_wallets',
        name: 'Monero (XMR) Wallets',
        icon: Hash,
        color: '#10b981',
        bgColor: 'rgba(16, 185, 129, 0.12)',
        borderColor: 'rgba(16, 185, 129, 0.35)',
        whatIsThis: 'Privacy-centric cryptocurrency stealth addresses. Obfuscates sender, receiver, and transaction amounts. Heavily favored by ransomware gangs for untraceable extortion.',
      },
    ],
  },
  {
    id: 'identity',
    label: 'Threat Actor Personas & Communications',
    shortLabel: 'Identities & Comms',
    icon: User,
    themeColor: '#8b5cf6',
    whatAreThey: 'Digital identities, aliases, and operational communication channels used by threat actors to negotiate with victims, coordinate cybercrime operations, or publish leak announcements.',
    types: [
      {
        key: 'handles',
        name: 'Threat Actor Handles / Aliases',
        icon: User,
        color: '#a78bfa',
        bgColor: 'rgba(167, 139, 250, 0.12)',
        borderColor: 'rgba(167, 139, 250, 0.35)',
        whatIsThis: 'Operator usernames and handles observed across darknet forums, leak boards, and victim communication portals.',
      },
      {
        key: 'emails',
        name: 'Contact Email Addresses',
        icon: Mail,
        color: '#38bdf8',
        bgColor: 'rgba(56, 189, 248, 0.12)',
        borderColor: 'rgba(56, 189, 248, 0.35)',
        whatIsThis: 'Direct communication email addresses (e.g. Mail2Tor, ProtonMail, OnionMail) cited for ransom negotiations and proof-of-life requests.',
      },
      {
        key: 'telegram',
        name: 'Telegram Channels & Handles',
        icon: Radio,
        color: '#29b5e8',
        bgColor: 'rgba(41, 181, 232, 0.12)',
        borderColor: 'rgba(41, 181, 232, 0.35)',
        whatIsThis: 'Instant messaging handles and channel links used for decentralized victim negotiation and data release mirrors.',
      },
      {
        key: 'pgp_fingerprints',
        name: 'PGP Key Fingerprints',
        icon: Key,
        color: '#ec4899',
        bgColor: 'rgba(236, 72, 153, 0.12)',
        borderColor: 'rgba(236, 72, 153, 0.35)',
        whatIsThis: '40-character OpenPGP public key fingerprints used by threat actors to digitally sign extortion notices and verify authenticity.',
      },
    ],
  },
  {
    id: 'infrastructure',
    label: 'Darknet Infrastructure & Hidden Services',
    shortLabel: 'Darknet Infrastructure',
    icon: Globe,
    themeColor: '#3b82f6',
    whatAreThey: 'Tor V3 hidden service (.onion) endpoints and network locators discovered within page hyperlinks and source HTML. These represent adversary infrastructure, active leak portals, mirrors, or C2 nodes.',
    types: [
      {
        key: 'onion_addresses',
        name: 'Tor Hidden Services (.onion)',
        icon: Globe,
        color: '#60a5fa',
        bgColor: 'rgba(96, 165, 250, 0.12)',
        borderColor: 'rgba(96, 165, 250, 0.35)',
        whatIsThis: 'Active or referenced .onion hidden services discovered during the crawl. Includes victim leak portals, affiliate panels, mirror sites, and adversary communications nodes.',
      },
    ],
  },
];

// ── Categorized Entity Section Component ───────────────────────────────────────
function CategorizedEntitiesSection({ allEntities }) {
  const [activeCategoryTab, setActiveCategoryTab] = useState('all');
  const [expandedTypes, setExpandedTypes] = useState({});
  const [searchTerms, setSearchTerms] = useState({});

  if (!allEntities || Object.keys(allEntities).length === 0) {
    return (
      <div className="glass-card" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        No entities extracted from scraped pages.
      </div>
    );
  }

  // Count entities in each category
  const categoryCounts = {};
  let totalEntitiesCount = 0;
  ENTITY_CATEGORIES.forEach(cat => {
    let catCount = 0;
    cat.types.forEach(t => {
      const items = allEntities[t.key] || [];
      catCount += items.length;
    });
    categoryCounts[cat.id] = catCount;
    totalEntitiesCount += catCount;
  });

  const toggleExpandType = (key) => {
    setExpandedTypes(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleCopyAll = (items, label) => {
    if (!items || items.length === 0) return;
    navigator.clipboard?.writeText(items.join('\n'));
    alert(`Copied ${items.length} ${label} to clipboard!`);
  };

  const filteredCategories = activeCategoryTab === 'all'
    ? ENTITY_CATEGORIES.filter(cat => categoryCounts[cat.id] > 0)
    : ENTITY_CATEGORIES.filter(cat => cat.id === activeCategoryTab && categoryCounts[cat.id] > 0);

  return (
    <div className="glass-card" style={{ padding: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={17} color="var(--accent-primary)" />
            Categorized Threat Intelligence Entities
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            All discovered entities are grouped under distinct intelligence families with context on what they represent.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-info" style={{ fontSize: '0.8rem' }}>
            {totalEntitiesCount} Total Entities
          </span>
          <span className="badge badge-neutral" style={{ fontSize: '0.8rem' }}>
            {Object.keys(allEntities).length} Entity Types
          </span>
        </div>
      </div>

      {/* Category Navigation Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '12px' }}>
        <button
          type="button"
          onClick={() => setActiveCategoryTab('all')}
          style={{
            padding: '6px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '0.82rem', fontWeight: 600,
            background: activeCategoryTab === 'all' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.04)',
            border: `1px solid ${activeCategoryTab === 'all' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.1)'}`,
            color: activeCategoryTab === 'all' ? '#fff' : 'var(--text-secondary)',
            display: 'flex', alignItems: 'center', gap: '6px',
            transition: 'all 0.15s ease'
          }}
        >
          <Layers size={13} />
          All Categories ({totalEntitiesCount})
        </button>

        {ENTITY_CATEGORIES.map(cat => {
          const Icon = cat.icon;
          const count = categoryCounts[cat.id] || 0;
          if (count === 0) return null;
          const isActive = activeCategoryTab === cat.id;
          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => setActiveCategoryTab(cat.id)}
              style={{
                padding: '6px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '0.82rem', fontWeight: 600,
                background: isActive ? `${cat.themeColor}22` : 'rgba(255,255,255,0.04)',
                border: `1px solid ${isActive ? cat.themeColor : 'rgba(255,255,255,0.1)'}`,
                color: isActive ? cat.themeColor : 'var(--text-secondary)',
                display: 'flex', alignItems: 'center', gap: '6px',
                transition: 'all 0.15s ease'
              }}
            >
              <Icon size={13} color={isActive ? cat.themeColor : 'var(--text-muted)'} />
              {cat.shortLabel} ({count})
            </button>
          );
        })}
      </div>

      {/* Render Category Blocks */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {filteredCategories.map(cat => {
          const CatIcon = cat.icon;
          return (
            <div
              key={cat.id}
              style={{
                borderRadius: '10px',
                background: 'rgba(255,255,255,0.015)',
                border: `1px solid rgba(255,255,255,0.08)`,
                overflow: 'hidden',
              }}
            >
              {/* Category Explanation Banner */}
              <div style={{
                padding: '14px 18px',
                background: `${cat.themeColor}12`,
                borderBottom: `1px solid ${cat.themeColor}28`,
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
              }}>
                <div style={{
                  padding: '8px', borderRadius: '8px',
                  background: `${cat.themeColor}25`,
                  border: `1px solid ${cat.themeColor}40`,
                  color: cat.themeColor,
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <CatIcon size={18} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff' }}>
                      {cat.label}
                    </span>
                    <span style={{
                      padding: '2px 8px', borderRadius: '10px', fontSize: '0.72rem', fontWeight: 600,
                      background: `${cat.themeColor}20`, color: cat.themeColor, border: `1px solid ${cat.themeColor}40`
                    }}>
                      {categoryCounts[cat.id]} items detected
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
                    <strong style={{ color: 'var(--text-primary)' }}>What are they: </strong>
                    {cat.whatAreThey}
                  </div>
                </div>
              </div>

              {/* Sub-types inside this Category */}
              <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {cat.types.map(typeDef => {
                  const rawItems = allEntities[typeDef.key] || [];
                  if (rawItems.length === 0) return null;

                  const TypeIcon = typeDef.icon;
                  const isExpanded = expandedTypes[typeDef.key] ?? false;
                  const searchTerm = searchTerms[typeDef.key] || '';
                  const filteredItems = searchTerm
                    ? rawItems.filter(item => String(item).toLowerCase().includes(searchTerm.toLowerCase()))
                    : rawItems;
                  const displayItems = isExpanded ? filteredItems : filteredItems.slice(0, 6);

                  return (
                    <div
                      key={typeDef.key}
                      style={{
                        padding: '14px 16px',
                        borderRadius: '8px',
                        background: 'rgba(0,0,0,0.25)',
                        border: '1px solid rgba(255,255,255,0.06)',
                      }}
                    >
                      {/* Sub-type Header */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px', marginBottom: '10px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <TypeIcon size={14} color={typeDef.color} />
                            <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#fff' }}>
                              {typeDef.name}
                            </span>
                            <span style={{
                              padding: '1px 7px', borderRadius: '10px', fontSize: '0.72rem',
                              background: typeDef.bgColor, color: typeDef.color, border: `1px solid ${typeDef.borderColor}`,
                              fontFamily: 'var(--font-mono)'
                            }}>
                              {rawItems.length}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '3px' }}>
                            {typeDef.whatIsThis}
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {rawItems.length > 8 && (
                            <div style={{ position: 'relative' }}>
                              <Search size={12} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                              <input
                                type="text"
                                placeholder={`Filter ${typeDef.name}…`}
                                value={searchTerm}
                                onChange={e => setSearchTerms(prev => ({ ...prev, [typeDef.key]: e.target.value }))}
                                style={{
                                  padding: '3px 8px 3px 24px', fontSize: '0.75rem',
                                  background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-color)',
                                  borderRadius: '6px', color: 'var(--text-primary)', width: '140px', outline: 'none'
                                }}
                              />
                            </div>
                          )}
                          <button
                            type="button"
                            onClick={() => handleCopyAll(rawItems, typeDef.name)}
                            style={{
                              padding: '3px 8px', borderRadius: '5px', fontSize: '0.72rem',
                              background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)',
                              color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                            }}
                          >
                            <Copy size={11} /> Copy All ({rawItems.length})
                          </button>
                        </div>
                      </div>

                      {/* Items Pill Grid */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
                        {displayItems.map((val, idx) => (
                          <div
                            key={idx}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '4px 10px',
                              borderRadius: '6px',
                              fontSize: '0.78rem',
                              fontFamily: 'var(--font-mono)',
                              background: typeDef.bgColor,
                              border: `1px solid ${typeDef.borderColor}`,
                              color: typeDef.color,
                              maxWidth: '100%',
                              wordBreak: 'break-all',
                            }}
                          >
                            <TypeIcon size={12} style={{ flexShrink: 0 }} />
                            <span style={{ color: '#fff', userSelect: 'all' }}>{String(val)}</span>
                            <CopyButton text={String(val)} minimal={true} />
                          </div>
                        ))}
                      </div>

                      {/* Show More / Show Less Toggle Button */}
                      {filteredItems.length > 6 && (
                        <div style={{ marginTop: '10px', textAlign: 'left' }}>
                          <button
                            type="button"
                            onClick={() => toggleExpandType(typeDef.key)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: typeDef.color,
                              fontSize: '0.78rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '4px 0',
                            }}
                          >
                            {isExpanded ? (
                              <>
                                <ChevronUp size={13} />
                                Show Less (collapse to 6)
                              </>
                            ) : (
                              <>
                                <ChevronDown size={13} />
                                Expand &amp; View All {filteredItems.length} {typeDef.name}
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Expandable Scraped Page Card ──────────────────────────────────────────────
function ExpandableScrapedPage({ page, index, initialOpen = false }) {
  const [isOpen, setIsOpen] = useState(initialOpen);

  useEffect(() => {
    setIsOpen(initialOpen);
  }, [initialOpen]);

  const pageEntities = page.entities || {};
  const pageText = page.text || '(No text content returned for this hidden service)';
  const totalEntitiesOnPage = page.entity_count || Object.values(pageEntities).reduce((acc, v) => acc + (Array.isArray(v) ? v.length : 0), 0);
  const isSuccess = page.status === 'success';

  return (
    <div
      style={{
        borderRadius: '8px',
        background: isOpen ? 'rgba(255,255,255,0.035)' : 'rgba(255,255,255,0.015)',
        border: `1px solid ${isOpen ? 'var(--accent-primary)45' : 'var(--border-color)'}`,
        transition: 'all 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Clickable Accordion Header */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '12px 14px',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          userSelect: 'none',
          background: isOpen ? 'rgba(99,102,241,0.06)' : 'transparent',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0, marginRight: '10px' }}>
          <span style={{ color: isOpen ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
            {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </span>

          <div style={{
            width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
            background: isSuccess ? 'var(--success)' : 'var(--danger)',
            boxShadow: isSuccess ? '0 0 6px var(--success)' : '0 0 6px var(--danger)'
          }} />

          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: '0.86rem', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {page.title || '(Untitled Onion Service)'}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-secondary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: '1px' }}>
              🧅 {page.url}
            </div>
          </div>
        </div>

        {/* Right Header Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          {page.engine && (
            <span className="badge badge-info" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
              {page.engine}
            </span>
          )}
          <span style={{
            padding: '1px 6px', borderRadius: '8px', fontSize: '0.68rem',
            background: totalEntitiesOnPage > 0 ? 'rgba(245,158,11,0.12)' : 'rgba(255,255,255,0.05)',
            color: totalEntitiesOnPage > 0 ? '#f59e0b' : 'var(--text-muted)',
            border: `1px solid ${totalEntitiesOnPage > 0 ? 'rgba(245,158,11,0.3)' : 'rgba(255,255,255,0.1)'}`,
            fontFamily: 'var(--font-mono)'
          }}>
            {totalEntitiesOnPage} ent.
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--accent-primary)', fontWeight: 600 }}>
            {isOpen ? '▴' : '▾'}
          </span>
        </div>
      </div>

      {/* Expanded Accordion Body */}
      {isOpen && (
        <div style={{ padding: '0 14px 14px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          {/* Metadata Strip */}
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center',
            padding: '8px 12px', margin: '12px 0 10px',
            background: 'rgba(0,0,0,0.35)', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)',
            fontSize: '0.74rem'
          }}>
            <div style={{ flex: 1, minWidth: '220px', wordBreak: 'break-all' }}>
              <span style={{ color: 'var(--text-muted)' }}>URL: </span>
              <span style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>{page.url}</span>
              <span style={{ marginLeft: '6px' }}><CopyButton text={page.url} minimal={true} /></span>
            </div>
            {page.engine && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Engine: </span>
                <span style={{ color: 'var(--info)', fontWeight: 600 }}>{page.engine}</span>
              </div>
            )}
            <div>
              <span style={{ color: 'var(--success)', fontWeight: 600 }}>🛡 Tor Route Active</span>
            </div>
          </div>

          {/* Extracted Entities on this page */}
          {Object.keys(pageEntities).length > 0 ? (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Hash size={12} color="var(--accent-primary)" />
                Page Extracted Entities:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                {Object.entries(pageEntities).map(([typeKey, vals]) => {
                  if (!Array.isArray(vals) || vals.length === 0) return null;
                  return vals.map((v, vIdx) => (
                    <span
                      key={`${typeKey}-${vIdx}`}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '5px',
                        fontSize: '0.72rem',
                        fontFamily: 'var(--font-mono)',
                        background: 'rgba(99,102,241,0.12)',
                        border: '1px solid rgba(99,102,241,0.3)',
                        color: '#c7d2fe',
                        maxWidth: '100%',
                        wordBreak: 'break-all'
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>{typeKey}:</span>
                      <strong style={{ color: '#fff' }}>{String(v)}</strong>
                      <CopyButton text={String(v)} minimal={true} />
                    </span>
                  ));
                })}
              </div>
            </div>
          ) : (
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '10px', fontStyle: 'italic' }}>
              No discrete wallet or identity entities extracted from this page.
            </div>
          )}

          {/* Raw Scraped Page Text Viewer */}
          <div style={{ marginTop: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <FileText size={12} color="var(--info)" />
                Scraped Content ({pageText.length} chars):
              </span>
              <CopyButton text={pageText} label="Copy Text" minimal={true} />
            </div>

            <pre
              style={{
                margin: 0,
                padding: '10px 12px',
                borderRadius: '6px',
                background: 'rgba(0,0,0,0.55)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#e2e8f0',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                lineHeight: 1.45,
                maxHeight: '220px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                userSelect: 'text',
              }}
            >
              {pageText}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Job row ────────────────────────────────────────────────────────────────────
function JobRow({ job, onSelect, selected }) {
  return (
    <div
      onClick={() => onSelect(job.job_id)}
      style={{
        padding: '10px 14px', cursor: 'pointer', borderRadius: '8px',
        background: selected ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.02)',
        border: `1px solid ${selected ? 'var(--accent-primary)50' : 'var(--border-color)'}`,
        marginBottom: '6px', transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, fontSize: '0.85rem', color: selected ? 'var(--accent-primary)' : 'var(--text-primary)' }}>
          "{job.query}"
        </span>
        <StatusBadge status={job.status} />
      </div>
      <div style={{ display: 'flex', gap: '10px', marginTop: '4px', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
        <span><Globe size={11} style={{ verticalAlign: 'middle' }} /> {job.search_results_count || 0} links</span>
        <span><Eye size={11} style={{ verticalAlign: 'middle' }} /> {job.pages_scraped || 0} scraped</span>
        <span><Database size={11} style={{ verticalAlign: 'middle' }} /> {job.observations_count || 0} obs</span>
        {job.elapsed_seconds && <span>⏱ {job.elapsed_seconds}s</span>}
      </div>
    </div>
  );
}

// ── Main RobinSearch Page ──────────────────────────────────────────────────────
export default function RobinSearch() {
  const [query, setQuery] = useState('');
  const [numEngines, setNumEngines] = useState(3);
  const [maxPages, setMaxPages] = useState(5);
  const [useTor, setUseTor] = useState(true);
  const [launching, setLaunching] = useState(false);

  // Left panel view mode: 'jobs' | 'options' | 'engines'
  const [leftNavMode, setLeftNavMode] = useState('jobs');

  const [robinStatus, setRobinStatus] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [engines, setEngines] = useState({ onion_engines: [], clearnet_engines: [] });

  // Accordion state for scraped pages (in the left column)
  const [allPagesExpanded, setAllPagesExpanded] = useState(false);
  const [pageSearchFilter, setPageSearchFilter] = useState('');

  // Search results filter (in right column)
  const [resultFilter, setResultFilter] = useState('');

  const pollRef = useRef(null);

  // ── Fetch Robin status and jobs ──────────────────────────────────────────────
  const fetchStatus = async () => {
    try {
      const [statusRes, jobsRes] = await Promise.all([
        axios.get(`${API}/api/crawler/robin/status`),
        axios.get(`${API}/api/crawler/robin/jobs`),
      ]);
      setRobinStatus(statusRes.data);
      const jobsList = jobsRes.data.jobs || [];
      setJobs(jobsList);

      // Auto-select first job if none selected
      if (!selectedJobId && jobsList.length > 0) {
        setSelectedJobId(jobsList[0].job_id);
      }
    } catch (e) { /* ignore */ }
  };

  const fetchEngines = async () => {
    try {
      const res = await axios.get(`${API}/api/crawler/robin/engines`);
      setEngines(res.data);
    } catch (e) { /* ignore */ }
  };

  const fetchSelectedJob = async (id) => {
    if (!id) return;
    try {
      const res = await axios.get(`${API}/api/crawler/robin/jobs/${id}`);
      setSelectedJob(res.data);
    } catch (e) { /* ignore */ }
  };

  useEffect(() => {
    fetchStatus();
    fetchEngines();
    pollRef.current = setInterval(() => {
      fetchStatus();
      if (selectedJobId) fetchSelectedJob(selectedJobId);
    }, 3000); // Poll every 3s for real-time updates
    return () => clearInterval(pollRef.current);
  }, [selectedJobId]);

  const handleSelectJob = (id) => {
    setSelectedJobId(id);
    fetchSelectedJob(id);
  };

  // ── Launch search ────────────────────────────────────────────────────────────
  const launchSearch = async () => {
    if (!query.trim()) return;
    setLaunching(true);
    try {
      const res = await axios.post(`${API}/api/crawler/robin/search`, {
        query: query.trim(),
        num_engines: numEngines,
        max_pages: maxPages,
        use_tor: useTor,
      });
      const jobId = res.data.job_id;
      setSelectedJobId(jobId);
      setLeftNavMode('jobs');
      setQuery('');
      await fetchStatus();
    } catch (e) {
      alert('Search failed: ' + (e.response?.data?.detail || e.message));
    }
    setLaunching(false);
  };

  // ── Ingest job into DB ───────────────────────────────────────────────────────
  const ingestJob = async (jobId) => {
    try {
      const res = await axios.post(`${API}/api/crawler/robin/jobs/${jobId}/ingest`);
      alert(`✅ Ingested: ${res.data.observations_created} new observations created (${res.data.duplicates_skipped} duplicates skipped)`);
    } catch (e) {
      alert('Ingest failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const torUp = robinStatus?.tor_available;
  const runningJobs = jobs.filter(j => ['queued', 'searching', 'scraping'].includes(j.status));

  // Filtered scraped pages
  const rawScrapedPages = selectedJob?.scraped_pages || [];
  const filteredScrapedPages = pageSearchFilter
    ? rawScrapedPages.filter(p =>
        (p.title || '').toLowerCase().includes(pageSearchFilter.toLowerCase()) ||
        (p.url || '').toLowerCase().includes(pageSearchFilter.toLowerCase()) ||
        (p.text || '').toLowerCase().includes(pageSearchFilter.toLowerCase())
      )
    : rawScrapedPages;

  // Filtered search results
  const rawSearchResults = selectedJob?.search_results || [];
  const filteredSearchResults = resultFilter
    ? rawSearchResults.filter(r =>
        (r.title || '').toLowerCase().includes(resultFilter.toLowerCase()) ||
        (r.link || '').toLowerCase().includes(resultFilter.toLowerCase()) ||
        (r.snippet || '').toLowerCase().includes(resultFilter.toLowerCase())
      )
    : rawSearchResults;

  return (
    <div style={{ padding: '24px', maxWidth: '1680px', margin: '0 auto' }}>

      {/* ── Top Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.7rem' }}>Robin Dark Web Search</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
            AI-powered OSINT scraper · {robinStatus?.total_engines || 16} onion search engines
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {/* Tor status badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '6px 14px', borderRadius: '20px',
            background: torUp ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
            border: `1px solid ${torUp ? 'var(--success)' : 'var(--warning)'}40`,
            color: torUp ? 'var(--success)' : 'var(--warning)',
            fontSize: '0.82rem', fontWeight: 600,
          }}>
            {torUp ? <Wifi size={14} /> : <WifiOff size={14} />}
            {torUp ? 'Tor Active' : 'Clearnet Fallback (Ahmia)'}
          </div>

          {runningJobs.length > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '6px 14px', borderRadius: '20px',
              background: 'rgba(99,102,241,0.12)', border: '1px solid var(--accent-primary)40',
              color: 'var(--accent-primary)', fontSize: '0.82rem', fontWeight: 600,
            }}>
              <Loader size={14} className="spin" />
              {runningJobs.length} job{runningJobs.length > 1 ? 's' : ''} running
            </div>
          )}

          <button
            onClick={fetchStatus}
            title="Refresh status"
            style={{
              background: 'transparent', border: '1px solid var(--border-color)', padding: '7px 11px',
              borderRadius: '8px', cursor: 'pointer', color: 'var(--text-secondary)'
            }}
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* ── Top Stat Bar ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '20px' }}>
        {[
          { label: 'Total Engines', value: robinStatus?.total_engines || 16, icon: <Globe size={16} />, color: 'var(--accent-primary)' },
          { label: 'Total Jobs', value: robinStatus?.total_jobs || jobs.length, icon: <Database size={16} />, color: 'var(--info)' },
          { label: 'Completed', value: robinStatus?.completed_jobs || jobs.filter(j => j.status === 'done').length, icon: <CheckCircle size={16} />, color: 'var(--success)' },
          { label: 'Failed', value: robinStatus?.failed_jobs || jobs.filter(j => j.status === 'error').length, icon: <AlertCircle size={16} />, color: 'var(--danger)' },
        ].map(s => (
          <div key={s.label} className="glass-card" style={{ padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div className="stat-label">{s.label}</div>
              <div className="stat-value" style={{ color: s.color, marginTop: '2px' }}>{s.value}</div>
            </div>
            <span style={{ color: s.color, opacity: 0.7 }}>{s.icon}</span>
          </div>
        ))}
      </div>

      {/* ── 2-Column Balanced Dashboard Layout ── */}
      {/* LEFT COLUMN: Search & Jobs Controls (Top) + Scraped Pages Accordion (Bottom) */}
      {/* RIGHT COLUMN: Selected Job Header + Stats + Categorized Intelligence + Search Results */}
      <div style={{ display: 'grid', gridTemplateColumns: '430px 1fr', gap: '20px', alignItems: 'start' }}>

        {/* ══════════════ LEFT COLUMN ══════════════ */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* 1. Compact Search & Job Selector Control Card */}
          <div className="glass-card" style={{ padding: '16px' }}>
            {/* Quick Search Bar */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && launchSearch()}
                  placeholder="Search Dark Web (e.g. ransomware)…"
                  style={{
                    width: '100%', padding: '8px 10px 8px 30px', boxSizing: 'border-box',
                    background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
                    borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.84rem',
                    outline: 'none',
                  }}
                />
              </div>
              <button
                onClick={launchSearch}
                disabled={!query.trim() || launching}
                style={{
                  padding: '0 14px', borderRadius: '6px', cursor: 'pointer',
                  background: launching || !query.trim() ? 'rgba(99,102,241,0.3)' : 'var(--accent-primary)',
                  border: 'none', color: '#fff', fontWeight: 600, fontSize: '0.84rem',
                  display: 'flex', alignItems: 'center', gap: '5px',
                  opacity: !query.trim() ? 0.5 : 1, flexShrink: 0
                }}
              >
                {launching ? <Loader size={13} className="spin" /> : <Zap size={13} />}
                Search
              </button>
            </div>

            {/* Sub-nav Mode Pills: Recent Jobs | Search Config | Engines */}
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '8px' }}>
              <button
                type="button"
                onClick={() => setLeftNavMode('jobs')}
                style={{
                  padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.76rem', fontWeight: 600,
                  background: leftNavMode === 'jobs' ? 'rgba(99,102,241,0.2)' : 'transparent',
                  border: `1px solid ${leftNavMode === 'jobs' ? 'var(--accent-primary)50' : 'transparent'}`,
                  color: leftNavMode === 'jobs' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}
              >
                <List size={12} />
                Recent Jobs ({jobs.length})
              </button>

              <button
                type="button"
                onClick={() => setLeftNavMode('options')}
                style={{
                  padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.76rem', fontWeight: 600,
                  background: leftNavMode === 'options' ? 'rgba(99,102,241,0.2)' : 'transparent',
                  border: `1px solid ${leftNavMode === 'options' ? 'var(--accent-primary)50' : 'transparent'}`,
                  color: leftNavMode === 'options' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}
              >
                <Sliders size={12} />
                Search Config
              </button>

              <button
                type="button"
                onClick={() => setLeftNavMode('engines')}
                style={{
                  padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.76rem', fontWeight: 600,
                  background: leftNavMode === 'engines' ? 'rgba(99,102,241,0.2)' : 'transparent',
                  border: `1px solid ${leftNavMode === 'engines' ? 'var(--accent-primary)50' : 'transparent'}`,
                  color: leftNavMode === 'engines' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  display: 'flex', alignItems: 'center', gap: '4px'
                }}
              >
                <Globe size={12} />
                Engines ({engines.onion_engines?.length || 16})
              </button>
            </div>

            {/* Mode Content: Recent Jobs */}
            {leftNavMode === 'jobs' && (
              <div>
                {jobs.length === 0 ? (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', padding: '14px 0' }}>
                    No search jobs launched yet.
                  </div>
                ) : (
                  <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
                    {jobs.map(j => (
                      <JobRow key={j.job_id} job={j} onSelect={handleSelectJob} selected={j.job_id === selectedJobId} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Mode Content: Search Config */}
            {leftNavMode === 'options' && (
              <div style={{ padding: '6px 0' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                  <div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '3px' }}>Query Engines</div>
                    <select value={numEngines} onChange={e => setNumEngines(+e.target.value)}
                      style={{ width: '100%', padding: '6px', background: 'rgba(0,0,0,0.3)',
                               border: '1px solid var(--border-color)', borderRadius: '6px',
                               color: 'var(--text-primary)', fontSize: '0.8rem' }}>
                      {[1,2,3,5,8].map(n => <option key={n} value={n}>{n} engine{n>1?'s':''}</option>)}
                    </select>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '3px' }}>Pages to Scrape</div>
                    <select value={maxPages} onChange={e => setMaxPages(+e.target.value)}
                      style={{ width: '100%', padding: '6px', background: 'rgba(0,0,0,0.3)',
                               border: '1px solid var(--border-color)', borderRadius: '6px',
                               color: 'var(--text-primary)', fontSize: '0.8rem' }}>
                      {[1,2,3,5,10].map(n => <option key={n} value={n}>{n} page{n>1?'s':''}</option>)}
                    </select>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input type="checkbox" id="use-tor-chk" checked={useTor} onChange={e => setUseTor(e.target.checked)}
                    style={{ cursor: 'pointer' }} />
                  <label htmlFor="use-tor-chk" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                    Route through Tor {!torUp && <span style={{ color: 'var(--warning)', fontSize: '0.72rem' }}>(offline — fallback)</span>}
                  </label>
                </div>
              </div>
            )}

            {/* Mode Content: Search Engines List */}
            {leftNavMode === 'engines' && (
              <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                  {torUp ? '🟢 Tor Active — querying .onion search indices' : '🟡 Clearnet Fallback mode'}
                </div>
                {(torUp ? engines.onion_engines : engines.clearnet_engines)?.map(e => (
                  <div key={e.name} style={{
                    padding: '5px 8px', marginBottom: '4px', borderRadius: '5px',
                    background: 'rgba(255,255,255,0.03)', fontSize: '0.74rem',
                    color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
                  }}>
                    <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{e.name}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem', marginLeft: '6px' }}>{e.url.slice(0, 36)}…</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 2. Scraped Pages Section (Placed on the Left to Eliminate Vertical Scrolling!) */}
          <div className="glass-card" style={{ padding: '16px' }}>
            {/* Scraped Pages Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '0.96rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Eye size={15} color="var(--info)" />
                  Scraped Pages ({selectedJob?.scraped_pages?.length || 0})
                </h3>
                <p style={{ margin: '2px 0 0', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                  Click any page to expand text &amp; entities.
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {/* Search filter for scraped pages */}
                <div style={{ position: 'relative' }}>
                  <Filter size={11} style={{ position: 'absolute', left: '7px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    placeholder="Filter…"
                    value={pageSearchFilter}
                    onChange={e => setPageSearchFilter(e.target.value)}
                    style={{
                      padding: '3px 8px 3px 22px', fontSize: '0.74rem',
                      background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-color)',
                      borderRadius: '5px', color: 'var(--text-primary)', width: '90px', outline: 'none'
                    }}
                  />
                </div>

                {/* Expand All / Collapse All Toggle */}
                {selectedJob?.scraped_pages?.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setAllPagesExpanded(!allPagesExpanded)}
                    title={allPagesExpanded ? 'Collapse All Pages' : 'Expand All Pages'}
                    style={{
                      padding: '4px 8px', borderRadius: '5px', fontSize: '0.72rem', fontWeight: 600,
                      background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)',
                      color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                    }}
                  >
                    {allPagesExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    {allPagesExpanded ? 'Collapse' : 'Expand All'}
                  </button>
                )}
              </div>
            </div>

            {/* Scraped Pages List */}
            {!selectedJob ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Select a job above or launch a search to view scraped pages.
              </div>
            ) : filteredScrapedPages.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {pageSearchFilter ? `No pages match "${pageSearchFilter}"` : 'No pages scraped yet for this job.'}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '720px', overflowY: 'auto' }}>
                {filteredScrapedPages.map((p, i) => (
                  <ExpandableScrapedPage
                    key={`${p.url}-${i}`}
                    page={p}
                    index={i}
                    initialOpen={allPagesExpanded}
                  />
                ))}
              </div>
            )}
          </div>

        </div>

        {/* ══════════════ RIGHT COLUMN ══════════════ */}
        <div>
          {!selectedJob ? (
            <div className="glass-card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Search size={40} style={{ opacity: 0.3, marginBottom: '12px' }} />
              <div>Select a job on the left or launch a new search</div>
              <div style={{ fontSize: '0.8rem', marginTop: '8px', opacity: 0.6 }}>
                Robin will query {robinStatus?.total_engines || 16} dark web search engines and scrape results in real time
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>

              {/* Job Header & Telemetry Card */}
              <div className="glass-card" style={{ padding: '18px 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '4px', color: '#fff' }}>
                      "{selectedJob.query}"
                    </div>
                    <div style={{ display: 'flex', gap: '14px', fontSize: '0.8rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                      <span>Job: <code style={{ color: 'var(--accent-primary)' }}>{selectedJob.job_id}</code></span>
                      {selectedJob.started_at && (
                        <span><Clock size={12} style={{ verticalAlign: 'middle', marginRight: '3px' }} /> {new Date(selectedJob.started_at).toLocaleTimeString()}</span>
                      )}
                      {selectedJob.elapsed_seconds && <span>⏱ {selectedJob.elapsed_seconds}s</span>}
                      {selectedJob.tor_used && <span style={{ color: 'var(--success)' }}>🛡 Tor Circuit</span>}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <StatusBadge status={selectedJob.status} />
                    {selectedJob.status === 'done' && (
                      <button
                        onClick={() => ingestJob(selectedJob.job_id)}
                        style={{
                          padding: '6px 14px', borderRadius: '8px', cursor: 'pointer',
                          background: 'rgba(16,185,129,0.15)', border: '1px solid var(--success)40',
                          color: 'var(--success)', fontSize: '0.82rem', fontWeight: 600,
                          display: 'flex', alignItems: 'center', gap: '6px',
                        }}
                      >
                        <Download size={13} /> Ingest to DB
                      </button>
                    )}
                    <button onClick={() => fetchSelectedJob(selectedJob.job_id)}
                      title="Refresh job details"
                      style={{ background: 'transparent', border: '1px solid var(--border-color)',
                               padding: '6px 9px', borderRadius: '6px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                      <RefreshCw size={13} />
                    </button>
                  </div>
                </div>

                {/* Running state notice */}
                {['searching', 'scraping', 'queued'].includes(selectedJob.status) && (
                  <div style={{ marginTop: '14px', padding: '10px 14px', borderRadius: '8px',
                                background: 'rgba(99,102,241,0.08)', border: '1px solid var(--accent-primary)30',
                                display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: 'var(--accent-primary)' }}>
                    <Loader size={15} className="spin" />
                    {selectedJob.status === 'searching' && 'Querying dark web search engines in real time…'}
                    {selectedJob.status === 'scraping' && `Scraping discovered onion pages through Tor circuit…`}
                    {selectedJob.status === 'queued' && 'Job queued — starting soon…'}
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>(auto-refreshing every 3s)</span>
                  </div>
                )}

                {/* Error state */}
                {selectedJob.status === 'error' && (
                  <div style={{ marginTop: '12px', padding: '10px 14px', borderRadius: '8px',
                                background: 'rgba(239,68,68,0.08)', border: '1px solid var(--danger)30',
                                fontSize: '0.85rem', color: 'var(--danger)' }}>
                    ❌ {selectedJob.error}
                  </div>
                )}
              </div>

              {/* Stats Row */}
              {selectedJob.status === 'done' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                  {[
                    { label: 'Links Found', value: selectedJob.search_results_count || 0, color: 'var(--accent-primary)' },
                    { label: 'Pages Scraped', value: selectedJob.pages_scraped || 0, color: 'var(--info)' },
                    { label: 'Observations', value: selectedJob.observations?.length || 0, color: 'var(--success)' },
                    { label: 'Entity Types', value: Object.keys(selectedJob.all_entities || {}).length, color: 'var(--warning)' },
                  ].map(s => (
                    <div key={s.label} className="glass-card" style={{ padding: '14px 16px', textAlign: 'center' }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: s.color }}>{s.value}</div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '2px' }}>{s.label}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Categorized Threat Intelligence Entities */}
              {selectedJob.all_entities && Object.keys(selectedJob.all_entities).length > 0 && (
                <CategorizedEntitiesSection allEntities={selectedJob.all_entities} />
              )}

              {/* Search Results (Links Found across engines) */}
              {selectedJob.search_results?.length > 0 && (
                <div className="glass-card" style={{ padding: '18px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '0.98rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Link size={15} color="var(--accent-primary)" />
                        Search Results ({selectedJob.search_results.length} links found)
                      </h3>
                      <p style={{ margin: '3px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                        Onion links returned by engines matching "{selectedJob.query}".
                      </p>
                    </div>

                    <div style={{ position: 'relative' }}>
                      <Filter size={11} style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      <input
                        type="text"
                        placeholder="Filter links…"
                        value={resultFilter}
                        onChange={e => setResultFilter(e.target.value)}
                        style={{
                          padding: '4px 10px 4px 24px', fontSize: '0.76rem',
                          background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-color)',
                          borderRadius: '5px', color: 'var(--text-primary)', width: '150px', outline: 'none'
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ maxHeight: '300px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {filteredSearchResults.map((r, i) => (
                      <div
                        key={i}
                        style={{
                          padding: '9px 12px', borderRadius: '7px',
                          background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: '0.83rem', color: '#fff', marginBottom: '2px' }}>
                              {r.title || '(Untitled Darknet Link)'}
                            </div>
                            <div style={{ fontSize: '0.73rem', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              🧅 {r.link}
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                            <span className="badge badge-info" style={{ fontSize: '0.68rem' }}>via {r.engine}</span>
                            <CopyButton text={r.link} minimal={true} />
                          </div>
                        </div>

                        {r.snippet && (
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: 1.35 }}>
                            {r.snippet}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>

      </div>
    </div>
  );
}
