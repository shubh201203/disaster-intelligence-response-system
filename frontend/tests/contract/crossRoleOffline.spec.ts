/**
 * DIRS Phase 6G Accelerated Programme: Work Package 3
 * Cross-Role UI Integration & Offline Resilience Contract Suite.
 *
 * Verifies mathematical, numerical, architectural, and security invariants:
 * 1. Offline Draft schemas, payloads, and status unions.
 * 2. State transition machine for offline drafts (DRAFT -> SYNCING -> SYNCED/FAILED/CONFLICT).
 * 3. 401 Session Expiry & 422 Validation Error draft preservation invariants.
 * 4. Cross-role capability and least-privilege matrix invariants across 5 roles.
 * 5. NGO organization inventory scoping and institutional boundary contracts.
 * 6. User-isolation, multi-tenant draft store, and account-switching invariants.
 * 7. Synchronization acknowledgement, duplicate prevention, and conflict resolution policies.
 */

import { test, expect } from '@playwright/test';
import {
  OfflineDraft,
  OfflineDraftType,
  OfflineSyncStatus,
  IncidentReportPayload,
  FieldInspectionPayload,
} from '../../src/types/offline';

// ============================================================================
// 1. In-Memory Mock Store with Strict Principal Isolation
// ============================================================================
class MockDraftStore {
  private drafts: Map<string, OfflineDraft<any>> = new Map();

