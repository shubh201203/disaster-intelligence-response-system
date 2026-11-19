import React, { useState } from 'react';
import { 
  ClipboardCheck, 
  MapPin, 
  Compass, 
  Send, 
  Save, 
  CheckCircle2, 
  AlertTriangle, 
  Building2, 
  Activity,
  Layers,
  DollarSign,
  WifiOff
} from 'lucide-react';
import { OperationalCard, StatusBadge, SeverityBadge } from '../design-system';
import { apiClient } from '../../api/client';
import { useOfflineDrafts } from '../../hooks/useOfflineDrafts';
import { OfflineBanner } from '../offline/OfflineBanner';
import { DraftSyncManager } from '../offline/DraftSyncManager';
import { OfflineDraft } from '../../utils/offlineDraftStore';

interface VolunteerFieldInspectionProps {
  availableIncidents?: Array<{ id: string; incident_code?: string; title: string }>;
  onInspectionSubmitted?: (res: any) => void;
}

export const VolunteerFieldInspection: React.FC<VolunteerFieldInspectionProps> = ({
  availableIncidents = [],
  onInspectionSubmitted
}) => {
  const [incidentId, setIncidentId] = useState(availableIncidents[0]?.id || '');
  const [sector, setSector] = useState('HOUSING');
  const [facilityName, setFacilityName] = useState('');
  const [damageLevel, setDamageLevel] = useState('MODERATE');
  const [isOperational, setIsOperational] = useState(false);
  const [estimatedCost, setEstimatedCost] = useState(150000);
  const [structuralNotes, setStructuralNotes] = useState('');
  const [lat, setLat] = useState<number>(13.0827);
  const [lng, setLng] = useState<number>(80.2707);
  const [confidence, setConfidence] = useState<number>(95.0);
  const [activeDraftId, setActiveDraftId] = useState<string | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const {
    drafts,
    loading: draftsLoading,
    isOnline,
    saveCurrentDraft,
    syncDraft,
    syncAllPending,
    removeDraft,
    clearCompleted
  } = useOfflineDrafts('FIELD_INSPECTION');

  const pendingCount = drafts.filter(d => d.sync_status === 'DRAFT' || d.sync_status === 'FAILED').length;

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude);
          setLng(pos.coords.longitude);
        },
        () => {
          alert('GPS unavailable. Using default field coordinates.');
        }
      );
    }
  };

  const getPayload = () => ({
    incident_id: incidentId || '00000000-0000-0000-0000-000000000001',
    sector,
    facility_name: facilityName.trim() || `${sector} Facility @ Sector 4`,
    damage_level: damageLevel,
    is_operational: isOperational,
    estimated_reconstruction_cost: Number(estimatedCost),
    structural_notes: structuralNotes.trim() || 'Field inspection performed by Level-2 volunteer responder.',
    evidence_media_urls: [],
    latitude: lat,
    longitude: lng,
    assessor_confidence: Number(confidence)
  });

  const handleSaveDraft = async () => {
    try {
      const payload = getPayload();
      const saved = await saveCurrentDraft(payload, activeDraftId);
      setActiveDraftId(saved.client_draft_id);
      setStatusMessage('Inspection assessment saved to local device draft storage.');
      setTimeout(() => setStatusMessage(null), 4000);
    } catch (e: any) {
      alert('Failed to save draft: ' + e.message);
    }
  };

  const handleLoadDraft = (draft: OfflineDraft) => {
    setActiveDraftId(draft.client_draft_id);
    const p = draft.payload;
    if (p.incident_id) setIncidentId(p.incident_id);
    if (p.sector) setSector(p.sector);
    if (p.facility_name) setFacilityName(p.facility_name);
    if (p.damage_level) setDamageLevel(p.damage_level);
    if (p.is_operational !== undefined) setIsOperational(p.is_operational);
    if (p.estimated_reconstruction_cost !== undefined) setEstimatedCost(p.estimated_reconstruction_cost);
    if (p.structural_notes) setStructuralNotes(p.structural_notes);
    if (p.latitude) setLat(p.latitude);
    if (p.longitude) setLng(p.longitude);
    if (p.assessor_confidence !== undefined) setConfidence(p.assessor_confidence);
    setStatusMessage(`Loaded inspection draft #${draft.client_draft_id.slice(0, 8)} into form.`);
    setTimeout(() => setStatusMessage(null), 3000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    const payload = getPayload();

    if (!navigator.onLine) {
      try {
        await saveCurrentDraft(payload, activeDraftId);
        setStatusMessage('Offline Mode Active: Inspection queued locally in IndexedDB for auto-sync.');
      } catch (err: any) {
        alert('Failed to queue offline inspection: ' + err.message);
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    try {
      const res = await apiClient.post('/recovery/damage-assessments/field-inspection', {
        ...payload,
        client_draft_id: activeDraftId
      });
      if (activeDraftId) {
        await removeDraft(activeDraftId);
      }
      setStatusMessage(`Inspection submitted successfully! Assessment Code: ${res.data?.assessment_code || 'Recorded'}. Status: PENDING_VERIFICATION.`);
      setFacilityName('');
      setStructuralNotes('');
      setActiveDraftId(undefined);
      if (onInspectionSubmitted) {
        onInspectionSubmitted(res.data);
      }
    } catch (err: any) {
      if (!err.response || err.message?.includes('Network Error')) {
        await saveCurrentDraft(payload, activeDraftId);
        setStatusMessage('Network dropped during submission: Inspection saved locally in IndexedDB.');
      } else {
        alert('Inspection submission error: ' + (err.response?.data?.detail || err.message));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      <OfflineBanner
        pendingDraftCount={pendingCount}
        onSyncNow={syncAllPending}
      />

      <OperationalCard
        title="Field Damage & Structural Inspection"
        subtitle="Submit engineering and field observation reports to Government Command verification pipeline"
        headerAction={
          <div className="flex items-center gap-2">
            {activeDraftId && (
              <span className="text-[10px] text-cyan-ops bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800">
                EDITING DRAFT
              </span>
            )}
            <button
              type="button"
              onClick={handleSaveDraft}
              className="px-2.5 py-1 bg-obsidian-800 hover:bg-obsidian-750 text-slate-300 rounded border border-obsidian-700 flex items-center gap-1 transition"
            >
              <Save className="w-3.5 h-3.5 text-amber-ops" />
              <span>Save Draft</span>
            </button>
          </div>
        }
      >
        {statusMessage && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-950/80 border border-emerald-700 text-emerald-300 flex items-center justify-between">
            <span>{statusMessage}</span>
            <button type="button" onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-white font-bold ml-2">×</button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Target Incident
              </label>
              {availableIncidents.length > 0 ? (
                <select
                  value={incidentId}
                  onChange={(e) => setIncidentId(e.target.value)}
                  className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-amber-ops"
                >
                  {availableIncidents.map((inc) => (
                    <option key={inc.id} value={inc.id}>
                      {inc.incident_code || inc.id.slice(0, 8)} — {inc.title.slice(0, 30)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  placeholder="Enter Incident UUID"
                  value={incidentId}
                  onChange={(e) => setIncidentId(e.target.value)}
                  className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-amber-ops"
                />
              )}
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Sector Classification
              </label>
              <select
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 font-bold focus:outline-none focus:border-amber-ops"
              >
                <option value="HOUSING">HOUSING (Residential/Shelter)</option>
                <option value="HEALTH">HEALTH (Clinic/Hospital)</option>
                <option value="EDUCATION">EDUCATION (School/College)</option>
                <option value="WASH">WASH (Water & Sanitation)</option>
                <option value="TRANSPORT">TRANSPORT (Roads/Bridges)</option>
                <option value="POWER">POWER (Grid & Transformers)</option>
                <option value="TELECOM">TELECOM (Cell Tower/Fiber)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Damage Rating
              </label>
              <select
                value={damageLevel}
                onChange={(e) => setDamageLevel(e.target.value)}
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 font-bold focus:outline-none focus:border-amber-ops"
              >
                <option value="NONE">NONE (Intact)</option>
                <option value="MINOR">MINOR (&lt; 20% loss)</option>
                <option value="MODERATE">MODERATE (20–50% loss)</option>
                <option value="SEVERE">SEVERE (50–80% loss)</option>
                <option value="DESTROYED">DESTROYED (&gt; 80% loss)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Facility / Structure Name
              </label>
              <input
                type="text"
                required
                value={facilityName}
                onChange={(e) => setFacilityName(e.target.value)}
                placeholder="e.g. Community Health Center Ward 4, Substation 2"
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-amber-ops"
              />
            </div>

            <div className="flex items-center gap-3 pt-6">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isOperational}
                  onChange={(e) => setIsOperational(e.target.checked)}
                  className="w-4 h-4 rounded bg-obsidian-900 border-obsidian-700 text-amber-ops focus:ring-0"
                />
                <span className="text-[11px] text-slate-200 font-bold">Currently Operational</span>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Field Structural Observation & Notes
            </label>
            <textarea
              required
              rows={3}
              value={structuralNotes}
              onChange={(e) => setStructuralNotes(e.target.value)}
              placeholder="Detail structural integrity: collapsed pillars, wall fissures, mud accumulation, standing water depth, transformer burns..."
              className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-amber-ops"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Estimated Reconstruction Cost (INR)
              </label>
              <input
                type="number"
                min="0"
                step="5000"
                value={estimatedCost}
                onChange={(e) => setEstimatedCost(parseFloat(e.target.value) || 0)}
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 font-bold focus:outline-none focus:border-amber-ops"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-[11px] text-slate-400 uppercase tracking-wider">
                  Coordinates (Lat, Lng)
                </label>
                <button
                  type="button"
                  onClick={getCurrentLocation}
                  className="text-[10px] text-amber-ops hover:underline flex items-center gap-1"
                >
                  <Compass className="w-3 h-3" /> GPS
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="any"
                  value={lat}
                  onChange={(e) => setLat(parseFloat(e.target.value))}
                  className="bg-obsidian-900 border border-obsidian-750 rounded px-2.5 py-2 text-slate-100"
                />
                <input
                  type="number"
                  step="any"
                  value={lng}
                  onChange={(e) => setLng(parseFloat(e.target.value))}
                  className="bg-obsidian-900 border border-obsidian-750 rounded px-2.5 py-2 text-slate-100"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Assessor Confidence: {confidence.toFixed(0)}%
              </label>
              <input
                type="range"
                min="30"
                max="100"
                step="5"
                value={confidence}
                onChange={(e) => setConfidence(parseFloat(e.target.value))}
                className="w-full mt-2 accent-amber-500 cursor-pointer"
              />
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full sm:flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-lg text-xs font-mono transition flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
            >
              {isSubmitting ? (
                <span>Submitting to Government Queue...</span>
              ) : (
                <>
                  <ClipboardCheck className="w-4 h-4" />
                  <span>
                    {!isOnline ? 'QUEUE OFFLINE ASSESSMENT (INDEXEDDB)' : 'SUBMIT FIELD INSPECTION ASSESSMENT'}
                  </span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleSaveDraft}
              className="w-full sm:w-auto px-4 py-3 bg-obsidian-800 hover:bg-obsidian-750 text-slate-200 rounded-lg text-xs font-mono border border-obsidian-700 flex items-center justify-center gap-1.5 transition"
            >
              <Save className="w-4 h-4 text-amber-ops" />
              <span>Save Local Draft</span>
            </button>
          </div>
        </form>
      </OperationalCard>

      <DraftSyncManager
        drafts={drafts}
        loading={draftsLoading}
        isOnline={isOnline}
        onSyncDraft={syncDraft}
        onSyncAll={syncAllPending}
        onDeleteDraft={removeDraft}
        onClearCompleted={clearCompleted}
        onLoadDraft={handleLoadDraft}
        title="Local Field Inspection Drafts (IndexedDB)"
      />
    </div>
  );
};
