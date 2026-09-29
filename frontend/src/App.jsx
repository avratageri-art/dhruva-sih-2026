import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { 
  Activity, Network, Clock, FileText, AlertTriangle, ShieldAlert, 
  Users, Search, Bell, Settings, Database, Server, Fingerprint, Map, 
  ActivitySquare, HardDrive, RefreshCw, Radio
} from 'lucide-react'
import axios from 'axios'

// Pages
import GraphUI from './pages/GraphUI'
import Timeline from './pages/Timeline'
import Reports from './pages/Reports'
import Alerts from './pages/Alerts'
import Actors from './pages/Actors'
import ActorProfile from './pages/ActorProfile'
import PersonaAnalysis from './pages/PersonaAnalysis'
import Infrastructure from './pages/Infrastructure'
import CrawlerMonitoring from './pages/CrawlerMonitoring'
import Models from './pages/Models'
import Architecture from './pages/Architecture'
import RobinSearch from './pages/RobinSearch'

// Dashboard Component
const Dashboard = () => {
  const [stats, setStats] = useState({
    actors: 0, handles: 0, services: 0, alerts: 0, observations: 0, high_confidence: 0
  })
  const [loading, setLoading] = useState(false)

  const fetchStats = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/dashboard')
      setStats(res.data)
    } catch (e) {
      console.error("Failed to fetch stats", e)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 10000) // Poll every 10s
    return () => clearInterval(interval)
  }, [])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>Command Center</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={fetchStats}
            disabled={loading}
            className="glass-card" 
            style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)', fontWeight: 500 }}>
            <RefreshCw size={18} className={loading ? "spin" : ""} /> {loading ? "Syncing..." : "Refresh Dash"}
          </button>
          <button 
            onClick={async () => {
              setLoading(true);
              try {
                await axios.post('/api/ingest/live');
                await fetchStats();
              } catch(e) { console.error(e) }
              setLoading(false);
            }}
            disabled={loading}
            className="glass-card" 
            style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', background: 'var(--accent-primary)', border: 'none', color: '#000', fontWeight: 600 }}>
            <ActivitySquare size={18} /> Fetch Live Intel
          </button>
        </div>
      </div>
      <div className="grid grid-cols-4">
        <div className="glass-card" style={{ padding: '20px' }}>
          <div className="stat-label">Tracked Actors</div>
          <div className="stat-value">{stats.actors}</div>
        </div>
        <div className="glass-card" style={{ padding: '20px' }}>
          <div className="stat-label">Correlated Handles</div>
          <div className="stat-value">{stats.handles}</div>
        </div>
        <div className="glass-card" style={{ padding: '20px' }}>
          <div className="stat-label">Monitored Services</div>
          <div className="stat-value">{stats.services}</div>
        </div>
        <div className="glass-card" style={{ padding: '20px', borderLeft: '3px solid var(--accent-secondary)' }}>
          <div className="stat-label" style={{ color: 'var(--accent-secondary)' }}>Critical Alerts</div>
          <div className="stat-value" style={{ color: 'var(--text-primary)' }}>{stats.alerts}</div>
        </div>
      </div>
      <div style={{ marginTop: '30px' }} className="grid grid-cols-2">
        <div className="glass-card">
          <div style={{ padding: '20px', borderBottom: '1px solid var(--border-color)' }}>
            <h3>Recent Intelligence Observations</h3>
          </div>
          <div style={{ padding: '20px', color: 'var(--text-secondary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span>Total Raw Observations:</span>
              <strong style={{color: 'white'}}>{stats.observations}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>High Confidence Attributions:</span>
              <strong style={{color: 'white'}}>{stats.high_confidence}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Placeholder Pages
const Investigations = () => <div className="p-6"><h1>Investigations</h1></div>
const SettingsPage = () => <div className="p-6"><h1>Settings</h1></div>

const NavItem = ({ to, icon: Icon, children }) => (
  <NavLink to={to} style={({isActive}) => ({
    padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '12px',
    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
    background: isActive ? 'rgba(255,255,255,0.08)' : 'transparent',
    borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent',
    fontSize: '0.9rem', fontWeight: isActive ? 600 : 400,
    marginBottom: '4px'
  })}>
    <Icon size={18} /> {children}
  </NavLink>
);

const Layout = ({ children }) => {
  return (
    <div className="app-container">
      {/* Sidebar */}
      <nav className="sidebar glass-panel" style={{ borderRight: '1px solid rgba(255,255,255,0.05)', width: '250px', padding: '0', overflowY: 'auto' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldAlert size={28} color="var(--accent-secondary)" />
            <div className="logo-text" style={{ fontSize: '1.25rem' }}>DHRU<span className="logo-accent">VA</span></div>
          </div>
        </div>
        
        <div style={{ padding: '15px 10px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '10px 0 5px 14px', letterSpacing: '0.1em' }}>Dashboard</div>
          <NavItem to="/" icon={Activity}>Command Center</NavItem>
          
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '20px 0 5px 14px', letterSpacing: '0.1em' }}>Investigate</div>
          <NavItem to="/investigations" icon={Search}>Investigations</NavItem>
          <NavItem to="/actors" icon={Users}>Actors</NavItem>
          <NavItem to="/persona-analysis" icon={Fingerprint}>Persona Analysis</NavItem>
          <NavItem to="/graph" icon={Network}>Graph Intelligence</NavItem>
          <NavItem to="/timeline" icon={Clock}>Timeline</NavItem>
          
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '20px 0 5px 14px', letterSpacing: '0.1em' }}>Intelligence</div>
          <NavItem to="/infrastructure" icon={Server}>Infrastructure</NavItem>
          <NavItem to="/crawler" icon={Database}>Darknet Collection</NavItem>
          <NavItem to="/robin" icon={Radio}>Robin Web Search</NavItem>
          
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '20px 0 5px 14px', letterSpacing: '0.1em' }}>Operations</div>
          <NavItem to="/alerts" icon={AlertTriangle}>Alerts</NavItem>
          <NavItem to="/reports" icon={FileText}>Reports</NavItem>
          
          <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '20px 0 5px 14px', letterSpacing: '0.1em' }}>System</div>
          <NavItem to="/models" icon={ActivitySquare}>AI Models</NavItem>
          <NavItem to="/architecture" icon={HardDrive}>Architecture</NavItem>
          <NavItem to="/settings" icon={Settings}>Settings</NavItem>
        </div>
      </nav>
      
      {/* Main Content */}
      <main className="main-content">
        {/* Topbar */}
        <header className="header glass-panel" style={{ borderRadius: 0, borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Workspace: <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>Global Threat Intelligence</span>
            </div>
            <div className="badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              ANALYST WORKSPACE
            </div>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input 
                type="text" 
                placeholder="Global Search..." 
                style={{ 
                  background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', 
                  borderRadius: '20px', padding: '6px 15px 6px 35px', color: 'var(--text-primary)',
                  outline: 'none', fontSize: '0.85rem', width: '250px'
                }} 
              />
            </div>
            
            <Bell size={20} color="var(--text-secondary)" style={{ cursor: 'pointer' }} />
            
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', background: 'rgba(0,0,0,0.2)', padding: '6px 12px', borderRadius: '20px', border: '1px solid var(--border-color)' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 8px var(--success)' }}></div>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>System Online</span>
            </div>
            
            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold', fontSize: '0.9rem', cursor: 'pointer' }}>
              A1
            </div>
          </div>
        </header>
        
        {/* Page Content */}
        <div className="content-scroll">
          {children}
        </div>
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/investigations" element={<Investigations />} />
          <Route path="/actors" element={<Actors />} />
          <Route path="/actors/:id" element={<ActorProfile />} />
          <Route path="/persona-analysis" element={<PersonaAnalysis />} />
          <Route path="/graph" element={<GraphUI />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/infrastructure" element={<Infrastructure />} />
          <Route path="/crawler" element={<CrawlerMonitoring />} />
          <Route path="/sources" element={<CrawlerMonitoring />} />
          <Route path="/robin" element={<RobinSearch />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/models" element={<Models />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
