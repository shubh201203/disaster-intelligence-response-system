import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { 
  Users, 
  ShieldCheck, 
  MapPin, 
  Navigation, 
  CheckCircle2, 
  Clock, 
  Truck,
  AlertTriangle,
  Radio,
  Check,
  Award,
  ChevronRight,
  ClipboardCheck,
  Building2,
  Activity
} from 'lucide-react';
import { 
  OperationalCard, 
  PageHeader, 
  StatusBadge, 
  SeverityBadge, 
  KPIStat,
  NavigationModal 
} from '../../components/design-system';
import { VolunteerFieldInspection } from '../../components/volunteer/VolunteerFieldInspection';
import { IncidentEvidenceViewer } from '../../components/incident/IncidentEvidenceViewer';
import { OfflineBanner } from '../../components/offline/OfflineBanner';
import { useOfflineDrafts } from '../../hooks/useOfflineDrafts';
import { useAuth } from '../../context/AuthContext';

export const VolunteerDashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'MISSIONS' | 'FIELD_INSPECTION'>('MISSIONS');
  const [isAvailable, setIsAvailable] = useState(true);
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  const { drafts, syncAllPending } = useOfflineDrafts('FIELD_INSPECTION');
  const pendingInspectionDrafts = drafts.filter(d => d.sync_status === 'DRAFT' || d.sync_status === 'FAILED').length;

  const { data: userProfile } = useQuery({
    queryKey: ['volunteer-me', user?.id],
    queryFn: async () => {
      const res = await apiClient.get('/volunteers/me');
      return res.data;
    }
  });

  const { data: myTasks = [], refetch: refetchMyTasks } = useQuery({
    queryKey: ['volunteer-my-tasks', user?.id],
    queryFn: async () => {
      const res = await apiClient.get('/volunteers/my-tasks');
      return res.data;
    }
  });

  const { data: incidents = [] } = useQuery({
    queryKey: ['incidents-volunteer', user?.id],
    queryFn: async () => {
      const res = await apiClient.get('/incidents?status=VERIFIED');
      return res.data;
    }
  });

  const { data: submittedAssessments = [], refetch: refetchAssessments } = useQuery({
    queryKey: ['volunteer-submitted-assessments'],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/recovery/assessments');
        return res.data;
      } catch (e) {
        return [];
      }
    }
  });

  // Find active task assigned to this volunteer (prefer active non-completed)
  const activeTask = myTasks.find((t: any) => t.status !== 'COMPLETED' && t.status !== 'REJECTED') || myTasks[0] || null;
  const activeTaskStatus = activeTask?.status || 'ASSIGNED';

  const pipelineSteps = ['ASSIGNED', 'ACCEPTED', 'EN_ROUTE', 'ARRIVED', 'RESCUE_STARTED', 'COMPLETED'];
  const currentStepIdx = pipelineSteps.indexOf(activeTaskStatus);

  const [claimLoadingId, setClaimLoadingId] = useState<string | null>(null);
  const [claimError, setClaimError] = useState<string | null>(null);

  const handleStatusTransition = async (targetStatus: string) => {
    if (!activeTask?.id) return;
    setTransitionError(null);
    try {
      await apiClient.post(`/volunteers/tasks/${activeTask.id}/status?target_status=${targetStatus}`);
      refetchMyTasks();
    } catch (e: any) {
      setTransitionError(`Status transition failed: ${e.response?.data?.detail || e.message}`);
    }
  };

  const handleClaimIncident = async (incidentId: string) => {
    setClaimError(null);
    setClaimLoadingId(incidentId);
    try {
      await apiClient.post(`/volunteers/incidents/${incidentId}/claim`);
      refetchMyTasks();
    } catch (e: any) {
      setClaimError(e.response?.data?.detail || 'Failed to claim incident task.');
    } finally {
      setClaimLoadingId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12 font-sans">
      <OfflineBanner
        pendingDraftCount={pendingInspectionDrafts}
        onSyncNow={syncAllPending}
      />

      {/* Top Page Header */}
      <PageHeader
        title="VOLUNTEER RESPONDER HUB"
        subtitle="Field Task Dispatch, Tactical Rescue Pipeline & Infrastructure Damage Inspection"
        icon={Users}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
            RESPONDER READY
          </span>
        }
        actions={
          <button
            type="button"
            onClick={() => setIsAvailable(!isAvailable)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold transition border ${
              isAvailable
                ? 'bg-emerald-950/80 text-emerald-400 border-emerald-700'
                : 'bg-obsidian-850 text-slate-400 border-obsidian-700'
            }`}
          >
            {isAvailable ? '● ON DUTY & DISPATCHABLE' : '○ OFF DUTY'}
          </button>
        }
      />

      {/* Volunteer Responder Profile Card */}
      <div className="bg-obsidian-850 border border-obsidian-700 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-mono font-bold text-slate-100">
                {userProfile?.full_name || 'Volunteer Responder #042'}
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                CERTIFIED LEVEL-2
              </span>
            </div>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Specialization: Flood Rescue & Rapid Extraction • Vehicle: 4x4 High-Clearance Truck
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="p-2.5 bg-obsidian-900 rounded-lg border border-obsidian-750 text-center">
            <span className="text-[10px] text-slate-500 block uppercase">Operational State</span>
            <span className={`text-xs font-bold ${isAvailable ? 'text-emerald-400' : 'text-slate-400'}`}>
              {isAvailable ? 'AVAILABLE' : 'OFFLINE'}
            </span>
          </div>
          <div className="p-2.5 bg-obsidian-900 rounded-lg border border-obsidian-750 text-center">
            <span className="text-[10px] text-slate-500 block uppercase">Field Role</span>
            <span className="text-xs font-bold text-cyan-ops">RESPONDER</span>
          </div>
        </div>
      </div>

      {/* TAB NAVIGATION: Tactical Missions vs Field Damage Inspection */}
      <div className="flex items-center gap-2 border-b border-obsidian-750 pb-2 font-mono text-xs">
        <button
          type="button"
          onClick={() => setActiveTab('MISSIONS')}
          className={`px-4 py-2 rounded-lg font-bold flex items-center gap-2 transition ${
            activeTab === 'MISSIONS'
              ? 'bg-amber-ops text-obsidian-950 shadow-md'
              : 'text-slate-400 hover:text-slate-200 bg-obsidian-850 hover:bg-obsidian-800'
          }`}
        >
          <Truck className="w-4 h-4" />
          <span>Tactical Rescue Missions</span>
          {activeTask && (
            <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
              activeTab === 'MISSIONS' ? 'bg-black/30 text-obsidian-950' : 'bg-amber-950 text-amber-300 border border-amber-800'
            }`}>
              1 ACTIVE
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('FIELD_INSPECTION')}
          className={`px-4 py-2 rounded-lg font-bold flex items-center gap-2 transition ${
            activeTab === 'FIELD_INSPECTION'
              ? 'bg-emerald-600 text-white shadow-md'
              : 'text-slate-400 hover:text-slate-200 bg-obsidian-850 hover:bg-obsidian-800'
          }`}
        >
          <ClipboardCheck className="w-4 h-4" />
          <span>Field Damage Inspection</span>
          {pendingInspectionDrafts > 0 && (
            <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
              activeTab === 'FIELD_INSPECTION' ? 'bg-black/30 text-white' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
            }`}>
              {pendingInspectionDrafts} DRAFTS
            </span>
          )}
        </button>
      </div>

      {/* VIEW 1: TACTICAL MISSIONS PIPELINE */}
      {activeTab === 'MISSIONS' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Main Column: Active Task & Execution Pipeline (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            <OperationalCard
              title={
                <div className="flex items-center gap-2">
                  <Truck className="w-4 h-4 text-cyan-ops" />
                  <span>Active Assigned Mission {activeTask ? `(#${activeTask.id.slice(0, 8)})` : ''}</span>
                </div>
              }
              subtitle="Command Dispatch with Multi-Stage Status Transition"
              accent="amber"
            >
              <div className="space-y-5">
                {/* Task Details Card */}
                {activeTask ? (
                  <div className="p-4 bg-obsidian-900 rounded-xl border border-obsidian-750 space-y-3 font-mono text-xs">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-amber-ops">{activeTask.incident_code}</span>
                          <SeverityBadge severity={activeTask.priority_level || 'CRITICAL'} />
                        </div>
                        <h3 className="font-bold text-slate-100 text-sm mt-1">
                          {activeTask.incident_title}
                        </h3>
                        <p className="text-xs text-cyan-ops flex items-center gap-1 mt-1">
                          <MapPin className="w-3.5 h-3.5 shrink-0" />
                          {activeTask.location_address || 'Riverfront Colony'}
                        </p>
                      </div>

                      <StatusBadge status={activeTask.status} />
                    </div>

                    <p className="text-[11px] text-slate-400 font-sans">
                      {activeTask.incident_description}
                    </p>

                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-obsidian-800 text-center">
                      <div className="p-2 bg-obsidian-950 rounded border border-obsidian-800">
                        <span className="text-[10px] text-slate-500 block">Civilians Affected</span>
                        <span className="text-sm font-bold text-slate-100 tabular-nums">
                          {activeTask.people_affected || 0}
                        </span>
                      </div>
                      <div className="p-2 bg-obsidian-950 rounded border border-obsidian-800">
                        <span className="text-[10px] text-slate-500 block">Injuries Reported</span>
                        <span className="text-sm font-bold text-red-400 tabular-nums">
                          {activeTask.injuries || 0}
                        </span>
                      </div>
                      <div className="p-2 bg-obsidian-950 rounded border border-obsidian-800">
                        <span className="text-[10px] text-slate-500 block">Vulnerable Count</span>
                        <span className="text-sm font-bold text-amber-ops tabular-nums">
                          {activeTask.vulnerable_count || 0}
                        </span>
                      </div>
                    </div>

                    {/* Incident Photographic Evidence */}
                    <IncidentEvidenceViewer
                      incident={{
                        id: activeTask.incident_id || activeTask.id,
                        incident_code: activeTask.incident_code,
                        title: activeTask.incident_title
                      }}
                    />
                  </div>
                ) : (
                  <div className="p-8 bg-obsidian-900 rounded-xl border border-dashed border-obsidian-750 text-center space-y-2">
                    <ShieldCheck className="w-8 h-8 text-slate-600 mx-auto" />
                    <p className="text-xs font-mono font-bold text-slate-300">No Active Mission Assigned</p>
                    <p className="text-[11px] text-slate-500 font-sans max-w-sm mx-auto">
                      Government Command Officers assign emergency rescue tasks based on tactical priority and responder proximity. When assigned, your mission will appear here for acceptance.
                    </p>
                  </div>
                )}

                {/* Status Pipeline Visualizer */}
                {activeTask && (
                  <div className="space-y-2">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                      Field Progress Pipeline:
                    </span>
                    <div className="grid grid-cols-5 gap-1.5 font-mono text-[10px] text-center">
                      {pipelineSteps.map((step, idx) => {
                        const isDone = idx < currentStepIdx;
                        const isCurrent = idx === currentStepIdx;
                        return (
                          <div
                            key={step}
                            className={`p-2 rounded-lg border transition ${
                              isCurrent
                                ? 'bg-amber-ops text-obsidian-950 font-bold border-amber-ops shadow-lg'
                                : isDone
                                ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
                                : 'bg-obsidian-900 text-slate-600 border-obsidian-800'
                            }`}
                          >
                            <div className="truncate">{step}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                {activeTask && (
                  <div className="space-y-3 pt-3 border-t border-obsidian-750">
                    {transitionError && (
                      <div className="p-2.5 rounded-lg bg-red-950/80 border border-red-800 text-red-300 text-xs font-mono flex items-center justify-between">
                        <span>{transitionError}</span>
                        <button type="button" onClick={() => setTransitionError(null)} className="text-red-400 hover:text-white font-bold">×</button>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => setIsNavOpen(true)}
                        className="px-3.5 py-2 bg-obsidian-800 hover:bg-obsidian-750 text-slate-200 rounded-lg text-xs font-mono border border-obsidian-700 flex items-center gap-1.5 transition"
                      >
                        <Navigation className="w-3.5 h-3.5 text-cyan-ops" />
                        Tactical Waypoint & Route
                      </button>

                      {activeTask.status === 'ASSIGNED' ? (
                        <button
                          type="button"
                          onClick={() => handleStatusTransition('ACCEPTED')}
                          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs font-mono transition flex items-center gap-1.5 shadow-lg shadow-emerald-950"
                        >
                          <Check className="w-4 h-4" />
                          <span>Accept Assigned Task</span>
                        </button>
                      ) : currentStepIdx < pipelineSteps.length - 1 ? (
                        <button
                          type="button"
                          onClick={() => handleStatusTransition(pipelineSteps[currentStepIdx + 1])}
                          className="px-4 py-2 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded-lg text-xs font-mono transition flex items-center gap-1.5 shadow"
                        >
                          <span>Advance Status to: {pipelineSteps[currentStepIdx + 1]}</span>
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      ) : (
                        <span className="text-xs font-mono text-emerald-400 font-bold flex items-center gap-1">
                          <CheckCircle2 className="w-4 h-4" /> TASK COMPLETED
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </OperationalCard>
          </div>

          {/* Right Column: Available Tasks Queue (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <OperationalCard
              title="Available Verified Incidents"
              subtitle="Verified by Govt Command • Dispatched by Command Officers"
              headerAction={
                <span className="text-xs font-mono text-slate-400">
                  {incidents.length} Pending
                </span>
              }
            >
              <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
                {incidents.map((inc: any) => (
                  <div
                    key={inc.id}
                    className="p-3.5 bg-obsidian-900 rounded-xl border border-obsidian-750 space-y-2 hover:border-obsidian-600 transition font-mono text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-amber-ops">{inc.incident_code}</span>
                      <SeverityBadge severity={inc.priority_level || inc.severity || 'MEDIUM'} />
                    </div>

                    <h4 className="font-sans font-bold text-slate-200">
                      {inc.title}
                    </h4>

                    <p className="text-[11px] text-slate-400 font-sans line-clamp-2">
                      {inc.description}
                    </p>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-obsidian-800 text-[10px]">
                      <span className="text-slate-500">{inc.people_affected || 0} Affected</span>
                      
                      {inc.assigned_task_id || inc.status === 'ASSIGNED' ? (
                        <span className="px-2.5 py-1 bg-obsidian-800 text-slate-500 rounded border border-obsidian-750 font-mono text-[10px] flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                          Assigned to Responder
                        </span>
                      ) : activeTask && activeTask.status !== 'COMPLETED' ? (
                        <span className="px-2.5 py-1 bg-obsidian-800/80 text-amber-500/80 rounded border border-obsidian-750 font-mono text-[10px] flex items-center gap-1" title="Complete current mission before taking another">
                          <Clock className="w-3 h-3" />
                          Active Task in Progress
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleClaimIncident(inc.id)}
                          disabled={claimLoadingId === inc.id}
                          className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-bold rounded text-[10px] transition flex items-center gap-1 shadow disabled:opacity-50"
                        >
                          <Check className="w-3 h-3" />
                          <span>{claimLoadingId === inc.id ? 'Claiming...' : 'Claim & Accept Task'}</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {claimError && (
                <div className="mt-3 p-2.5 bg-red-950/80 border border-red-800 rounded-lg text-red-300 font-mono text-[11px] flex items-center justify-between">
                  <span>{claimError}</span>
                  <button type="button" onClick={() => setClaimError(null)} className="text-red-400 hover:text-white font-bold ml-2">×</button>
                </div>
              )}
            </OperationalCard>
          </div>
        </div>
      )}

      {/* VIEW 2: FIELD DAMAGE INSPECTION & ASSESSMENT */}
      {activeTab === 'FIELD_INSPECTION' && (
        <div className="space-y-6">
          <VolunteerFieldInspection
            availableIncidents={incidents}
            onInspectionSubmitted={() => refetchAssessments()}
          />

          {/* List of recent submitted assessments */}
          <OperationalCard
            title="Field Assessments In Government Verification Pipeline"
            subtitle="Inspections submitted to Command Engineering Gate"
            headerAction={
              <span className="text-xs font-mono text-slate-400">
                {submittedAssessments.length} Recorded
              </span>
            }
          >
            {submittedAssessments.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-slate-500">
                No field assessments submitted yet. Fill out the form above to record an inspection.
              </div>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1 font-mono text-xs">
                {submittedAssessments.slice(0, 10).map((a: any) => (
                  <div
                    key={a.id}
                    className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 flex flex-wrap items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-amber-ops">{a.assessment_code}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-obsidian-800 text-slate-300 border border-obsidian-700">
                          {a.sector}
                        </span>
                        <SeverityBadge severity={a.damage_level} />
                      </div>
                      <div className="text-slate-200 font-bold">{a.facility_name}</div>
                      <div className="text-[11px] text-slate-400 font-sans">{a.structural_notes}</div>
                    </div>

                    <div className="flex flex-col items-end gap-1 text-[11px]">
                      <StatusBadge status={a.verification_status} />
                      <span className="text-slate-500 text-[10px]">
                        Confidence: {(a.data_confidence || 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </OperationalCard>
        </div>
      )}

      {/* DEF-09: Volunteer Tactical Waypoint & Route Navigation Modal */}
      <NavigationModal
        isOpen={isNavOpen && Boolean(activeTask)}
        onClose={() => setIsNavOpen(false)}
        title={activeTask?.incident_title || activeTask?.incident_code || 'Assigned Tactical Mission'}
        subtitle={`Tactical Mission Code: ${activeTask?.incident_code || 'INC-ASSIGNED'}`}
        address={activeTask?.location_address || 'Riverfront Colony Rescue Sector'}
        latitude={activeTask?.latitude || 13.0827}
        longitude={activeTask?.longitude || 80.2707}
        badge={
          <SeverityBadge severity={activeTask?.priority_level || 'CRITICAL'} />
        }
      />
    </div>
  );
};

export default VolunteerDashboard;
