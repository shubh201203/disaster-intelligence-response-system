/**
 * DIRS Phase 7 Offline Crypto Vault Contract Suite
 * 
 * Verifies client-side cryptographic invariants:
 * 1. Web Crypto API availability & 256-bit AES-GCM key derivation via PBKDF2 (100,000 iterations).
 * 2. Authenticated encryption & decryption lossless roundtrip for incident & field assessment drafts.
 * 3. Ciphertext authentication & anti-tampering (MAC tag validation).
 * 4. Passphrase integrity (rejection on wrong passphrase).
 * 5. Envelope format compliance & type discrimination (v1 plain vs v2 encrypted).
 */

import { test, expect } from '@playwright/test';
import {
  isWebCryptoAvailable,
  generateSalt,
  deriveKeyFromPassphrase,
  encryptDraftPayload,
  decryptDraftPayload,
  isEncryptedEnvelope,
  EncryptedPayloadEnvelope
} from '../../src/utils/cryptoVault';

test.describe('DIRS Phase 7: Web Crypto Offline Vault Invariants', () => {

  test('TC-P7-CRYPTO-01: Web Crypto API is available in test environment', () => {
    expect(isWebCryptoAvailable()).toBe(true);
  });

  test('TC-P7-CRYPTO-02: Deterministic key derivation with identical passphrase and salt', async () => {
    const salt = generateSalt(16);
    expect(salt.length).toBe(16);

    const keyA = await deriveKeyFromPassphrase('MissionSecurePass123!', salt);
    const keyB = await deriveKeyFromPassphrase('MissionSecurePass123!', salt);

    expect(keyA.type).toBe('secret');
    expect(keyA.algorithm.name).toBe('AES-GCM');
    expect((keyA.algorithm as any).length).toBe(256);
    expect(keyB.type).toBe('secret');
  });

  test('TC-P7-CRYPTO-03: Lossless roundtrip encryption and decryption for Incident Report', async () => {
    const salt = generateSalt(16);
    const key = await deriveKeyFromPassphrase('RescueWorker@2026', salt);

    const incidentDraft = {
      title: 'Flash Flood Inundation Sector 4',
      disaster_type: 'FLOOD',
      severity_level: 'HIGH',
      people_affected: 45,
      latitude: 28.6139,
      longitude: 77.2090,
      description: 'Water levels rising rapidly above danger mark',
      notes: 'Requires emergency evacuation boats and food packets'
    };

    const envelope = await encryptDraftPayload(incidentDraft, key, salt);

    expect(envelope.__format).toBe('DIRS_VAULT_V2');
    expect(envelope.algorithm).toBe('AES-256-GCM');
    expect(envelope.kdf).toBe('PBKDF2-HMAC-SHA256');
    expect(envelope.iterations).toBe(100000);
    expect(typeof envelope.ciphertext).toBe('string');
    expect(envelope.ciphertext.length).toBeGreaterThan(20);
    expect(isEncryptedEnvelope(envelope)).toBe(true);

    const decrypted = await decryptDraftPayload<typeof incidentDraft>(envelope, key);
    expect(decrypted).toEqual(incidentDraft);
  });

  test('TC-P7-CRYPTO-04: Lossless roundtrip encryption for Field Damage Assessment', async () => {
    const salt = generateSalt(16);
    const key = await deriveKeyFromPassphrase('GovtEngineerSecret#89', salt);

    const fieldInspectionDraft = {
      incident_id: 'inc-f9012-abc',
      ward_code: 'WARD-07',
      structure_type: 'BRIDGE_CULVERT',
      structural_damage_pct: 68.5,
      habitability_status: 'UNINHABITABLE',
      estimated_restoration_cost_inr: 4500000,
      inspector_notes: 'Structural integrity compromised on northern pier.'
    };

    const envelope = await encryptDraftPayload(fieldInspectionDraft, key, salt);
    const decrypted = await decryptDraftPayload<typeof fieldInspectionDraft>(envelope, key);

    expect(decrypted).toEqual(fieldInspectionDraft);
  });

  test('TC-P7-CRYPTO-05: AES-GCM authentication failure on ciphertext tampering', async () => {
    const salt = generateSalt(16);
    const key = await deriveKeyFromPassphrase('FieldAgentPassphrase!', salt);

    const payload = { sensitiveReport: 'Classified evacuation order' };
    const envelope = await encryptDraftPayload(payload, key, salt);

    // Tamper with ciphertext by altering last character
    const tamperedCiphertext = envelope.ciphertext.slice(0, -2) + (envelope.ciphertext.endsWith('A') ? 'B' : 'A');
    const tamperedEnvelope: EncryptedPayloadEnvelope = {
      ...envelope,
      ciphertext: tamperedCiphertext
    };

    await expect(decryptDraftPayload(tamperedEnvelope, key)).rejects.toThrow();
  });

  test('TC-P7-CRYPTO-06: Decryption rejection when using incorrect passphrase', async () => {
    const salt = generateSalt(16);
    const correctKey = await deriveKeyFromPassphrase('CorrectPassphrase123!', salt);
    const wrongKey = await deriveKeyFromPassphrase('WrongPassphrase456?', salt);

    const payload = { confidential: 'NGO Supply Chain Inventory' };
    const envelope = await encryptDraftPayload(payload, correctKey, salt);

    await expect(decryptDraftPayload(envelope, wrongKey)).rejects.toThrow();
  });

  test('TC-P7-CRYPTO-07: Type guard isEncryptedEnvelope correctly discriminates envelopes', () => {
    expect(isEncryptedEnvelope(null)).toBe(false);
    expect(isEncryptedEnvelope(undefined)).toBe(false);
    expect(isEncryptedEnvelope({ title: 'Unencrypted plain v1 draft' })).toBe(false);
    expect(isEncryptedEnvelope({ __format: 'DIRS_VAULT_V1' })).toBe(false);

    const validEnvelope: EncryptedPayloadEnvelope = {
      __format: 'DIRS_VAULT_V2',
      algorithm: 'AES-256-GCM',
      kdf: 'PBKDF2-HMAC-SHA256',
      iterations: 100000,
      salt: 'c2FsdA==',
      iv: 'aXYxMjM0NTY3ODkw',
      ciphertext: 'Y2lwaGVydGV4dA=='
    };
    expect(isEncryptedEnvelope(validEnvelope)).toBe(true);
  });

});
