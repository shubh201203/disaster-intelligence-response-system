import React from 'react';
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';

interface OfflineBannerProps {
  pendingDraftCount?: number;
  onSyncNow?: () => void;
  isSyncing?: boolean;
}

export const OfflineBanner: React.FC<OfflineBannerProps> = ({
  pendingDraftCount = 0,
  onSyncNow,
  isSyncing = false
}) => {
  const { isOnline, offlineSince } = useNetworkStatus();

  if (isOnline && pendingDraftCount === 0) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={`w-full py-2 px-4 text-xs font-mono flex flex-wrap items-center justify-between gap-2 border-b transition-all ${
        !isOnline
          ? 'bg-amber-950/95 border-amber-700 text-amber-200'
          : 'bg-cyan-950/95 border-cyan-700 text-cyan-200'
      }`}
    >
      <div className="flex items-center gap-2">
        {!isOnline ? (
          <>
            <WifiOff className="w-4 h-4 text-amber-400 animate-pulse shrink-0" />
            <span className="font-bold tracking-wide">
              OFFLINE MODE: Disconnected from DIRS Server.
            </span>
            <span className="text-[11px] opacity-80 hidden sm:inline">
              Submissions are securely auto-saved locally in IndexedDB.
            </span>
            {offlineSince && (
              <span className="text-[10px] opacity-60">
                (Offline since {offlineSince.toLocaleTimeString()})
              </span>
            )}
          </>
        ) : (
          <>
            <Wifi className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="font-bold tracking-wide text-emerald-300">
              NETWORK RESTORED.
            </span>
            <span>
              {pendingDraftCount} local draft{pendingDraftCount > 1 ? 's' : ''} ready for synchronization.
            </span>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        {pendingDraftCount > 0 && (
          <span className="px-2 py-0.5 rounded bg-black/40 border border-current text-[10px] font-bold">
            {pendingDraftCount} PENDING DRAFT{pendingDraftCount > 1 ? 'S' : ''}
          </span>
        )}

        {isOnline && pendingDraftCount > 0 && onSyncNow && (
          <button
            type="button"
            onClick={onSyncNow}
            disabled={isSyncing}
            className="px-2.5 py-1 rounded bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold text-[11px] flex items-center gap-1 transition shadow disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Syncing...' : 'Sync Now'}</span>
          </button>
        )}
      </div>
    </div>
  );
};