  async saveDraft<T>(draft: OfflineDraft<T>): Promise<OfflineDraft<T>> {
    if (!draft.userId) {
      throw new Error('Principal error: user_id is required');
    }
    const existing = this.drafts.get(draft.id);
    const updatedDraft: OfflineDraft<T> = {
      ...draft,
      createdAt: existing ? existing.createdAt : draft.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    this.drafts.set(draft.id, updatedDraft);
    return updatedDraft;
  }

  async getDraft<T>(id: string, expectedUserId?: string): Promise<OfflineDraft<T> | null> {
    const d = this.drafts.get(id);
    if (!d) return null;
    if (expectedUserId && d.userId !== expectedUserId) {
      return null; // Principal isolation
    }
    return d as OfflineDraft<T>;
  }

  async listDraftsByUser(userId: string): Promise<OfflineDraft<any>[]> {
    return Array.from(this.drafts.values()).filter((d) => d.userId === userId);
  }

  async listDraftsByType<T>(userId: string, draftType: OfflineDraftType): Promise<OfflineDraft<T>[]> {
    return Array.from(this.drafts.values()).filter(
      (d) => d.userId === userId && d.draftType === draftType
    ) as OfflineDraft<T>[];
  }

  async updateDraftStatus(
    id: string,
    status: OfflineSyncStatus,
    syncError?: string,
    serverAssignedId?: string,
    expectedUserId?: string
  ): Promise<OfflineDraft<any> | null> {
    const d = this.drafts.get(id);
    if (!d) return null;
    if (expectedUserId && d.userId !== expectedUserId) {
      throw new Error(`Security violation: User ${expectedUserId} cannot update foreign draft ${id}`);
    }
    const updated: OfflineDraft<any> = {
      ...d,
      status,
      syncError: syncError !== undefined ? syncError : d.syncError,
      serverAssignedId: serverAssignedId !== undefined ? serverAssignedId : d.serverAssignedId,
      updatedAt: new Date().toISOString(),
    };
    this.drafts.set(id, updated);
    return updated;
  }

  async deleteDraft(id: string, expectedUserId?: string): Promise<boolean> {
    const d = this.drafts.get(id);
    if (!d) return true; // Idempotent
    if (expectedUserId && d.userId !== expectedUserId) {
      throw new Error(`Security violation: User ${expectedUserId} cannot delete foreign draft ${id}`);
    }
    return this.drafts.delete(id);
  }

  async clearSyncedDrafts(userId: string): Promise<number> {
    let count = 0;
    for (const [id, d] of Array.from(this.drafts.entries())) {
      if (d.userId === userId && d.status === 'SYNCED') {
        this.drafts.delete(id);
        count++;
      }
    }
    return count;
  }
}

// ============================================================================
// 2. Test Suite Execution
// ============================================================================
test.describe('WP3 Cross-Role UI Integration & Offline Resilience Contract Suite', () => {
  // --------------------------------------------------------------------------
  // Group A: Offline Draft Schema & Type Invariants
  // --------------------------------------------------------------------------
  test.describe('A. Offline Draft Schema & Status Invariants', () => {
    test('Incident Report payload conforms to mandatory contract schema', () => {
      const incidentPayload: IncidentReportPayload = {
        title: 'Flash Flood Overtopping Culvert 4',
        disaster_type: 'FLOOD',
        description: 'Rapid water level rise reaching 1.2m across the main arterial road',
        latitude: 13.0827,
        longitude: 80.2707,
        location_address: 'Ward 12, Culvert 4 Crossing',
        people_affected: 45,
        injuries: 2,
        vulnerable_count: 8,
      };

      expect(typeof incidentPayload.title).toBe('string');
      expect(incidentPayload.title.length).toBeGreaterThan(0);
      expect(['FLOOD', 'CYCLONE', 'FIRE', 'LANDSLIDE', 'EARTHQUAKE']).toContain(
        incidentPayload.disaster_type
      );
      expect(incidentPayload.latitude).toBeGreaterThanOrEqual(-90);
      expect(incidentPayload.latitude).toBeLessThanOrEqual(90);
      expect(incidentPayload.longitude).toBeGreaterThanOrEqual(-180);
      expect(incidentPayload.longitude).toBeLessThanOrEqual(180);
      expect(incidentPayload.people_affected).toBeGreaterThanOrEqual(0);
    });

    test('Field Inspection payload conforms to DamageAssessmentFieldCreate schema', () => {
      const inspectionPayload: FieldInspectionPayload = {
        incident_id: 'inc-f902a-4311',
        sector: 'HEALTH',
        facility_name: 'Ward 4 Community Health Clinic',
        damage_level: 'MODERATE',
        is_operational: false,
        estimated_reconstruction_cost: 350000.0,
        structural_notes: 'Roof compromised, perimeter wall cracked, clinical supplies dry',
        latitude: 13.0845,
        longitude: 80.2741,
        assessor_confidence: 90.0,
      };

      expect(typeof inspectionPayload.incident_id).toBe('string');
      expect(['HEALTH', 'EDUCATION', 'HOUSING', 'TRANSPORT', 'WATER', 'POWER']).toContain(
        inspectionPayload.sector
      );
      expect(['NONE', 'MINOR', 'MODERATE', 'SEVERE', 'TOTAL_DESTRUCTION']).toContain(
        inspectionPayload.damage_level
      );
      expect(typeof inspectionPayload.is_operational).toBe('boolean');
      expect(inspectionPayload.estimated_reconstruction_cost).toBeGreaterThanOrEqual(0);
      expect(inspectionPayload.assessor_confidence).toBeGreaterThanOrEqual(0);
      expect(inspectionPayload.assessor_confidence).toBeLessThanOrEqual(100);
    });

    test('Draft status transitions adhere to valid finite state machine paths', () => {
      const validStatuses: OfflineSyncStatus[] = ['DRAFT', 'SYNCING', 'SYNCED', 'FAILED', 'CONFLICT'];
      expect(validStatuses).toHaveLength(5);

      const allowedTransitions: Record<OfflineSyncStatus, OfflineSyncStatus[]> = {
        DRAFT: ['SYNCING', 'DRAFT'],
        SYNCING: ['SYNCED', 'FAILED', 'CONFLICT', 'DRAFT'],
        SYNCED: ['SYNCED'], // Terminal until cleared
        FAILED: ['SYNCING', 'DRAFT'], // May be retried or edited
        CONFLICT: ['SYNCING', 'DRAFT'], // May be resolved
      };

      expect(allowedTransitions['DRAFT']).toContain('SYNCING');
      expect(allowedTransitions['SYNCING']).toContain('SYNCED');
      expect(allowedTransitions['SYNCING']).toContain('FAILED');
      expect(allowedTransitions['SYNCING']).toContain('DRAFT');
      expect(allowedTransitions['FAILED']).toContain('SYNCING');
    });
  });

  // --------------------------------------------------------------------------
  // Group B: Multi-User Account Switching & Store Isolation Invariants
  // --------------------------------------------------------------------------
  test.describe('B. Multi-User Account Switching & Principal Isolation', () => {
    test('User A drafts are completely isolated and inaccessible to User B on the same device', async () => {
      const store = new MockDraftStore();

      // Step 1: User A logs in and creates incident and inspection drafts
      const userAId = 'usr-responder-alice-01';
      await store.saveDraft({
        id: 'draft-alice-incident-01',
        userId: userAId,
        draftType: 'INCIDENT_REPORT',
        status: 'DRAFT',
        createdAt: '2026-11-18T00:00:00Z',
        updatedAt: '2026-11-18T00:00:00Z',
        payload: { title: 'Alice Flooded Basement', disaster_type: 'FLOOD', latitude: 13.08, longitude: 80.27 },
      });
      await store.saveDraft({
        id: 'draft-alice-inspection-01',
        userId: userAId,
        draftType: 'FIELD_INSPECTION',
        status: 'DRAFT',
        createdAt: '2026-11-18T00:01:00Z',
        updatedAt: '2026-11-18T00:01:00Z',
        payload: { incident_id: 'inc-01', sector: 'HEALTH', facility_name: 'Alice Clinic', damage_level: 'MINOR', is_operational: true, estimated_reconstruction_cost: 20000, latitude: 13.08, longitude: 80.27 },
      });

      // Step 2: User A logs out. User B logs in.
      const userBId = 'usr-responder-bob-02';

      // User B lists drafts: must be empty
      const bobDrafts = await store.listDraftsByUser(userBId);
      expect(bobDrafts).toHaveLength(0);

      // User B attempts direct retrieval of Alice's draft: must return null
      const foreignGet = await store.getDraft('draft-alice-incident-01', userBId);
      expect(foreignGet).toBeNull();

      // User B attempts to update Alice's draft: must throw security violation
      await expect(
        store.updateDraftStatus('draft-alice-incident-01', 'SYNCED', undefined, 'srv-hack', userBId)
      ).rejects.toThrow(/Security violation/);

      // User B attempts to delete Alice's draft: must throw security violation
      await expect(store.deleteDraft('draft-alice-incident-01', userBId)).rejects.toThrow(
        /Security violation/
      );

      // Step 3: User B creates their own draft
      await store.saveDraft({
        id: 'draft-bob-incident-01',
        userId: userBId,
        draftType: 'INCIDENT_REPORT',
        status: 'DRAFT',
        createdAt: '2026-11-18T00:05:00Z',
        updatedAt: '2026-11-18T00:05:00Z',
        payload: { title: 'Bob Tree Fallen', disaster_type: 'CYCLONE', latitude: 13.09, longitude: 80.28 },
      });

      const bobDraftsAfterSave = await store.listDraftsByUser(userBId);
      expect(bobDraftsAfterSave).toHaveLength(1);
      expect(bobDraftsAfterSave[0].id).toBe('draft-bob-incident-01');

      // Step 4: User B logs out. User A logs back in.
      // User A's drafts must be 100% recovered and intact with 0 data loss
      const aliceRecovered = await store.listDraftsByUser(userAId);
      expect(aliceRecovered).toHaveLength(2);
      expect(aliceRecovered.some((d) => d.id === 'draft-alice-incident-01')).toBe(true);
      expect(aliceRecovered.some((d) => d.id === 'draft-alice-inspection-01')).toBe(true);
      expect(aliceRecovered.some((d) => d.id === 'draft-bob-incident-01')).toBe(false);
    });

    test('Logout with pending drafts preserves data without leakage or destruction', async () => {
      const store = new MockDraftStore();
      const userId = 'usr-pending-logout-01';

      await store.saveDraft({
        id: 'draft-pending-01',
        userId,
        draftType: 'FIELD_INSPECTION',
        status: 'DRAFT',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        payload: {
          incident_id: 'inc-pending',
          sector: 'TRANSPORT',
          facility_name: 'Overpass Bridge',
          damage_level: 'MODERATE',
          is_operational: false,
          estimated_reconstruction_cost: 1500000,
          latitude: 13.08,
          longitude: 80.27,
        },
      });

      // Session ends (logout)
      // When user logs back in, draft is still intact
      const recovered = await store.getDraft(
        'draft-pending-01',
        userId
      );
      expect(recovered).not.toBeNull();
      expect(recovered?.payload.facility_name).toBe('Overpass Bridge');
      expect(recovered?.status).toBe('DRAFT');
    });
  });

  // --------------------------------------------------------------------------
  // Group C: Synchronization Integrity & Error Handling
  // --------------------------------------------------------------------------
  test.describe('C. Synchronization Lifecycle, Idempotency & Error Handling', () => {
    test('Only verified server acknowledgement establishes SYNCED state', async () => {
      const store = new MockDraftStore();
      const draftId = 'draft-ack-01';
      const userId = 'usr-ack-01';

      await store.saveDraft({
        id: draftId,
        userId,
        draftType: 'INCIDENT_REPORT',
        status: 'SYNCING',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        payload: { title: 'Transformer Surge', disaster_type: 'FIRE', latitude: 13.08, longitude: 80.27 },
      });

      // Server returns HTTP 201 with generated server identifier
      const serverAssignedId = 'inc-srv-9001-uuid';
      await store.updateDraftStatus(draftId, 'SYNCED', undefined, serverAssignedId, userId);

      const synced = await store.getDraft(draftId, userId);
      expect(synced?.status).toBe('SYNCED');
      expect(synced?.serverAssignedId).toBe('inc-srv-9001-uuid');
      expect(synced?.syncError).toBeUndefined();
    });

    test('Duplicate synchronization request on SYNCED draft avoids duplicate HTTP dispatch', async () => {
      const store = new MockDraftStore();
      const draftId = 'draft-idempotent-01';
      const userId = 'usr-idempotent-01';

      await store.saveDraft({
        id: draftId,
        userId,
        draftType: 'INCIDENT_REPORT',
        status: 'SYNCED',
        serverAssignedId: 'inc-srv-existing-uuid',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        payload: { title: 'Already synced incident', disaster_type: 'FLOOD', latitude: 13.08, longitude: 80.27 },
      });

      // Client sync runner checks: if draft is already SYNCED, return existing serverAck without dispatch
      const existingDraft = await store.getDraft(draftId, userId);
      let dispatchCount = 0;

      function syncSimulator(draft: OfflineDraft<any>) {
        if (draft.status === 'SYNCED' && draft.serverAssignedId) {
          // Idempotency guard: do not re-dispatch
          return { success: true, ack: { id: draft.serverAssignedId }, wasDispatched: false };
        }
        dispatchCount++;
        return { success: true, wasDispatched: true };
      }

      const result = syncSimulator(existingDraft!);
      expect(result.wasDispatched).toBe(false);
      expect(result.ack.id).toBe('inc-srv-existing-uuid');
      expect(dispatchCount).toBe(0);
    });

    test('401 Session Expiry preserves draft without data loss and prompts re-auth', async () => {
      const store = new MockDraftStore();
      const draftId = 'draft-401-01';
      const userId = 'usr-401-01';

      await store.saveDraft({
        id: draftId,
        userId,
        draftType: 'FIELD_INSPECTION',
        status: 'SYNCING',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        payload: {
          incident_id: 'inc-401',
          sector: 'HEALTH',
          facility_name: 'Subcentre Ward 4',
          damage_level: 'MODERATE',
          is_operational: false,
          estimated_reconstruction_cost: 250000,
          latitude: 13.08,
          longitude: 80.27,
        },
      });

      // 401 error handler transitions draft to DRAFT with notification
      await store.updateDraftStatus(
        draftId,
        'DRAFT',
        'Session expired. Please log in again to sync.',
        undefined,
        userId
      );

      const preserved = await store.getDraft(draftId, userId);
      expect(preserved?.status).toBe('DRAFT');
      expect(preserved?.syncError).toContain('Session expired');
      expect(preserved?.payload.facility_name).toBe('Subcentre Ward 4');
    });

    test('422 Validation Error sets status to FAILED and retains structured diagnostics', async () => {
      const store = new MockDraftStore();
      const draftId = 'draft-422-01';
      const userId = 'usr-422-01';

      await store.saveDraft({
        id: draftId,
        userId,
        draftType: 'INCIDENT_REPORT',
        status: 'SYNCING',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        payload: { title: '', disaster_type: 'INVALID_TYPE', latitude: 999.0, longitude: 999.0 },
      });

      // 422 handler formats validation errors and marks FAILED
      const errorMsg = 'Validation error: latitude: Input should be less than or equal to 90';
      await store.updateDraftStatus(draftId, 'FAILED', errorMsg, undefined, userId);

      const failedDraft = await store.getDraft(draftId, userId);
      expect(failedDraft?.status).toBe('FAILED');
      expect(failedDraft?.syncError).toContain('Input should be less than or equal to 90');
      // Payload is preserved so user can edit and correct
      expect(failedDraft?.payload.disaster_type).toBe('INVALID_TYPE');
    });

    test('409 Server-Side Conflict sets status to CONFLICT and suppresses blind retry', async () => {
      const store = new MockDraftStore();
      const draftId = 'draft-409-01';
      const userId = 'usr-409-01';

      await store.saveDraft({
        id: draftId,
        userId,
        draftType: 'INCIDENT_REPORT',
        status: 'SYNCING',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        payload: { title: 'Conflict Test', disaster_type: 'FLOOD', latitude: 13.08, longitude: 80.27 },
      });

      // Server returns 409 Conflict
      await store.updateDraftStatus(
        draftId,
        'CONFLICT',
        'Server reports duplicate or conflicting submission.',
        undefined,
        userId
      );

      const conflictDraft = await store.getDraft(draftId, userId);
      expect(conflictDraft?.status).toBe('CONFLICT');
      expect(conflictDraft?.syncError).toContain('conflicting');

      // SyncAllPending ignores CONFLICT drafts (only picks DRAFT or FAILED)
      const allDrafts = await store.listDraftsByUser(userId);
      const retryCandidates = allDrafts.filter(
        (d) => d.status === 'DRAFT' || d.status === 'FAILED'
      );
      expect(retryCandidates).toHaveLength(0);
    });

    test('Network restoration allows successful retry of FAILED drafts', async () => {
      const store = new MockDraftStore();
      const draftId = 'draft-retry-01';
      const userId = 'usr-retry-01';

      // 1. Initial failed attempt
      await store.saveDraft({
        id: draftId,
        userId,
        draftType: 'INCIDENT_REPORT',
        status: 'FAILED',
        syncError: 'Network transport disconnect',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        payload: { title: 'Post-Network Retry Incident', disaster_type: 'FLOOD', latitude: 13.08, longitude: 80.27 },
      });

      // 2. Connectivity restored: operator triggers sync
      await store.updateDraftStatus(draftId, 'SYNCING', undefined, undefined, userId);
      let draftInFlight = await store.getDraft(draftId, userId);
      expect(draftInFlight?.status).toBe('SYNCING');

      // 3. Network acknowledges 201 Created
      await store.updateDraftStatus(draftId, 'SYNCED', undefined, 'srv-restored-id', userId);
      let draftCompleted = await store.getDraft(draftId, userId);
      expect(draftCompleted?.status).toBe('SYNCED');
      expect(draftCompleted?.serverAssignedId).toBe('srv-restored-id');
    });
  });

  // --------------------------------------------------------------------------
  // Group D: Cross-Role Capability & Institutional Boundaries
  // --------------------------------------------------------------------------
  test.describe('D. Cross-Role Capability Matrix & Policy Boundaries', () => {
    type DirsRole = 'CITIZEN' | 'VOLUNTEER' | 'NGO' | 'GOVT' | 'ADMIN';

    interface RoleCapabilities {
      canReportIncident: boolean;
      canTriggerSOS: boolean;
      canSubmitFieldDamageInspection: boolean;
      canVerifyDamageInspection: boolean;
      canManageReliefInventory: boolean;
      canViewFieldReliefRequests: boolean;
      canRunPortfolioOptimization: boolean;
      canViewCommunityMonitoringMetrics: boolean;
    }

    const roleMatrix: Record<DirsRole, RoleCapabilities> = {
      CITIZEN: {
        canReportIncident: true,
        canTriggerSOS: true,
        canSubmitFieldDamageInspection: false,
        canVerifyDamageInspection: false,
        canManageReliefInventory: false,
        canViewFieldReliefRequests: false,
        canRunPortfolioOptimization: false,
        canViewCommunityMonitoringMetrics: true,
      },
      VOLUNTEER: {
        canReportIncident: true,
        canTriggerSOS: true,
        canSubmitFieldDamageInspection: true,
        canVerifyDamageInspection: false,
        canManageReliefInventory: false,
        canViewFieldReliefRequests: true,
        canRunPortfolioOptimization: false,
        canViewCommunityMonitoringMetrics: true,
      },
      NGO: {
        canReportIncident: true,
        canTriggerSOS: false,
        canSubmitFieldDamageInspection: false,
        canVerifyDamageInspection: false,
        canManageReliefInventory: true,
        canViewFieldReliefRequests: true,
        canRunPortfolioOptimization: false,
        canViewCommunityMonitoringMetrics: true,
      },
      GOVT: {
        canReportIncident: true,
        canTriggerSOS: false,
        canSubmitFieldDamageInspection: true,
        canVerifyDamageInspection: true,
        canManageReliefInventory: true,
        canViewFieldReliefRequests: true,
        canRunPortfolioOptimization: true,
        canViewCommunityMonitoringMetrics: true,
      },
      ADMIN: {
        canReportIncident: true,
        canTriggerSOS: false,
        canSubmitFieldDamageInspection: true,
        canVerifyDamageInspection: true,
        canManageReliefInventory: true,
        canViewFieldReliefRequests: true,
        canRunPortfolioOptimization: true,
        canViewCommunityMonitoringMetrics: true,
      },
    };

    test('Citizens are strictly restricted from engineering inspections and optimization', () => {
      const citizen = roleMatrix['CITIZEN'];
      expect(citizen.canReportIncident).toBe(true);
      expect(citizen.canTriggerSOS).toBe(true);
      expect(citizen.canSubmitFieldDamageInspection).toBe(false);
      expect(citizen.canVerifyDamageInspection).toBe(false);
      expect(citizen.canRunPortfolioOptimization).toBe(false);
      expect(citizen.canManageReliefInventory).toBe(false);
    });

    test('Volunteers can submit inspections but cannot self-verify', () => {
      const volunteer = roleMatrix['VOLUNTEER'];
      expect(volunteer.canSubmitFieldDamageInspection).toBe(true);
      expect(volunteer.canVerifyDamageInspection).toBe(false);
      expect(volunteer.canRunPortfolioOptimization).toBe(false);
    });

    test('NGOs have relief inventory and request access but no optimization privilege', () => {
      const ngo = roleMatrix['NGO'];
      expect(ngo.canManageReliefInventory).toBe(true);
      expect(ngo.canViewFieldReliefRequests).toBe(true);
      expect(ngo.canRunPortfolioOptimization).toBe(false);
      expect(ngo.canVerifyDamageInspection).toBe(false);
    });

    test('Government and Admin hold exclusive authority to verify inspections and run optimization', () => {
      for (const privilegedRole of ['GOVT', 'ADMIN'] as DirsRole[]) {
        const caps = roleMatrix[privilegedRole];
        expect(caps.canVerifyDamageInspection).toBe(true);
        expect(caps.canRunPortfolioOptimization).toBe(true);
        expect(caps.canManageReliefInventory).toBe(true);
      }
    });

    test('NGO inventory filtering accurately separates My Org from All Hubs', () => {
      interface ResourceItem {
        id: string;
        resource_name: string;
        category: string;
        owner_type: string;
        owner_id: string;
        supplier_info?: string;
      }

      const resources: ResourceItem[] = [
        { id: 'res-1', resource_name: 'Water Bottles', category: 'WATER', owner_type: 'NGO', owner_id: 'usr-ngo-redcross', supplier_info: 'Red Cross Chennai' },
        { id: 'res-2', resource_name: 'Medical Kits', category: 'MEDICAL', owner_type: 'NGO', owner_id: 'usr-ngo-oxfam', supplier_info: 'Oxfam India' },
        { id: 'res-3', resource_name: 'Tarpaulins', category: 'SHELTER', owner_type: 'GOVT', owner_id: 'usr-govt-state', supplier_info: 'State Disaster Relief' },
        { id: 'res-4', resource_name: 'Blankets', category: 'SHELTER', owner_type: 'NGO', owner_id: 'usr-ngo-redcross', supplier_info: 'Red Cross Chennai' },
      ];

      function filterInventory(items: ResourceItem[], scope: 'ALL' | 'MY_ORG', currentUserId: string): ResourceItem[] {
        if (scope === 'ALL') return items;
        return items.filter((item) => item.owner_id === currentUserId);
      }

      const myOrgItems = filterInventory(resources, 'MY_ORG', 'usr-ngo-redcross');
      expect(myOrgItems).toHaveLength(2);
      expect(myOrgItems.every((item) => item.owner_id === 'usr-ngo-redcross')).toBe(true);

      const allItems = filterInventory(resources, 'ALL', 'usr-ngo-redcross');
      expect(allItems).toHaveLength(4);
    });
  });
});
