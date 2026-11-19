/**
 * DIRS Offline Draft Store — IndexedDB Persistence Engine
 * 
 * Provides transactional, client-side persistence for field operational drafts
 * (Citizen Incident Reports, Volunteer Field Inspections).
 * Enforces strict user isolation on shared devices.
 * Integrates Web Crypto AES-256-GCM authenticated encryption for sensitive payloads at rest.
 * Zero external dependencies (native IndexedDB and SubtleCrypto APIs).
 */

import {
  encryptDraftPayload,
  decryptDraftPayload,
  isEncryptedEnvelope,
  generateSalt,
  isWebCryptoAvailable,
  EncryptedPayloadEnvelope
} from './cryptoVault';

export type DraftWorkflowType = 'INCIDENT_REPORT' | 'FIELD_INSPECTION';

export type DraftSyncStatus = 'DRAFT' | 'SYNCING' | 'SYNCED' | 'FAILED' | 'CONFLICT';

export interface OfflineDraft<T = any> {
  client_draft_id: string; // Unique UUID (Idempotency Key)
  workflow_type: DraftWorkflowType;
  user_id: string; // Enforces user-isolation on shared device
  user_email?: string;
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
  sync_status: DraftSyncStatus;
  last_sync_attempt: string | null;
  sync_error: string | null;
  payload: T;
  server_acknowledged_id?: string | null;
  server_acknowledged_code?: string | null;
}

const DB_NAME = 'dirs_offline_db';
const DB_VERSION = 1;
const STORE_NAME = 'dirs_offline_drafts';

/**
 * Ephemeral session vault keys map (userId -> CryptoKey).
 * Held strictly in volatile JavaScript memory.
 * Never persisted to disk, localStorage, sessionStorage, or IndexedDB.
 * Automatically wiped on page reload or browser restart.
 */
const sessionVaultKeys = new Map<string, CryptoKey>();

export function setSessionVaultKey(userId: string, key: CryptoKey | null): void {
  if (key) {
    sessionVaultKeys.set(userId, key);
  } else {
    sessionVaultKeys.delete(userId);
  }
}

export function getSessionVaultKey(userId: string): CryptoKey | null {
  return sessionVaultKeys.get(userId) || null;
}

export function clearSessionVaultKeys(): void {
  sessionVaultKeys.clear();
}

/**
 * Opens or upgrades the IndexedDB database instance.
 */
