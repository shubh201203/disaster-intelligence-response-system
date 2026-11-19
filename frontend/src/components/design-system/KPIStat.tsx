import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KPIStatProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: LucideIcon;
  variant?: 'critical' | 'high' | 'amber' | 'cyan' | 'emerald' | 'neutral';
  delta?: {
    value: string;
    isPositive?: boolean;
    label?: string;
  };
  className?: string;
}

export const KPIStat: React.FC<KPIStatProps> = ({
  label,
  value,
  subtext,
  icon: Icon,
  variant = 'neutral',
  delta,
  className = ''
}) => {
  const variantMap = {
    critical: {
      accent: 'border-l-red-500',
      valueColor: 'text-red-400',
      iconColor: 'text-red-500',
      iconBg: 'bg-red-500/10 border-red-500/20'
    },
    high: {
      accent: 'border-l-orange-500',
      valueColor: 'text-orange-400',
      iconColor: 'text-orange-500',
      iconBg: 'bg-orange-500/10 border-orange-500/20'
    },
    amber: {
      accent: 'border-l-amber-500',
      valueColor: 'text-amber-400',
      iconColor: 'text-amber-500',
      iconBg: 'bg-amber-500/10 border-amber-500/20'
    },
    cyan: {
      accent: 'border-l-cyan-500',
      valueColor: 'text-cyan-400',
      iconColor: 'text-cyan-500',
      iconBg: 'bg-cyan-500/10 border-cyan-500/20'
    },
    emerald: {
      accent: 'border-l-emerald-500',
      valueColor: 'text-emerald-400',
      iconColor: 'text-emerald-500',
      iconBg: 'bg-emerald-500/10 border-emerald-500/20'
    },
    neutral: {
      accent: 'border-l-obsidian-600',
      valueColor: 'text-slate-100',
      iconColor: 'text-slate-400',
      iconBg: 'bg-obsidian-800 border-obsidian-700'
    }
  };

  const style = variantMap[variant];

  return (
    <div
      className={`bg-obsidian-850 border border-obsidian-700/80 rounded-lg p-3.5 space-y-2 relative overflow-hidden transition-all hover:border-obsidian-600 border-l-2 ${style.accent} ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-medium truncate">
          {label}
        </span>
        {Icon && (
          <div className={`p-1.5 rounded-md border ${style.iconBg} ${style.iconColor} shrink-0`}>
            <Icon className="w-3.5 h-3.5" />
          </div>
        )}
      </div>

      <div className="flex items-baseline justify-between gap-2 pt-0.5">
        <span className={`text-2xl font-bold font-mono tracking-tight tabular-nums ${style.valueColor}`}>
          {value}
        </span>

        {delta && (
          <span
            className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${
              delta.isPositive
                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                : 'bg-red-950/60 text-red-400 border border-red-800/50'
            }`}
          >
            {delta.isPositive ? '↑' : '↓'} {delta.value}
          </span>
        )}
      </div>

      {subtext && (
        <p className="text-[10px] text-slate-500 font-mono truncate">
          {subtext}
        </p>
      )}
    </div>
  );
};
