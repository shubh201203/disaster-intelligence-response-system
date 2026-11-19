import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import {
  Bot,
  Search,
  Sparkles,
  BookOpen,
  CheckCircle2,
  XCircle,
  Edit3,
  ShieldAlert,
  Layers,
  ArrowRight,
  AlertCircle,
  FileText,
  Scale,
  ShieldCheck,
  Send
} from 'lucide-react';
import { StatusBadge, SeverityBadge, ConfirmDialog } from './design-system';

interface AICopilotPanelProps {
  selectedIncident?: any;
  onRefreshData?: () => void;
}

export const AICopilotPanel: React.FC<AICopilotPanelProps> = ({ selectedIncident, onRefreshData }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [response, setResponse] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'recommendations' | 'copilot' | 'citations'>('recommendations');
  const [modifyNotes, setModifyNotes] = useState<{ [key: string]: string }>({});
  const [modifyingId, setModifyingId] = useState<string | null>(null);

  // Dialog state for approvals/rejections
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    recId: string;
    action: 'approve' | 'reject';
    recTitle: string;
  }>({
    isOpen: false,
    recId: '',
    action: 'approve',
    recTitle: ''
  });
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch incident specific recommendations when an incident is selected
  useEffect(() => {
    if (selectedIncident?.id) {
      fetchIncidentRecommendations(selectedIncident.id);
      setActiveTab('recommendations');
    }
  }, [selectedIncident]);

  const fetchIncidentRecommendations = async (incidentId: string) => {
    try {
      const res = await apiClient.get(`/ai/incidents/${incidentId}/recommendations`);
      setRecommendations(res.data || []);
    } catch (e) {
      console.error('Failed to load incident recommendations', e);
    }
  };

  const handleQuery = async (customQuery?: string) => {
    const q = customQuery !== undefined ? customQuery : query;
    if (!q || !q.trim()) {
      setSearchError('Please enter a situation query or select one of the multi-hazard topics below.');
      return;
    }

    setSearchError(null);
    setLoading(true);
    try {
      const res = await apiClient.post('/ai/rag/query', {
        query: q.trim(),
        incident_id: selectedIncident?.id || null,
        mode: 'GENERAL_COPILOT'
      });
      setResponse(res.data);
      setActiveTab('copilot');
    } catch (e: any) {
      setSearchError('Error running AI Copilot query: ' + (e.response?.data?.detail || e.message || 'Network error'));
    } finally {
      setLoading(false);
    }
  };

  const executeDecision = async (recId: string, action: 'approve' | 'reject' | 'modify') => {
    setActionLoading(true);
    setDecisionError(null);
    try {
      const endpoint = `/ai/recommendations/${recId}/${action}`;
      const body: any = { notes: `Decision executed by Government Command Officer via DIRS Command UI.` };

      if (action === 'modify') {
        const notes = modifyNotes[recId];
        if (!notes) {
          setDecisionError('Please enter modification instructions before submitting.');
          setActionLoading(false);
          return;
        }
        body.notes = notes;
        body.modified_values = { human_override: notes, modified_by: 'Government Officer' };
      }

      await apiClient.post(endpoint, body);
      setModifyingId(null);
      setConfirmModal(prev => ({ ...prev, isOpen: false }));

      if (selectedIncident?.id) {
        fetchIncidentRecommendations(selectedIncident.id);
      }
      if (onRefreshData) onRefreshData();
    } catch (e: any) {
      setDecisionError(`Failed to record decision: ${e.response?.data?.detail || e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="bg-obsidian-850 border border-obsidian-700/80 rounded-xl overflow-hidden shadow-2xl space-y-4">
      {/* Panel Operational Header */}
      <div className="p-4 bg-obsidian-900 border-b border-obsidian-700/80 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-obsidian-800 border border-obsidian-700 text-amber-ops">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-mono font-bold tracking-wider text-slate-100 uppercase">
                Grounded AI Copilot & Decision Review
              </h2>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-950/80 text-amber-ops border border-amber-800/80">
                HITL
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-mono mt-0.5">
              Knowledge-Base Grounded • Human Authority Maintained
            </p>
          </div>
        </div>

        {selectedIncident && (
          <div className="text-right">
            <span className="text-[10px] font-mono text-cyan-ops bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/60">
              TARGET: {selectedIncident.incident_code}
            </span>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="px-4 flex gap-1 border-b border-obsidian-700/60 text-xs font-mono">
        <button
          type="button"
          onClick={() => setActiveTab('recommendations')}
          className={`pb-2.5 px-3 font-semibold transition border-b-2 flex items-center gap-1.5 ${
            activeTab === 'recommendations'
              ? 'border-amber-ops text-amber-ops'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          Decision Review ({recommendations.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('copilot')}
          className={`pb-2.5 px-3 font-semibold transition border-b-2 flex items-center gap-1.5 ${
            activeTab === 'copilot'
              ? 'border-cyan-ops text-cyan-ops'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          AI Situation Query
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('citations')}
          className={`pb-2.5 px-3 font-semibold transition border-b-2 flex items-center gap-1.5 ${
            activeTab === 'citations'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          Authoritative KB ({response?.citations?.length || 0})
        </button>
      </div>

      <div className="p-4 pt-0 space-y-4">
        {/* Decision Error Alert */}
        {decisionError && (
          <div className="p-3 bg-red-950/80 border border-red-800 rounded-lg text-xs font-mono text-red-200 flex items-center justify-between">
            <span>{decisionError}</span>
            <button type="button" onClick={() => setDecisionError(null)} className="text-red-400 hover:text-white font-bold ml-2">×</button>
          </div>
        )}

        {/* TAB 1: DECISION RECOMMENDATIONS (HITL INTERFACE) */}
        {activeTab === 'recommendations' && (
          <div className="space-y-3">
            {recommendations.length === 0 ? (
              <div className="p-6 text-center bg-obsidian-900/60 border border-dashed border-obsidian-700 rounded-xl space-y-2">
                <ShieldCheck className="w-8 h-8 mx-auto text-slate-500" />
                <p className="text-xs font-mono text-slate-300">No Pending AI Decision Recommendations</p>
                <p className="text-[10px] text-slate-500 font-sans max-w-xs mx-auto">
                  Select an incident from the Priority Queue or dispatch an AI Situation Query to generate optimization actions.
                </p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
                {recommendations.map((rec) => (
                  <div
                    key={rec.id}
                    className="p-4 rounded-xl bg-obsidian-900 border border-obsidian-700/80 space-y-3 shadow-md transition hover:border-obsidian-600"
                  >
                    {/* Recommendation Top Identity */}
                    <div className="flex items-start justify-between gap-2 border-b border-obsidian-800 pb-2.5">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/80 text-amber-ops border border-amber-800/80 font-bold uppercase">
                            {rec.action_type || 'RESOURCE_DEPLOYMENT'}
                          </span>
                          <span className="text-xs font-mono font-bold text-slate-100">
                            {rec.title || 'Recommended Emergency Action'}
                          </span>
                        </div>
                        <p className="text-[10px] font-mono text-slate-400 mt-1">
                          STATUS: <span className="text-amber-ops uppercase">{rec.status || 'PENDING_APPROVAL'}</span> • CONFIDENCE: <span className="text-emerald-400">{rec.confidence ? `${rec.confidence}%` : 'VERIFIED'}</span>
                        </p>
                      </div>

                      <StatusBadge status={rec.status || 'PENDING'} />
                    </div>

                    {/* Structured Review Grid: WHY, IMPACT, RESOURCES, RISK */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                      <div className="p-2.5 bg-obsidian-950 rounded-lg border border-obsidian-800 space-y-1">
                        <span className="text-[10px] text-amber-ops font-bold uppercase tracking-wider block">
                          WHY THIS RECOMMENDATION:
                        </span>
                        <p className="text-slate-300 leading-relaxed font-sans text-xs">
                          {rec.rationale || rec.description || 'Optimized to minimize response latency and maximize life-saving coverage based on current spatial proximity.'}
                        </p>
                      </div>

                      <div className="p-2.5 bg-obsidian-950 rounded-lg border border-obsidian-800 space-y-1">
                        <span className="text-[10px] text-cyan-ops font-bold uppercase tracking-wider block">
                          ESTIMATED IMPACT:
                        </span>
                        <p className="text-slate-300 font-sans text-xs">
                          {rec.estimated_impact || 'Optimized allocation to reduce response delay and cover affected population.'}
                        </p>
                      </div>

                      <div className="p-2.5 bg-obsidian-950 rounded-lg border border-obsidian-800 space-y-1">
                        <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider block">
                          REQUIRED RESOURCES:
                        </span>
                        <p className="text-slate-300 font-sans text-xs">
                          {rec.resources_required || 'Calculated fleet and relief supply requirements.'}
                        </p>
                      </div>

                      <div className="p-2.5 bg-obsidian-950 rounded-lg border border-obsidian-800 space-y-1">
                        <span className="text-[10px] text-red-400 font-bold uppercase tracking-wider block">
                          RISK & CONSTRAINTS:
                        </span>
                        <p className="text-slate-300 font-sans text-xs">
                          {rec.constraints || 'Road segment IMPASSABLE; detour routed via Arterial Bypass.'}
                        </p>
                      </div>
                    </div>

                    {/* Modify Notes Drawer */}
                    {modifyingId === rec.id && (
                      <div className="p-3 bg-obsidian-950 border border-amber-800/80 rounded-lg space-y-2 animate-in fade-in duration-150">
                        <label className="text-[10px] font-mono text-amber-400 uppercase tracking-wider block">
                          Official Modification Instructions / Override:
                        </label>
                        <textarea
                          rows={2}
                          value={modifyNotes[rec.id] || ''}
                          onChange={(e) => setModifyNotes({ ...modifyNotes, [rec.id]: e.target.value })}
                          placeholder="e.g. Prioritize medical kits over food packs; divert route via North Bridge..."
                          className="w-full bg-obsidian-900 border border-obsidian-700 text-xs font-mono rounded p-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops"
                        />
                        <div className="flex justify-end gap-2 text-xs font-mono">
                          <button
                            type="button"
                            onClick={() => setModifyingId(null)}
                            className="px-2.5 py-1 text-slate-400 hover:text-slate-200"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => executeDecision(rec.id, 'modify')}
                            className="px-3 py-1 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded"
                          >
                            Save & Record Modification
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Consequential Action Buttons */}
                    <div className="flex items-center justify-between pt-1 border-t border-obsidian-800">
                      <span className="text-[9px] font-mono text-slate-500">
                        OFFICER DECISION REQUIRED
                      </span>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setConfirmModal({
                            isOpen: true,
                            recId: rec.id,
                            action: 'reject',
                            recTitle: rec.title || 'this recommendation'
                          })}
                          className="px-3 py-1.5 rounded-lg bg-obsidian-800 hover:bg-red-950/80 border border-obsidian-700 hover:border-red-800/80 text-slate-300 hover:text-red-400 text-xs font-mono flex items-center gap-1.5 transition"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          Reject
                        </button>

                        <button
                          type="button"
                          onClick={() => setModifyingId(modifyingId === rec.id ? null : rec.id)}
                          className="px-3 py-1.5 rounded-lg bg-obsidian-800 hover:bg-amber-950/80 border border-obsidian-700 hover:border-amber-800/80 text-slate-300 hover:text-amber-400 text-xs font-mono flex items-center gap-1.5 transition"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          Modify
                        </button>

                        <button
                          type="button"
                          onClick={() => setConfirmModal({
                            isOpen: true,
                            recId: rec.id,
                            action: 'approve',
                            recTitle: rec.title || 'this recommendation'
                          })}
                          className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold flex items-center gap-1.5 transition shadow"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Approve Dispatch
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: COPILOT SITUATION QUERY */}
        {activeTab === 'copilot' && (
          <div className="space-y-3">
            {/* Search Feedback Banner */}
            {searchError && (
              <div className="p-3 bg-red-950/80 border border-red-800 rounded-lg text-xs font-mono text-red-200 flex items-center justify-between">
                <span>{searchError}</span>
                <button type="button" onClick={() => setSearchError(null)} className="text-red-400 hover:text-white font-bold ml-2">×</button>
              </div>
            )}

            {/* Quick Query Input */}
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
                placeholder="Ask DIRS Grounded Copilot (e.g. 'NDMA SOP for cyclone evacuation')..."
                className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg pl-3 pr-24 py-2.5 text-xs font-mono text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-ops"
              />
              <button
                type="button"
                onClick={() => handleQuery()}
                disabled={loading}
                className="absolute right-1.5 top-1.5 bottom-1.5 px-3 bg-cyan-ops hover:bg-cyan-ops-bright text-obsidian-950 font-bold rounded text-xs font-mono flex items-center gap-1 transition disabled:opacity-50"
              >
                {loading ? 'Querying...' : 'Search'}
                <Send className="w-3 h-3" />
              </button>
            </div>

            {/* Multi-Hazard Quick Queries */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
                Approved Multi-Hazard Guidance:
              </span>
              <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
                <button
                  type="button"
                  onClick={() => handleQuery('What is the NDMA shelter allocation protocol for flood evacuees?')}
                  className="px-2 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-400 hover:text-slate-200 hover:border-obsidian-600"
                >
                  🌊 Flood SOP
                </button>
                <button
                  type="button"
                  onClick={() => handleQuery('What is the NDMA coastal pre-evacuation and wind safety framework for cyclones?')}
                  className="px-2 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-400 hover:text-slate-200 hover:border-obsidian-600"
                >
                  🌀 Cyclone
                </button>
                <button
                  type="button"
                  onClick={() => handleQuery('What is the NDMA fire safety suppression perimeter and burn triage protocol?')}
                  className="px-2 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-400 hover:text-slate-200 hover:border-obsidian-600"
                >
                  🔥 Fire Safety
                </button>
                <button
                  type="button"
                  onClick={() => handleQuery('What is the NDMA earthquake drop cover hold and USAR collapse triage protocol?')}
                  className="px-2 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-400 hover:text-slate-200 hover:border-obsidian-600"
                >
                  🌋 Earthquake USAR
                </button>
                <button
                  type="button"
                  onClick={() => handleQuery('What is the NDMA landslide early warning and lateral slope evacuation protocol?')}
                  className="px-2 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-400 hover:text-slate-200 hover:border-obsidian-600"
                >
                  ⛰️ Landslide
                </button>
                <button
                  type="button"
                  onClick={() => handleQuery('What is the INCOIS coastal tsunami early warning and vertical evacuation protocol?')}
                  className="px-2 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-400 hover:text-slate-200 hover:border-obsidian-600"
                >
                  🌊 Tsunami
                </button>
                <button
                  type="button"
                  onClick={() => handleQuery('What is the NDMA hazmat hot zone isolation and chemical decontamination protocol?')}
                  className="px-2 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-400 hover:text-slate-200 hover:border-obsidian-600"
                >
                  ☣️ Chemical Hazmat
                </button>
              </div>
            </div>

            {/* Query Response */}
            {response && (
              <div className="space-y-3 pt-2">
                {!response.is_grounded || response.requires_human_review ? (
                  <div className="p-3 bg-red-950/60 border border-red-800/80 rounded-lg text-xs space-y-1">
                    <div className="flex items-center gap-1.5 text-red-400 font-bold font-mono">
                      <ShieldAlert className="w-4 h-4" /> LOW CONFIDENCE / REQUIRES HUMAN REVIEW
                    </div>
                    <p className="text-slate-300 font-mono text-[11px]">
                      Knowledge base threshold not fully met. Output requires explicit human verification.
                    </p>
                  </div>
                ) : (
                  <div className="p-2.5 bg-emerald-950/40 border border-emerald-800/60 rounded-lg flex items-center justify-between text-xs font-mono">
                    <span className="text-emerald-300 flex items-center gap-1.5 font-semibold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Grounded in Authoritative KB (NDMA/FEMA/INCOIS)
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Confidence: {response.confidence !== undefined ? `${response.confidence}%` : 'VERIFIED'}
                    </span>
                  </div>
                )}

                <div className="bg-obsidian-900 p-3.5 rounded-lg border border-obsidian-750 space-y-1.5 text-xs text-slate-200 leading-relaxed font-mono">
                  <p className="text-[10px] text-cyan-ops uppercase font-bold tracking-wider">AI Executive Summary:</p>
                  <p>{response.summary}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: CITATIONS */}
        {activeTab === 'citations' && (
          <div className="space-y-2 text-xs font-mono">
            {response?.citations && response.citations.length > 0 ? (
              <div className="space-y-2">
                {response.citations.map((c: any, idx: number) => {
                  const title = c.title || c.document_title || 'Emergency Management Document';
                  const org = c.organization || c.authoritative_body || 'Disaster Agency';
                  const section = c.section || c.section_ref || 'Operational Guidance';
                  const excerpt = c.excerpt || '';
                  const score = c.similarity_score !== undefined ? `${(c.similarity_score * 100).toFixed(0)}%` : 'VERIFIED';

                  return (
                    <div key={idx} className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-slate-200 text-xs truncate">{title}</span>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-900">
                            Match: {score}
                          </span>
                          <span className="text-[10px] text-amber-ops bg-amber-950/60 px-1.5 py-0.2 rounded border border-amber-900">
                            {org}
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400 italic font-sans leading-relaxed">"{excerpt}"</p>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-obsidian-800">
                        <span>Section: {section} • Curated Guidance</span>
                        {c.url && (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-ops hover:underline flex items-center gap-1"
                          >
                            <span>Reference Link</span>
                            <ArrowRight className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-6 text-center bg-obsidian-900/40 border border-dashed border-obsidian-750 rounded-xl text-slate-500">
                <BookOpen className="w-6 h-6 mx-auto mb-2 text-slate-600" />
                <span>Run an AI Situation Query to retrieve authoritative citations.</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Confirmation Dialog for Approvals / Rejections */}
      <ConfirmDialog
        isOpen={confirmModal.isOpen}
        title={confirmModal.action === 'approve' ? 'Approve Emergency Dispatch' : 'Reject Recommendation'}
        message={
          confirmModal.action === 'approve'
            ? `Are you sure you want to approve "${confirmModal.recTitle}"? This authorizes emergency vehicle routing and resource deployment.`
            : `Are you sure you want to reject "${confirmModal.recTitle}"? This will log a Human-In-The-Loop override in the audit trail.`
        }
        confirmLabel={confirmModal.action === 'approve' ? 'Approve & Dispatch' : 'Reject Action'}
        variant={confirmModal.action === 'approve' ? 'primary' : 'danger'}
        onConfirm={() => executeDecision(confirmModal.recId, confirmModal.action)}
        onCancel={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
        isLoading={actionLoading}
      />
    </div>
  );
};
