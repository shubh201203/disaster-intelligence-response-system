import React from 'react';

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;

interface SeverityBadgeProps {
  severity: SeverityLevel;
  showDot?: boolean;
  className?: string;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  showDot = true,
  className = '',
  size = 'sm'
}) => {
  const norm = (severity || 'LOW').toUpperCase();

  const config = {
    CRITICAL: {
      bg: 'bg-red-950/70',
      text: 'text-red-400',
      border: 'border-red-800/70',
      dot: 'bg-red-500 animate-pulse',
      label: 'CRITICAL'
    },
    HIGH: {
      bg: 'bg-orange-950/70',
      text: 'text-orange-400',
      border: 'border-orange-800/70',
      dot: 'bg-orange-500',
      label: 'HIGH'
    },
    MEDIUM: {
      bg: 'bg-amber-950/70',
      text: 'text-amber-400',
      border: 'border-amber-800/70',
      dot: 'bg-amber-500',
      label: 'MEDIUM'
    },
    LOW: {
      bg: 'bg-emerald-950/70',
      text: 'text-emerald-400',
      border: 'border-emerald-800/70',
      dot: 'bg-emerald-500',
      label: 'LOW'
    }
  }[norm] || {
    bg: 'bg-slate-900',
    text: 'text-slate-400',
    border: 'border-slate-800',
    dot: 'bg-slate-500',
    label: norm
  };

  const sizeClasses = size === 'sm' 
    ? 'text-[10px] px-2 py-0.5 gap-1.5' 
    : 'text-xs px-2.5 py-1 gap-2';

  return (
    <span
      className={`inline-flex items-center font-mono font-semibold rounded border ${config.bg} ${config.text} ${config.border} ${sizeClasses} ${className}`}
    >
      {showDot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${config.dot}`} />}
      <span>{config.label}</span>
    </span>
  );
};
