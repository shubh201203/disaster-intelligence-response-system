/**
 * DIRS Phase 7 Web Crypto Offline Vault
 * 
 * Provides client-side authenticated encryption for offline operational drafts
 * stored in IndexedDB (Citizen Incident Reports, Field Damage Assessments).
 * 
 * Cryptographic Architecture:
 * - Cipher: AES-256-GCM (Galois/Counter Mode with 128-bit authentication tag)
 * - Key Derivation: PBKDF2-HMAC-SHA-256 with 100,000 iterations and 16-byte random salt
 * - Initialization Vector: 12-byte cryptographically secure pseudorandom bytes (CSPRNG)
 * - Zero external libraries: 100% native Web Crypto API (SubtleCrypto)
 * - Versioned envelope format supporting seamless migration from unencrypted v1 to encrypted v2
 */

export interface EncryptedPayloadEnvelope {
  __format: 'DIRS_VAULT_V2';
  algorithm: 'AES-256-GCM';
  kdf: 'PBKDF2-HMAC-SHA256';
  iterations: number;
  salt: string; // Base64 encoded
  iv: string;   // Base64 encoded
  ciphertext: string; // Base64 encoded
}

export function isWebCryptoAvailable(): boolean {
  return typeof globalThis !== 'undefined' &&
    !!globalThis.crypto &&
    typeof globalThis.crypto.subtle !== 'undefined';
}

function bufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToBuffer(base64: string): Uint8Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function generateSalt(length = 16): Uint8Array {
  const salt = new Uint8Array(length);
  globalThis.crypto.getRandomValues(salt);
  return salt;
}

/**
 * Derives a 256-bit AES-GCM CryptoKey from a user passphrase and salt via PBKDF2.
 */
export async function deriveKeyFromPassphrase(
  passphrase: string,
  salt: Uint8Array,
  iterations = 100000
): Promise<CryptoKey> {
  if (!isWebCryptoAvailable()) {
    throw new Error('Web Crypto API is not available in this environment');
  }

  const enc = new TextEncoder();
  const baseKey = await globalThis.crypto.subtle.importKey(
    'raw',
    enc.encode(passphrase),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );

  return globalThis.crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt as any,
      iterations,
      hash: 'SHA-256'
    },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Encrypts arbitrary serializable payload using AES-256-GCM.
 */
export async function encryptDraftPayload<T = any>(
  payload: T,
  key: CryptoKey,
  salt: Uint8Array
): Promise<EncryptedPayloadEnvelope> {
  if (!isWebCryptoAvailable()) {
    throw new Error('Web Crypto API is not available in this environment');
  }

  const enc = new TextEncoder();
  const serialized = JSON.stringify(payload);
  const iv = new Uint8Array(12);
  globalThis.crypto.getRandomValues(iv);

  const ciphertextBuffer = await globalThis.crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    enc.encode(serialized)
  );

  return {
    __format: 'DIRS_VAULT_V2',
    algorithm: 'AES-256-GCM',
    kdf: 'PBKDF2-HMAC-SHA256',
    iterations: 100000,
    salt: bufferToBase64(salt),
    iv: bufferToBase64(iv),
    ciphertext: bufferToBase64(ciphertextBuffer)
  };
}

/**
 * Decrypts an EncryptedPayloadEnvelope back to its original object structure.
 */
export async function decryptDraftPayload<T = any>(
  envelope: EncryptedPayloadEnvelope,
  key: CryptoKey
): Promise<T> {
  if (!isWebCryptoAvailable()) {
    throw new Error('Web Crypto API is not available in this environment');
  }

  if (envelope.__format !== 'DIRS_VAULT_V2') {
    throw new Error(`Unsupported envelope format: ${envelope.__format}`);
  }

  const iv = base64ToBuffer(envelope.iv);
  const ciphertext = base64ToBuffer(envelope.ciphertext);

  const decryptedBuffer = await globalThis.crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: iv as any },
    key,
    ciphertext as any
  );

  const dec = new TextDecoder();
  const jsonString = dec.decode(decryptedBuffer);
  return JSON.parse(jsonString) as T;
}

/**
 * Type guard to check if a payload is encrypted with DIRS Vault v2.
 */
export function isEncryptedEnvelope(value: any): value is EncryptedPayloadEnvelope {
  return (
    value !== null &&
    typeof value === 'object' &&
    value.__format === 'DIRS_VAULT_V2' &&
    typeof value.ciphertext === 'string' &&
    typeof value.iv === 'string'
  );
}