export function openDraftDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      return reject(new Error('IndexedDB is not available in this browser environment'));
    }

    const request = window.indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'client_draft_id' });
        store.createIndex('by_user', 'user_id', { unique: false });
        store.createIndex('by_type', 'workflow_type', { unique: false });
        store.createIndex('by_status', 'sync_status', { unique: false });
        store.createIndex('by_user_type', ['user_id', 'workflow_type'], { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Resolves a retrieved draft record:
 * - If payload is unencrypted (v1/legacy), returns directly (lossless backward compatibility).
 * - If payload is encrypted (v2), decrypts with active session key or provided key.
 * - If key is missing or decryption fails, preserves draft safely without data loss.
 */
async function resolveDraftPayload<T>(
  draft: OfflineDraft<any>,
  key?: CryptoKey | null
): Promise<OfflineDraft<T>> {
  if (!isEncryptedEnvelope(draft.payload)) {
    // Unencrypted legacy/v1 draft: return directly
    return draft as OfflineDraft<T>;
  }

  const activeKey = key || getSessionVaultKey(draft.user_id);
  if (!activeKey) {
    // Key not unlocked in memory: preserve draft intact, flag locked error, never discard
    return {
      ...draft,
      sync_error: draft.sync_error || 'VAULT_LOCKED: Decryption key required to inspect payload'
    };
  }

  try {
    const decrypted = await decryptDraftPayload<T>(draft.payload, activeKey);
    return {
      ...draft,
      payload: decrypted
    };
  } catch (err: any) {
    // Decryption failure (tampered ciphertext or invalid key): preserve draft, never discard!
    return {
      ...draft,
      sync_error: `DECRYPTION_FAILED: ${err?.message || 'Ciphertext verification failed'}`
    };
  }
}

/**
 * Saves or updates a draft in IndexedDB.
 * If a vault key is available (passed directly or in sessionVaultKeys), encrypts the payload with AES-256-GCM.
 */
export async function saveDraft<T>(
  draft: Omit<OfflineDraft<T>, 'created_at' | 'updated_at'> & { created_at?: string; updated_at?: string },
  customKey?: CryptoKey
): Promise<OfflineDraft<T>> {
  if (!draft.user_id) {
    throw new Error('Cannot save offline draft without authenticated user_id principal');
  }

  const key = customKey || getSessionVaultKey(draft.user_id);
  let payloadToPersist: any = draft.payload;

  // Authenticated encryption with AES-256-GCM if key is available and not already encrypted
  if (key && isWebCryptoAvailable() && !isEncryptedEnvelope(draft.payload)) {
    const salt = generateSalt(16);
    payloadToPersist = await encryptDraftPayload(draft.payload, key, salt);
  }

  const db = await openDraftDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);

    const now = new Date().toISOString();
    const fullDraftToStore: OfflineDraft<any> = {
      ...draft,
      created_at: draft.created_at || now,
      updated_at: now,
      sync_status: draft.sync_status || 'DRAFT',
      last_sync_attempt: draft.last_sync_attempt || null,
      sync_error: draft.sync_error || null,
      payload: payloadToPersist
    };

    const request = store.put(fullDraftToStore);
    request.onsuccess = () => {
      // Return draft with in-memory unencrypted payload so caller can use it immediately
      resolve({
        ...fullDraftToStore,
        payload: draft.payload
      });
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Retrieves a single draft by client_draft_id with optional principal isolation check and decryption.
 */
export async function getDraft<T = any>(
  client_draft_id: string,
  expectedUserId?: string,
  customKey?: CryptoKey
): Promise<OfflineDraft<T> | null> {
  const db = await openDraftDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.get(client_draft_id);

    request.onsuccess = async () => {
      const result = request.result as OfflineDraft<any> | undefined;
      if (!result) return resolve(null);
      if (expectedUserId && result.user_id !== expectedUserId) {
        // Enforce account isolation: reject access from foreign user
        return resolve(null);
      }
      try {
        const resolved = await resolveDraftPayload<T>(result, customKey);
        resolve(resolved);
      } catch (err) {
        reject(err);
      }
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Lists drafts belonging exclusively to a specific authenticated user.
 * Decrypts payloads using session vault key if encrypted.
 */
export async function listDraftsByUser<T = any>(
  userId: string,
  workflowType?: DraftWorkflowType,
  customKey?: CryptoKey
): Promise<OfflineDraft<T>[]> {
  const db = await openDraftDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const index = store.index('by_user');
    const request = index.getAll(userId);

    request.onsuccess = async () => {
      let results: OfflineDraft<any>[] = request.result || [];
      // Guarantee filtering by user_id
      results = results.filter(d => d.user_id === userId);
      if (workflowType) {
        results = results.filter(d => d.workflow_type === workflowType);
      }
      // Order descending by updated_at
      results.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

      try {
        const resolvedList = await Promise.all(
          results.map(d => resolveDraftPayload<T>(d, customKey))
        );
        resolve(resolvedList);
      } catch (err) {
        reject(err);
      }
    };
    request.onerror = () => reject(request.error);
  });
}

/**
 * Updates synchronization metadata for an existing draft with principal verification.
 * Preserves existing encrypted or plaintext payload unchanged.
 */
export async function updateDraftStatus(
  client_draft_id: string,
  status: DraftSyncStatus,
  error?: string | null,
  serverAck?: { id?: string; code?: string },
  expectedUserId?: string
): Promise<void> {
  const db = await openDraftDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const getReq = store.get(client_draft_id);

    getReq.onsuccess = () => {
      const draft = getReq.result as OfflineDraft;
      if (!draft) {
        return reject(new Error(`Draft with ID ${client_draft_id} not found`));
      }

      if (expectedUserId && draft.user_id !== expectedUserId) {
        return reject(new Error(`Security violation: User ${expectedUserId} is not authorized to update draft ${client_draft_id}`));
      }

      draft.sync_status = status;
      draft.updated_at = new Date().toISOString();
      draft.last_sync_attempt = new Date().toISOString();
      if (error !== undefined) {
        draft.sync_error = error;
      }
      if (serverAck?.id) {
        draft.server_acknowledged_id = serverAck.id;
      }
      if (serverAck?.code) {
        draft.server_acknowledged_code = serverAck.code;
      }

      const putReq = store.put(draft);
      putReq.onsuccess = () => resolve();
      putReq.onerror = () => reject(putReq.error);
    };
    getReq.onerror = () => reject(getReq.error);
  });
}

/**
 * Deletes a draft from IndexedDB with optional principal verification.
 */
export async function deleteDraft(
  client_draft_id: string,
  expectedUserId?: string
): Promise<void> {
  const db = await openDraftDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);

    if (expectedUserId) {
      const getReq = store.get(client_draft_id);
      getReq.onsuccess = () => {
        const draft = getReq.result as OfflineDraft | undefined;
        if (!draft) return resolve(); // Idempotent delete if not found
        if (draft.user_id !== expectedUserId) {
          return reject(new Error(`Security violation: User ${expectedUserId} cannot delete foreign draft ${client_draft_id}`));
        }
        const delReq = store.delete(client_draft_id);
        delReq.onsuccess = () => resolve();
        delReq.onerror = () => reject(delReq.error);
      };
      getReq.onerror = () => reject(getReq.error);
    } else {
      const request = store.delete(client_draft_id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    }
  });
}

/**
 * Clears all SYNCED drafts for a user to reclaim client storage.
 */
export async function clearSyncedDrafts(userId: string): Promise<number> {
  const db = await openDraftDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const index = store.index('by_user');
    const request = index.getAll(userId);

    request.onsuccess = () => {
      const drafts: OfflineDraft[] = request.result || [];
      const syncedDrafts = drafts.filter(d => d.sync_status === 'SYNCED' && d.user_id === userId);
      
      let deletedCount = 0;
      if (syncedDrafts.length === 0) {
        return resolve(0);
      }

      syncedDrafts.forEach(d => {
        store.delete(d.client_draft_id);
        deletedCount++;
      });

      tx.oncomplete = () => resolve(deletedCount);
      tx.onerror = () => reject(tx.error);
    };
    request.onerror = () => reject(request.error);
  });
}
