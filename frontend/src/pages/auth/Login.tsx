import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { 
  KeyRound, 
  Mail, 
  AlertCircle, 
  ArrowRight, 
  Activity, 
  Users, 
  Package, 
  ShieldCheck,
  Radio,
  Layers,
  Cpu
} from 'lucide-react';
import { DIRSLogo } from '../../components/design-system';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      redirectUser(user.role);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to authenticate. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const redirectUser = (role: string) => {
    switch (role) {
      case 'GOVT': navigate('/admin'); break;
      case 'VOLUNTEER': navigate('/volunteer'); break;
      case 'NGO': navigate('/ngo'); break;
      default: navigate('/citizen'); break;
    }
  };

  const quickLogin = async (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError('');
    setLoading(true);
    try {
      const user = await login(demoEmail, demoPass);
      redirectUser(user.role);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Demo login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-obsidian-950 flex text-slate-100 font-sans selection:bg-amber-ops selection:text-obsidian-950">
      {/* LEFT PANEL: Operational Visualization & Intelligence Grid */}
      <div className="hidden lg:flex lg:w-7/12 relative flex-col justify-between p-12 bg-obsidian-900 border-r border-obsidian-700/80 overflow-hidden bg-grid-pattern">
        {/* Ambient Topographic / Geo SVG Art */}
        <div className="absolute inset-0 pointer-events-none opacity-20 overflow-hidden">
          <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(245, 158, 11, 0.08)" strokeWidth="1" />
              </pattern>
              <radialGradient id="radar-glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.15" />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
              </radialGradient>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
            
            {/* Topographic Contours */}
            <circle cx="45%" cy="50%" r="280" fill="none" stroke="rgba(6, 182, 212, 0.15)" strokeWidth="1.5" strokeDasharray="6,6" />
            <circle cx="45%" cy="50%" r="200" fill="none" stroke="rgba(245, 158, 11, 0.2)" strokeWidth="1" />
            <circle cx="45%" cy="50%" r="120" fill="none" stroke="rgba(245, 158, 11, 0.3)" strokeWidth="1.5" />
            <circle cx="45%" cy="50%" r="40" fill="url(#radar-glow)" stroke="rgba(239, 68, 68, 0.5)" strokeWidth="2" />

            {/* Tactical Grid Vectors & Coordinate Markers */}
            <line x1="10%" y1="50%" x2="80%" y2="50%" stroke="rgba(255, 255, 255, 0.06)" strokeWidth="1" />
            <line x1="45%" y1="10%" x2="45%" y2="90%" stroke="rgba(255, 255, 255, 0.06)" strokeWidth="1" />

            {/* Incident Nodes with Simulated Pulse */}
            <g transform="translate(320, 240)">
              <circle r="4" fill="#ef4444" className="animate-ping" opacity="0.75" />
              <circle r="3" fill="#ef4444" />
              <text x="10" y="4" fill="#ef4444" fontSize="10" fontFamily="monospace">INC-2026-1024 [CRITICAL]</text>
            </g>
            <g transform="translate(480, 420)">
              <circle r="3" fill="#f59e0b" />
              <text x="10" y="4" fill="#f59e0b" fontSize="10" fontFamily="monospace">SHELTER_S-104 [ACTIVE]</text>
            </g>
            <g transform="translate(240, 520)">
              <circle r="3" fill="#06b6d4" />
              <text x="10" y="4" fill="#06b6d4" fontSize="10" fontFamily="monospace">DEPOT_CENTRAL [READY]</text>
            </g>
          </svg>
        </div>

        {/* Top Header Identity */}
        <div className="relative z-10">
          <DIRSLogo size={84} />
        </div>

        {/* Middle Intelligence Summary */}
        <div className="relative z-10 max-w-lg space-y-5 my-auto py-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-obsidian-850 border border-obsidian-700/80 text-[11px] font-mono text-cyan-ops">
            <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-ops" />
            <span>Chennai Metropolitan Coordinate Frame EPSG:4326</span>
          </div>

          <h1 className="text-3xl lg:text-4xl font-mono font-bold text-slate-100 leading-tight">
            Intelligent Emergency Operations Command Platform
          </h1>

          <p className="text-xs text-slate-400 font-sans leading-relaxed">
            Multi-modal situational awareness with mathematical resource allocation (PuLP LP), 
            capacitated fleet routing (CP-SAT VRP-TW), PostGIS spatial index matching, 
            and isolated SHA-256 predictive what-if simulation sandboxes.
          </p>

          <div className="grid grid-cols-3 gap-3 pt-4 font-mono">
            <div className="p-3 rounded-lg bg-obsidian-850/80 border border-obsidian-700/60">
              <p className="text-[10px] text-slate-400 uppercase">Optimization</p>
              <p className="text-sm font-bold text-amber-ops mt-0.5">CP-SAT OPTIMIZATION</p>
            </div>
            <div className="p-3 rounded-lg bg-obsidian-850/80 border border-obsidian-700/60">
              <p className="text-[10px] text-slate-400 uppercase">Spatial Engine</p>
              <p className="text-sm font-bold text-cyan-ops mt-0.5">PostGIS SPATIAL INDEX</p>
            </div>
            <div className="p-3 rounded-lg bg-obsidian-850/80 border border-obsidian-700/60">
              <p className="text-[10px] text-slate-400 uppercase">Governance</p>
              <p className="text-sm font-bold text-emerald-400 mt-0.5">HITL Authority</p>
            </div>
          </div>
        </div>

        {/* Bottom Operational Telemetry Footer */}
        <div className="relative z-10 flex items-center justify-between text-[11px] font-mono text-slate-400 border-t border-obsidian-800 pt-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>KNOWLEDGE BASE GROUNDED (NDMA / FEMA / WHO)</span>
          </div>
          <span className="text-slate-400">STATE ENCRYPTION: SHA-256</span>
        </div>
      </div>

      {/* RIGHT PANEL: Authentication & Quick Access */}
      <div className="w-full lg:w-5/12 flex flex-col justify-center px-6 sm:px-12 py-12 bg-obsidian-950">
        <div className="w-full max-w-md mx-auto space-y-7">
          {/* Header */}
          <div className="space-y-1.5">
            <div className="lg:hidden mb-4">
              <DIRSLogo size={48} />
            </div>
            <h2 className="text-xl font-mono font-bold text-slate-100 tracking-tight">
              OPERATIONAL AUTHENTICATION
            </h2>
            <p className="text-xs text-slate-400 font-sans">
              Enter authorized personnel credentials to access active emergency subsystems.
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-950/60 border border-red-800/80 rounded-lg flex items-center gap-2 text-xs text-red-300 font-mono">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-4 font-mono text-xs">
            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1.5">
                Personnel Identifier / Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@dirs.gov"
                  className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops focus:ring-1 focus:ring-amber-ops transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1.5">
                Security Password
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops focus:ring-1 focus:ring-amber-ops transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold py-2.5 rounded-lg transition flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-obsidian-950 border-t-transparent rounded-full animate-spin" />
                  <span>Validating Credentials...</span>
                </>
              ) : (
                <>
                  <span>AUTHENTICATE & ENTER COMMAND</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick One-Click Demo Access Cards */}
          <div className="pt-6 border-t border-obsidian-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono uppercase tracking-widest text-slate-500 font-semibold">
                DEMO COMMAND ACCESS
              </span>
              <span className="text-[9px] font-mono text-amber-ops bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-900">
                1-CLICK VERIFIED
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              {/* Govt Command */}
              <button
                type="button"
                onClick={() => quickLogin('admin@dirs.gov', 'Admin123!')}
                className="p-3 bg-obsidian-900 hover:bg-obsidian-850 border border-red-900/60 hover:border-red-700 rounded-lg text-left transition group space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="text-red-400 font-bold flex items-center gap-1.5 text-[11px]">
                    <ShieldCheck className="w-3.5 h-3.5 text-red-500" /> Govt Command
                  </span>
                  <span className="text-[9px] text-red-400/80">ADMIN</span>
                </div>
                <p className="text-[10px] text-slate-500 truncate">Situation HQ & RAG Review</p>
              </button>

              {/* Citizen Portal */}
              <button
                type="button"
                onClick={() => quickLogin('citizen@dirs.org', 'Citizen123!')}
                className="p-3 bg-obsidian-900 hover:bg-obsidian-850 border border-cyan-900/60 hover:border-cyan-700 rounded-lg text-left transition group space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-bold flex items-center gap-1.5 text-[11px]">
                    <Activity className="w-3.5 h-3.5 text-cyan-400" /> Citizen Portal
                  </span>
                  <span className="text-[9px] text-cyan-400/80">PUBLIC</span>
                </div>
                <p className="text-[10px] text-slate-500 truncate">Report & Shelter Finder</p>
              </button>

              {/* Volunteer Hub */}
              <button
                type="button"
                onClick={() => quickLogin('volunteer@dirs.org', 'Volunteer123!')}
                className="p-3 bg-obsidian-900 hover:bg-obsidian-850 border border-emerald-900/60 hover:border-emerald-700 rounded-lg text-left transition group space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="text-emerald-400 font-bold flex items-center gap-1.5 text-[11px]">
                    <Users className="w-3.5 h-3.5 text-emerald-400" /> Volunteer Hub
                  </span>
                  <span className="text-[9px] text-emerald-400/80">RESPOND</span>
                </div>
                <p className="text-[10px] text-slate-500 truncate">Rescue Tasks & Pipeline</p>
              </button>

              {/* NGO Relief */}
              <button
                type="button"
                onClick={() => quickLogin('ngo@dirs.org', 'Ngo123!')}
                className="p-3 bg-obsidian-900 hover:bg-obsidian-850 border border-purple-900/60 hover:border-purple-700 rounded-lg text-left transition group space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="text-purple-400 font-bold flex items-center gap-1.5 text-[11px]">
                    <Package className="w-3.5 h-3.5 text-purple-400" /> NGO Relief
                  </span>
                  <span className="text-[9px] text-purple-400/80">SUPPLY</span>
                </div>
                <p className="text-[10px] text-slate-500 truncate">Inventory & Dispatch</p>
              </button>
            </div>
          </div>

          <div className="text-center text-xs text-slate-500 font-sans">
            Need an operational account?{' '}
            <Link to="/register" className="text-amber-ops hover:underline font-mono">
              Register New Responder
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
