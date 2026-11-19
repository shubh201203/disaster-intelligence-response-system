import React from 'react';

interface LoadingSkeletonProps {
  lines?: number;
  className?: string;
  variant?: 'card' | 'table' | 'text';
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  lines = 3,
  className = '',
  variant = 'text'
}) => {
  if (variant === 'card') {
    return (
      <div className={`bg-obsidian-850 border border-obsidian-700/60 rounded-xl p-5 space-y-4 animate-pulse ${className}`}>
        <div className="flex items-center justify-between">
          <div className="h-4 w-32 bg-obsidian-700 rounded" />
          <div className="h-6 w-16 bg-obsidian-700 rounded-full" />
        </div>
        <div className="h-8 w-24 bg-obsidian-700 rounded" />
        <div className="h-3 w-48 bg-obsidian-800 rounded" />
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className={`space-y-2 animate-pulse ${className}`}>
        <div className="h-8 bg-obsidian-800 rounded border border-obsidian-700/50" />
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className="h-10 bg-obsidian-850 rounded border border-obsidian-700/30 flex items-center px-4 gap-4">
            <div className="h-3 w-16 bg-obsidian-700 rounded" />
            <div className="h-3 w-28 bg-obsidian-700 rounded" />
            <div className="h-3 flex-1 bg-obsidian-800 rounded" />
            <div className="h-3 w-20 bg-obsidian-700 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`space-y-2.5 animate-pulse ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-3.5 bg-obsidian-700/70 rounded"
          style={{ width: `${85 - (i * 15)}%` }}
        />
      ))}
    </div>
  );
};
