import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNetworkStatus } from './useNetworkStatus';
import { apiClient } from '../api/client';
import {
  DraftWorkflowType,
  DraftSyncStatus,
  OfflineDraft,
  saveDraft,
  listDraftsByUser,
  updateDraftStatus,
  deleteDraft,
  clearSyncedDrafts,
  setSessionVaultKey,
  getSessionVaultKey
} from '../utils/offlineDraftStore';
import { deriveKeyFromPassphrase } from '../utils/cryptoVault';

export interface UseOfflineDraftsResult<T = any> {
  drafts: OfflineDraft<T>[];
  loading: boolean;
  isOnline: boolean;
  saveCurrentDraft: (payload: T, clientDraftId?: string) => Promise<OfflineDraft<T>>;
  syncDraft: (clientDraftId: string) => Promise<{ success: boolean; error?: string; ack?: any }>;
  syncAllPending: () => Promise<{ attempted: number; succeeded: number; failed: number }>;
  removeDraft: (clientDraftId: string) => Promise<void>;
  clearCompleted: () => Promise<number>;
  reloadDrafts: () => Promise<void>;
  unlockVault: (passphrase: string) => Promise<boolean>;
  lockVault: () => void;
}

export function useOfflineDrafts<T = any>(workflowType: DraftWorkflowType): UseOfflineDraftsResult<T> {
  const { user } = useAuth();
  const { isOnline } = useNetworkStatus();
  const [drafts, setDrafts] = useState<OfflineDraft<T>[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const currentUserId = user?.id || 'anonymous_guest';
  const currentUserEmail = user?.email || undefined;

  const reloadDrafts = useCallback(async () => {
    if (!currentUserId) return;
    try {
      setLoading(true);
      const items = await listDraftsByUser<T>(currentUserId, workflowType);
      setDrafts(items);
    } catch (err) {
      console.warn('Failed to load offline drafts from IndexedDB', err);
    } finally {
      setLoading(false);
    }
  }, [currentUserId, workflowType]);

  // Immediately clear previous user drafts on account switch before loading new
  useEffect(() => {
    setDrafts([]);
    reloadDrafts();
  }, [reloadDrafts]);

  const unlockVault = async (passphrase: string): Promise<boolean> => {
    if (!currentUserId || !passphrase) return false;
    try {
      const enc = new TextEncoder();
      const rawSalt = `dirs_user_salt_${currentUserId}`;
      const userSalt = enc.encode(rawSalt.padEnd(16, '0').slice(0, 16));
      const key = await deriveKeyFromPassphrase(passphrase, userSalt);
      setSessionVaultKey(currentUserId, key);
      await reloadDrafts();
      return true;
    } catch {
      return false;
    }
  };

  const lockVault = (): void => {
    if (currentUserId) {
      setSessionVaultKey(currentUserId, null);
      reloadDrafts();
    }
  };

  const saveCurrentDraft = async (payload: T, existingDraftId?: string): Promise<OfflineDraft<T>> => {
    const draftId = existingDraftId || crypto.randomUUID();
    const saved = await saveDraft<T>({
      client_draft_id: draftId,
      workflow_type: workflowType,
      user_id: currentUserId,
      user_email: currentUserEmail,
      sync_status: 'DRAFT',
      last_sync_attempt: null,
      sync_error: null,
      payload
    });
    await reloadDrafts();
    return saved;
  };

  const syncDraft = async (clientDraftId: string): Promise<{ success: boolean; error?: string; ack?: any }> => {
    if (!navigator.onLine) {
      await updateDraftStatus(
        clientDraftId,
        'FAILED',
        'Device is offline. Connect to a network to synchronize.',
        undefined,
        currentUserId
      );
      await reloadDrafts();
      return { success: false, error: 'Device is offline' };
    }

    const draft = drafts.find(d => d.client_draft_id === clientDraftId);
    if (!draft || draft.user_id !== currentUserId) {
      return { success: false, error: 'Draft not found or principal mismatch' };
    }

    // Idempotency check: if draft was already server-acknowledged, avoid duplicate network submission
    if (draft.sync_status === 'SYNCED' && draft.server_acknowledged_id) {
      return {
        success: true,
        ack: {
          id: draft.server_acknowledged_id,
          code: draft.server_acknowledged_code || draft.server_acknowledged_id
        }
      };
    }

    try {
      // Transition to SYNCING
      await updateDraftStatus(clientDraftId, 'SYNCING', null, undefined, currentUserId);
      await reloadDrafts();

      // Dispatch mutation via REST client with client_draft_id as Idempotency-Key
      let response: any;
      if (workflowType === 'INCIDENT_REPORT') {
        // Collect any base64 images into media_urls array so backend persists them
        const p: any = { ...(draft.payload as any) };
        const mediaUrls: string[] = Array.isArray(p.media_urls) ? [...p.media_urls] : [];
        if (p.image_preview && typeof p.image_preview === 'string' && !mediaUrls.includes(p.image_preview)) {
          mediaUrls.push(p.image_preview);
        }
        if (Array.isArray(p.image_previews)) {
          for (const item of p.image_previews) {
            const u = item?.preview || item;
            if (typeof u === 'string' && !mediaUrls.includes(u)) {
              mediaUrls.push(u);
            }
          }
        }
        p.media_urls = mediaUrls;

        response = await apiClient.post('/incidents', p, {
          headers: {
            'Idempotency-Key': clientDraftId,
            'X-Idempotency-Key': clientDraftId
          }
        });
      } else if (workflowType === 'FIELD_INSPECTION') {
        response = await apiClient.post('/recovery/damage-assessments/field-inspection', draft.payload, {
          headers: {
            'Idempotency-Key': clientDraftId,
            'X-Idempotency-Key': clientDraftId
          }
        });
      } else {
        throw new Error(`Unsupported workflow type: ${workflowType}`);
      }

      // Mark as SYNCED with authoritative server acknowledgement
      const ackData = {
        id: response.data.id,
        code: response.data.incident_code || response.data.assessment_code || response.data.id
      };
      await updateDraftStatus(clientDraftId, 'SYNCED', null, ackData, currentUserId);
      await reloadDrafts();

      return { success: true, ack: ackData };
    } catch (err: any) {
      const statusCode = err?.response?.status;
      let errorMsg = err?.response?.data?.detail || err.message || 'Synchronization failed';

      if (statusCode === 409) {
        // Server conflict: duplicate or state conflict
        await updateDraftStatus(clientDraftId, 'CONFLICT', `Conflict (409): ${errorMsg}`, undefined, currentUserId);
      } else if (statusCode === 401) {
        // Session expired: preserve draft safely for re-authentication
        await updateDraftStatus(clientDraftId, 'DRAFT', 'Session expired (401). Re-authenticate to synchronize.', undefined, currentUserId);
      } else if (statusCode === 422) {
        // Validation error: preserve draft for user correction
        await updateDraftStatus(clientDraftId, 'FAILED', `Validation failed (422): ${JSON.stringify(errorMsg)}`, undefined, currentUserId);
      } else {
        // Network or transient server error
        await updateDraftStatus(clientDraftId, 'FAILED', errorMsg, undefined, currentUserId);
      }

      await reloadDrafts();
      return { success: false, error: errorMsg };
    }
  };

  const syncAllPending = async (): Promise<{ attempted: number; succeeded: number; failed: number }> => {
    const pendingDrafts = drafts.filter(d => d.sync_status === 'DRAFT' || d.sync_status === 'FAILED');
    let succeeded = 0;
    let failed = 0;

    for (const draft of pendingDrafts) {
      const result = await syncDraft(draft.client_draft_id);
      if (result.success) {
        succeeded++;
      } else {
        failed++;
      }
    }

    return { attempted: pendingDrafts.length, succeeded, failed };
  };

  const removeDraft = async (clientDraftId: string): Promise<void> => {
    await deleteDraft(clientDraftId, currentUserId);
    await reloadDrafts();
  };

  const clearCompleted = async (): Promise<number> => {
    const cleared = await clearSyncedDrafts(currentUserId);
    await reloadDrafts();
    return cleared;
  };

  return {
    drafts,
    loading,
    isOnline,
    saveCurrentDraft,
    syncDraft,
    syncAllPending,
    removeDraft,
    clearCompleted,
    reloadDrafts,
    unlockVault,
    lockVault
  };
}
