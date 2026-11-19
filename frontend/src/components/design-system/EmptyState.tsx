import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className = ''
}) => {
  return (
    <div className={`p-8 text-center bg-obsidian-900/50 border border-dashed border-obsidian-700/80 rounded-xl space-y-3 ${className}`}>
      <div className="w-10 h-10 mx-auto rounded-lg bg-obsidian-800 border border-obsidian-700 flex items-center justify-center text-slate-400">
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
          {title}
        </h4>
        {description && (
          <p className="text-[11px] text-slate-500 font-sans mt-1 max-w-sm mx-auto">
            {description}
          </p>
        )}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </div>
  );
};
