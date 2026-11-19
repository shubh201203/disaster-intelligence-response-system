import React, { useState } from 'react';
import { 
  Database, 
  RefreshCw, 
  Trash2, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  FileEdit,
  ExternalLink,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { OfflineDraft } from '../../utils/offlineDraftStore';
import { StatusBadge } from '../design-system';

interface DraftSyncManagerProps<T = any> {
  drafts: OfflineDraft<T>[];
  loading: boolean;
  isOnline: boolean;
  onSyncDraft: (id: string) => Promise<{ success: boolean; error?: string }>;
  onSyncAll: () => Promise<{ attempted: number; succeeded: number; failed: number }>;
  onDeleteDraft: (id: string) => Promise<void>;
  onClearCompleted: () => Promise<number>;
  onLoadDraft?: (draft: OfflineDraft<T>) => void;
  title?: string;
}

export const DraftSyncManager: React.FC<DraftSyncManagerProps> = ({
  drafts,
  loading,
  isOnline,
  onSyncDraft,
  onSyncAll,
  onDeleteDraft,
  onClearCompleted,
  onLoadDraft,
  title = 'Local Offline Drafts & Synchronization Queue'
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const pendingCount = drafts.filter(d => d.sync_status === 'DRAFT' || d.sync_status === 'FAILED').length;
  const syncedCount = drafts.filter(d => d.sync_status === 'SYNCED').length;

  const handleSyncSingle = async (id: string) => {
    setSyncingId(id);
    setActionMessage(null);
    try {
      const res = await onSyncDraft(id);
      if (res.success) {
        setActionMessage('Draft successfully synchronized to server.');
      } else {
        setActionMessage(`Sync failed: ${res.error || 'Server error'}`);
      }
    } finally {
      setSyncingId(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    setActionMessage(null);
    try {
      const res = await onSyncAll();
      setActionMessage(`Sync complete: ${res.succeeded} synced, ${res.failed} failed.`);
    } finally {
      setSyncingAll(false);
    }
  };

  if (drafts.length === 0 && !loading) {
    return null;
  }

  return (
    <div className="bg-obsidian-900 border border-obsidian-750 rounded-xl p-4 space-y-3 font-mono text-xs shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-obsidian-800">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-amber-ops" />
          <span className="font-bold text-slate-200">{title}</span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-obsidian-700">
            {drafts.length} stored locally
          </span>
        </div>

        <div className="flex items-center gap-2">
          {syncedCount > 0 && (
            <button
              type="button"
              onClick={onClearCompleted}
              className="px-2 py-1 bg-obsidian-800 hover:bg-obsidian-750 text-slate-400 hover:text-slate-200 rounded text-[10px] border border-obsidian-700 transition"
            >
              Clear Synced ({syncedCount})
            </button>
          )}

          {pendingCount > 0 && (
            <button
              type="button"
              disabled={!isOnline || syncingAll}
              onClick={handleSyncAll}
              className="px-2.5 py-1 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded text-[10px] transition flex items-center gap-1 disabled:opacity-40"
            >
              <RefreshCw className={`w-3 h-3 ${syncingAll ? 'animate-spin' : ''}`} />
              <span>{syncingAll ? 'Syncing All...' : `Sync All Pending (${pendingCount})`}</span>
            </button>
          )}
        </div>
      </div>

      {actionMessage && (
        <div className="p-2 rounded bg-obsidian-850 border border-obsidian-700 text-[11px] text-amber-300 flex items-center justify-between">
          <span>{actionMessage}</span>
          <button type="button" onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">×</button>
        </div>
      )}

      <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
        {drafts.map((draft) => {
          const isExpanded = expandedId === draft.client_draft_id;
          const isItemSyncing = syncingId === draft.client_draft_id;

          const getStatusBadgeVariant = (st: string) => {
            switch (st) {
              case 'SYNCED': return 'bg-emerald-950/80 text-emerald-400 border-emerald-800';
              case 'SYNCING': return 'bg-cyan-950/80 text-cyan-300 border-cyan-800 animate-pulse';
              case 'FAILED': return 'bg-red-950/80 text-red-300 border-red-800';
              case 'CONFLICT': return 'bg-purple-950/80 text-purple-300 border-purple-800';
              default: return 'bg-amber-950/80 text-amber-300 border-amber-800';
            }
          };

          return (
            <div
              key={draft.client_draft_id}
              className="p-2.5 bg-obsidian-950 rounded-lg border border-obsidian-800 space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 font-bold">
                    ID: {draft.client_draft_id.slice(0, 8)}...
                  </span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-bold ${getStatusBadgeVariant(draft.sync_status)}`}>
                    {draft.sync_status}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {draft.payload?.title || draft.payload?.facility_name || 'Draft Record'}
                  </span>
                </div>

                <div className="flex items-center gap-1.5">
                  {onLoadDraft && draft.sync_status !== 'SYNCED' && (
                    <button
                      type="button"
                      onClick={() => onLoadDraft(draft)}
                      title="Load into form for editing"
                      className="p-1 text-slate-400 hover:text-cyan-ops transition"
                    >
                      <FileEdit className="w-3.5 h-3.5" />
                    </button>
                  )}

                  {draft.sync_status !== 'SYNCED' && (
                    <button
                      type="button"
                      disabled={!isOnline || isItemSyncing}
                      onClick={() => handleSyncSingle(draft.client_draft_id)}
                      title="Synchronize draft to server"
                      className="p-1 text-slate-400 hover:text-amber-ops transition disabled:opacity-30"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${isItemSyncing ? 'animate-spin' : ''}`} />
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => onDeleteDraft(draft.client_draft_id)}
                    title="Delete local draft"
                    className="p-1 text-slate-500 hover:text-red-400 transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>

                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : draft.client_draft_id)}
                    className="p-1 text-slate-500 hover:text-slate-300"
                  >
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {draft.sync_error && (
                <div className="p-1.5 rounded bg-red-950/60 border border-red-900 text-red-300 text-[10px] flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 shrink-0 text-red-400" />
                  <span className="truncate">{draft.sync_error}</span>
                </div>
              )}

              {draft.server_acknowledged_code && (
                <div className="text-[10px] text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 shrink-0" />
                  <span>Server Confirmed: {draft.server_acknowledged_code}</span>
                </div>
              )}

              {isExpanded && (
                <div className="p-2 bg-obsidian-900 rounded border border-obsidian-800 text-[10px] space-y-1 text-slate-400 font-mono">
                  <div>Saved: {new Date(draft.updated_at).toLocaleString()}</div>
                  {draft.last_sync_attempt && (
                    <div>Last Sync Attempt: {new Date(draft.last_sync_attempt).toLocaleString()}</div>
                  )}
                  <div className="pt-1 text-slate-500">Payload Preview:</div>
                  <pre className="p-1.5 bg-obsidian-950 rounded text-[9px] overflow-x-auto text-slate-300">
                    {JSON.stringify(draft.payload, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
