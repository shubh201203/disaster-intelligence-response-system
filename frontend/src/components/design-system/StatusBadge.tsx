import React from 'react';

interface StatusBadgeProps {
  status: string;
  variant?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  className = ''
}) => {
  const norm = (status || 'UNKNOWN').toUpperCase();

  // Auto-detect variant if not explicitly provided
  let determinedVariant = variant;
  if (!determinedVariant) {
    if (['VERIFIED', 'RESOLVED', 'COMPLETED', 'ON_DUTY', 'ACCEPTED', 'ACTIVE'].includes(norm)) {
      determinedVariant = 'success';
    } else if (['IN_PROGRESS', 'EN_ROUTE', 'ASSIGNED', 'PENDING'].includes(norm)) {
      determinedVariant = 'warning';
    } else if (['REJECTED', 'DISMISSED', 'OFFLINE', 'CRITICAL', 'PANIC'].includes(norm)) {
      determinedVariant = 'danger';
    } else if (['REPORTED', 'NEW', 'TELEMETRY'].includes(norm)) {
      determinedVariant = 'info';
    } else {
      determinedVariant = 'neutral';
    }
  }

  const variantStyles = {
    success: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60',
    warning: 'bg-amber-950/60 text-amber-300 border-amber-800/60',
    danger: 'bg-red-950/60 text-red-300 border-red-800/60',
    info: 'bg-cyan-950/60 text-cyan-300 border-cyan-800/60',
    neutral: 'bg-obsidian-800 text-slate-300 border-obsidian-700',
  }[determinedVariant];

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium border ${variantStyles} ${className}`}
    >
      {norm}
    </span>
  );
};
