import React from 'react';

interface OperationalCardProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  headerAction?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  level?: 1 | 2 | 3;
  accent?: 'none' | 'amber' | 'cyan' | 'red' | 'emerald';
}

export const OperationalCard: React.FC<OperationalCardProps> = ({
  title,
  subtitle,
  headerAction,
  children,
  className = '',
  bodyClassName = '',
  level = 2,
  accent = 'none'
}) => {
  const bgLevel = {
    1: 'bg-obsidian-900 border-obsidian-border',
    2: 'bg-obsidian-850 border-obsidian-700/80',
    3: 'bg-obsidian-800 border-obsidian-600',
  }[level];

  const accentBorder = {
    none: '',
    amber: 'border-t-2 border-t-amber-ops',
    cyan: 'border-t-2 border-t-cyan-ops',
    red: 'border-t-2 border-t-status-critical',
    emerald: 'border-t-2 border-t-status-low',
  }[accent];

  return (
    <div className={`rounded-xl border shadow-xl overflow-hidden transition-all ${bgLevel} ${accentBorder} ${className}`}>
      {(title || headerAction) && (
        <div className="px-5 py-3.5 border-b border-obsidian-700/60 flex items-center justify-between gap-3 bg-obsidian-900/40">
          <div>
            {typeof title === 'string' ? (
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                {title}
              </h3>
            ) : (
              title
            )}
            {subtitle && (
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
          {headerAction && <div className="shrink-0">{headerAction}</div>}
        </div>
      )}
      <div className={`p-5 ${bodyClassName}`}>
        {children}
      </div>
    </div>
  );
};
