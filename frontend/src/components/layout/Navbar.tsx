import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { LogOut, User, Bell, Radio, Activity, Menu } from 'lucide-react';
import { Link } from 'react-router-dom';
import { DIRSLogo } from '../design-system';

export interface NavbarProps {
  onToggleSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar }) => {
  const { user, logout } = useAuth();
  const [timeUtc, setTimeUtc] = useState('');
  const [timeLocal, setTimeLocal] = useState('');

  useEffect(() => {
    const updateClocks = () => {
      const now = new Date();
      setTimeUtc(now.toUTCString().slice(17, 25) + ' UTC');
      setTimeLocal(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) + ' IST');
    };
    updateClocks();
    const interval = setInterval(updateClocks, 1000);
    return () => clearInterval(interval);
  }, []);

  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case 'GOVT': return 'bg-red-950/70 text-red-400 border-red-800/80';
      case 'NGO': return 'bg-purple-950/70 text-purple-300 border-purple-800/80';
      case 'VOLUNTEER': return 'bg-emerald-950/70 text-emerald-300 border-emerald-800/80';
      default: return 'bg-cyan-950/70 text-cyan-300 border-cyan-800/80';
    }
  };

  return (
    <header className="h-14 border-b border-obsidian-700/80 bg-obsidian-900/95 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20 select-none">
      {/* Left: Brand Symbol / Mobile Toggle */}
      <div className="flex items-center gap-2">
        {onToggleSidebar && (
          <button
            type="button"
            onClick={onToggleSidebar}
            className="p-1.5 rounded-lg bg-obsidian-850 hover:bg-obsidian-800 text-slate-300 hover:text-white border border-obsidian-700 md:hidden transition"
            aria-label="Toggle navigation menu"
          >
            <Menu className="w-4 h-4 text-slate-300" />
          </button>
        )}
        <Link to="/" className="flex items-center transition-opacity hover:opacity-90 md:hidden" title="DIRS Emergency Operations">
          <DIRSLogo variant="compact" />
        </Link>
      </div>

      {/* Center: Mission Telemetry & Synchronized Clocks */}
      <div className="hidden lg:flex items-center gap-4 text-xs font-mono text-slate-400">
        <div className="flex items-center gap-2 bg-obsidian-950 px-2.5 py-1 rounded border border-obsidian-700/60">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] text-slate-300 tracking-wider">POSTGIS / WEBSOCKET TELEMETRY: CONNECTED</span>
        </div>

        <div className="flex items-center gap-3 bg-obsidian-950 px-3 py-1 rounded border border-obsidian-700/60 text-[11px] tabular-nums">
          <span className="text-slate-400">{timeLocal}</span>
          <span className="text-obsidian-600">|</span>
          <span className="text-cyan-ops font-semibold">{timeUtc}</span>
        </div>
      </div>

      {/* Right: User Security Context & Actions */}
      <div className="flex items-center gap-3">
        {user ? (
          <>
            <div className="flex items-center gap-2.5 bg-obsidian-950 px-3 py-1 rounded-lg border border-obsidian-700/70">
              <div className="w-6 h-6 rounded-md bg-obsidian-800 border border-obsidian-700 flex items-center justify-center text-slate-400">
                <User className="w-3.5 h-3.5" />
              </div>
              <div className="text-right">
                <p className="font-mono font-medium text-xs text-slate-200 leading-tight">
                  {user.full_name}
                </p>
                <span className={`inline-block px-1.5 py-0.2 text-[9px] font-mono rounded border uppercase ${getRoleBadgeStyle(user.role)}`}>
                  {user.role}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              className="p-2 rounded-lg bg-obsidian-800 hover:bg-red-950/60 text-slate-400 hover:text-red-400 border border-obsidian-700 hover:border-red-800/60 transition flex items-center gap-1.5 text-xs font-mono"
              title="Terminate Security Session"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </>
        ) : (
          <div className="flex items-center gap-2">
            <Link 
              to="/login" 
              className="text-xs font-mono px-3 py-1.5 text-slate-300 hover:text-white bg-obsidian-800 hover:bg-obsidian-750 rounded-lg border border-obsidian-700 transition"
            >
              Sign In
            </Link>
            <Link 
              to="/register" 
              className="text-xs font-mono px-3.5 py-1.5 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded-lg transition"
            >
              Register
            </Link>
          </div>
        )}
      </div>
    </header>
  );
};
