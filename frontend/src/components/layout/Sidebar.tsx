import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth, UserProfile } from '../../context/AuthContext';
import { DIRSLogo } from '../design-system';
import { 
  AlertTriangle, 
  MapPin, 
  Users, 
  Package, 
  Activity, 
  ShieldCheck, 
  Compass, 
  Cpu, 
  Layers, 
  Terminal, 
  LucideIcon,
  X
} from 'lucide-react';

export interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

interface SidebarNavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const { user } = useAuth();
  if (!user) return null;

  const roleNavItems: Record<UserProfile['role'], SidebarNavItem[]> = {
    CITIZEN: [
      { to: '/citizen', label: 'Citizen Dashboard', icon: Activity, badge: 'LIVE' },
      { to: '/citizen/report', label: 'Report Incident', icon: AlertTriangle },
      { to: '/citizen/shelters', label: 'Nearby Shelters', icon: MapPin },
    ],
    VOLUNTEER: [
      { to: '/volunteer', label: 'Volunteer Hub', icon: Users, badge: 'TASK' },
      { to: '/citizen/report', label: 'Report Hazard', icon: AlertTriangle },
      { to: '/citizen/shelters', label: 'Shelter Grid', icon: MapPin },
    ],
    NGO: [
      { to: '/ngo', label: 'Relief Inventory & Dispatch', icon: Package, badge: 'STOCK' },
      { to: '/citizen/shelters', label: 'Shelters', icon: MapPin },
    ],
    GOVT: [
      { to: '/admin', label: 'Command Center', icon: ShieldCheck, badge: 'HQ' },
      { to: '/admin/simulation', label: 'GIS & Simulation Lab', icon: Compass, badge: 'WHAT-IF' },
      { to: '/admin/recovery-optimization', label: 'Recovery Optimization', icon: Cpu, badge: 'MILP' },
      { to: '/citizen', label: 'Citizen Overview', icon: Activity },
      { to: '/volunteer', label: 'Responder Fleet', icon: Users },
      { to: '/ngo', label: 'NGO Relief Logistics', icon: Package },
    ],
    ADMIN: [
      { to: '/admin/recovery-optimization', label: 'Recovery Optimization', icon: Cpu, badge: 'MILP' },
    ],
  };

  const navs = roleNavItems[user.role] || roleNavItems.CITIZEN;

  const getRoleBadgeStyle = (role?: string) => {
    switch (role) {
      case 'ADMIN': return 'bg-amber-950/70 text-amber-400 border-amber-800/80';
      case 'GOVT': return 'bg-red-950/70 text-red-400 border-red-800/80';
      case 'NGO': return 'bg-purple-950/70 text-purple-300 border-purple-800/80';
      case 'VOLUNTEER': return 'bg-emerald-950/70 text-emerald-300 border-emerald-800/80';
      default: return 'bg-cyan-950/70 text-cyan-300 border-cyan-800/80';
    }
  };

  return (
    <aside
      className={`fixed top-0 left-0 h-screen h-[100dvh] w-60 z-40 md:z-30 border-r border-obsidian-700/80 bg-obsidian-900 flex flex-col justify-between p-3.5 select-none overflow-y-auto overflow-x-hidden transition-transform duration-200 ease-in-out ${
        isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0'
      }`}
    >
      <div className="space-y-6">
        {/* Top Branding & Role Indicator */}
        <div className="pb-3 mb-1 border-b border-obsidian-800/80">
          <div className="flex items-center justify-between px-1">
            <DIRSLogo size={36} />
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border tracking-wider uppercase ${getRoleBadgeStyle(user.role)}`}>
                {user.role}
              </span>
              {onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="p-1 rounded-lg text-slate-400 hover:text-white md:hidden"
                  aria-label="Close navigation"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        <div>
          <nav className="space-y-1">
            {navs.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-mono transition-all group ${
                      isActive
                        ? 'bg-obsidian-800 text-amber-ops font-semibold border-l-2 border-l-amber-ops border-y border-r border-obsidian-700 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-obsidian-850 hover:border-l-2 hover:border-l-obsidian-600'
                    }`
                  }
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon className="w-4 h-4 shrink-0 transition-colors group-hover:text-slate-200" />
                    <span className="truncate">{item.label}</span>
                  </div>

                  {item.badge && (
                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-obsidian-950 text-slate-400 border border-obsidian-800 shrink-0">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Engine Status Block */}
        <div className="px-2 space-y-2">
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 uppercase tracking-wider">
            <Terminal className="w-3 h-3 text-cyan-ops" />
            <span>SOLVER KERNEL</span>
          </div>
          <div className="p-2.5 rounded-lg bg-obsidian-950 border border-obsidian-800 space-y-1.5 text-[10px] font-mono">
            <div className="flex items-center justify-between text-slate-400">
              <span>Optimization:</span>
              <span className="text-emerald-400">CP-SAT OPTIMIZATION</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Spatial Graph:</span>
              <span className="text-cyan-ops">PostGIS SPATIAL INDEX</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span>Sandbox State:</span>
              <span className="text-amber-ops">SHA-256 Iso</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer System Telemetry */}
      <div className="bg-obsidian-950 p-2.5 rounded-lg border border-obsidian-800 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-[11px] font-mono font-medium text-slate-300">DIRS v5.2 Active</span>
        </div>
        <p className="text-[9px] font-mono text-slate-500 mt-1">
          Zero-Fabrication Data Guard Active
        </p>
      </div>
    </aside>
  );
};
