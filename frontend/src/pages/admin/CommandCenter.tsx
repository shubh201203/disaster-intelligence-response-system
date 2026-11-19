import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { 
  ShieldCheck, 
  AlertTriangle, 
  Users, 
  Home, 
  Package, 
  Activity, 
  CheckCircle2, 
  Radio, 
  Search, 
  Layers, 
  Eye, 
  FileText,
  Clock,
  Compass,
  MapPin,
  XCircle,
  Check,
  RotateCcw,
  GitCommit,
  ClipboardCheck,
  Filter
} from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { AICopilotPanel } from '../../components/AICopilotPanel';
import { PrecedenceGraphVisualizer } from '../../components/recovery/PrecedenceGraphVisualizer';
import { getPrecedenceGraph } from '../../api/precedence';
import { IncidentEvidenceViewer } from '../../components/incident/IncidentEvidenceViewer';
import { 
  KPIStat, 
  OperationalCard, 
  SeverityBadge, 
  StatusBadge, 
  PageHeader,
  ConfirmDialog,
  LoadingSkeleton 
} from '../../components/design-system';
import { useAuth } from '../../context/AuthContext';

// Leaflet default icon fix
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

export const CommandCenter: React.FC = () => {
  const { user } = useAuth();
  const [selectedIncident, setSelectedIncident] = useState<any>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [feedEvents, setFeedEvents] = useState<Array<{ id: string; time: string; text: string }>>([
    { id: '1', time: '16:40', text: 'Command Center initialized. WebSocket stream connected on /ws/feed' },
    { id: '2', time: '16:41', text: 'Incident INC-2026-1024 verified by Command Officer.' }
  ]);

  // Verification dialog state
  const [verifyModal, setVerifyModal] = useState<{
    isOpen: boolean;
    incidentId: string;
    incidentCode: string;
    action: 'VERIFY' | 'REJECT';
  }>({
    isOpen: false,
    incidentId: '',
    incidentCode: '',
    action: 'VERIFY'
  });
  const [verifyLoading, setVerifyLoading] = useState(false);

  // Active Tab: Operations vs. Infrastructure Precedence vs. Field Inspections
  const [activeTab, setActiveTab] = useState<'OPERATIONS' | 'PRECEDENCE' | 'INSPECTIONS'>('OPERATIONS');
  const [periodDays, setPeriodDays] = useState<number>(30);
  const [inspectionFilter, setInspectionFilter] = useState<'ALL' | 'PENDING_VERIFICATION' | 'VERIFIED' | 'REJECTED'>('ALL');

  // Inspection Verification Dialog State
  const [inspectionModal, setInspectionModal] = useState<{
    isOpen: boolean;
    assessmentId: string;
    assessmentCode: string;
    facilityName: string;
    action: 'VERIFY' | 'REJECT' | 'DISPUTE';
    damageLevel: string;
    notes: string;
  }>({
    isOpen: false,
    assessmentId: '',
    assessmentCode: '',
    facilityName: '',
    action: 'VERIFY',
    damageLevel: 'MODERATE',
    notes: 'Engineering verification certified by Command Officer.'
  });
  const [inspectionVerifyLoading, setInspectionVerifyLoading] = useState(false);

  // Field Damage Assessments Query
  const {
    data: assessments = [],
    isLoading: assessmentsLoading,
    refetch: refetchAssessments
  } = useQuery({
    queryKey: ['admin-field-assessments', user?.id],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/recovery/assessments');
        return res.data;
      } catch (e) {
        return [];
      }
    },
    enabled: activeTab === 'INSPECTIONS'
  });

  const handleInspectionVerify = async () => {
    setInspectionVerifyLoading(true);
    try {
      await apiClient.post(`/recovery/damage-assessments/${inspectionModal.assessmentId}/verify`, {
        action: inspectionModal.action,
        verified_damage_level: inspectionModal.damageLevel,
        engineering_notes: inspectionModal.notes.trim() || 'Engineering site certification completed.'
      });
      setInspectionModal(prev => ({ ...prev, isOpen: false }));
      refetchAssessments();
    } catch (err: any) {
      alert('Verification failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setInspectionVerifyLoading(false);
    }
  };

  // Precedence Graph Query
  const {
    data: precedenceData,
    isLoading: precedenceLoading,
    error: precedenceError,
    refetch: refetchPrecedence
  } = useQuery({
    queryKey: ['precedence-graph', periodDays],
    queryFn: () => getPrecedenceGraph(periodDays),
    enabled: activeTab === 'PRECEDENCE'
  });

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['admin-summary'],
    queryFn: async () => {
      const res = await apiClient.get('/analytics/summary');
      return res.data;
    },
    refetchInterval: 5000
  });

  const { data: incidents = [], refetch: refetchIncidents, isLoading: incidentsLoading } = useQuery({
    queryKey: ['admin-incidents'],
    queryFn: async () => {
      const res = await apiClient.get('/incidents');
      return res.data;
    },
    refetchInterval: 5000
  });

  const { data: shelters = [] } = useQuery({
    queryKey: ['admin-shelters'],
    queryFn: async () => {
      const res = await apiClient.get('/shelters');
      return res.data;
    }
  });

  // Listen to WebSocket feed
  useEffect(() => {
    const wsUrl = ((import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1')
      .replace('http', 'ws')
      .replace('/api/v1', '/ws/feed');

    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setFeedEvents(prev => [
          { id: String(Date.now()), time: timeStr, text: `[${data.type || 'EVENT'}] ${data.title || data.incident_code || 'System telemetry received'}` },
          ...prev.slice(0, 15)
        ]);
        refetchIncidents();
      } catch (e) {
        console.error(e);
      }
    };

    return () => {
      ws.close();
    };
  }, [refetchIncidents]);

  // Leaflet Map Initialization
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      zoomControl: false,
      attributionControl: false
    }).setView([13.0827, 80.2707], 12);

    L.control.zoom({ position: 'topright' }).addTo(map);

    // OpenStreetMap tiles with dark CSS filter (no API key required, zero watermark)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Invalidate map size whenever switching back to OPERATIONS tab
  useEffect(() => {
    if (activeTab === 'OPERATIONS' && mapInstanceRef.current) {
      const timer = setTimeout(() => {
        mapInstanceRef.current?.invalidateSize();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [activeTab]);

  // Update Map Markers when incidents change
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    incidents.forEach((inc: any) => {
      const lat = inc.latitude || 13.0827;
      const lng = inc.longitude || 80.2707;
      const isCritical = inc.priority_level === 'CRITICAL' || inc.severity === 'CRITICAL';
      const color = isCritical ? '#ef4444' : '#f59e0b';

      const customIcon = L.divIcon({
        className: 'custom-incident-marker',
        html: `
          <div style="
            position: relative;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
          ">
            <span style="
              position: absolute;
              width: 100%;
              height: 100%;
              border-radius: 50%;
              background: ${color};
              opacity: 0.4;
              animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
            "></span>
            <span style="
              width: 12px;
              height: 12px;
              border-radius: 50%;
              background: ${color};
              border: 2px solid #ffffff;
              box-shadow: 0 0 10px ${color};
            "></span>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      const marker = L.marker([lat, lng], { icon: customIcon });
      marker.on('click', () => {
        setSelectedIncident(inc);
      });

      marker.bindPopup(`
        <div style="font-family: monospace; font-size: 11px; color: #f1f5f9; padding: 4px;">
          <div style="font-weight: bold; color: ${color}; margin-bottom: 2px;">
            ${inc.incident_code}: ${inc.title}
          </div>
          <div>Disaster: ${inc.disaster_type}</div>
          <div>Priority: ${inc.priority_score || 0}/100 (${inc.priority_level || 'MED'})</div>
          <div>Affected: ${inc.people_affected || 0} civilians</div>
          <div style="color: #94a3b8; font-size: 10px; margin-top: 4px;">Click to inspect details</div>
        </div>
      `);

      markersLayerRef.current?.addLayer(marker);
    });
  }, [incidents]);

  const handleVerifyAction = async () => {
    setVerifyLoading(true);
    try {
      await apiClient.put(`/incidents/${verifyModal.incidentId}/verify`, {
        action: verifyModal.action,
        notes: `Recorded via Government Command Center UI by Command Officer.`
      });
      refetchIncidents();
      setVerifyModal(prev => ({ ...prev, isOpen: false }));
      if (selectedIncident?.id === verifyModal.incidentId) {
        setSelectedIncident(null);
      }
    } catch (e: any) {
      alert('Error updating incident status: ' + (e.response?.data?.detail || e.message));
    } finally {
      setVerifyLoading(false);
    }
  };

  const filteredIncidents = incidents.filter((inc: any) => {
    if (filterSeverity === 'ALL') return true;
    return (inc.priority_level || inc.severity) === filterSeverity;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <PageHeader
        title="GOVERNMENT EMERGENCY COMMAND CENTER"
        subtitle="Executive Situational Awareness, AI Priority Dispatch & Grounded Decision Support"
        icon={ShieldCheck}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800 flex items-center gap-1.5">
            <Radio className="w-3 h-3 animate-pulse" />
            COMMAND TELEMETRY
          </span>
        }
        actions={
          <button
            type="button"
            onClick={() => refetchIncidents()}
            className="px-3 py-1.5 rounded-lg bg-obsidian-850 hover:bg-obsidian-800 border border-obsidian-700 text-slate-300 text-xs font-mono flex items-center gap-1.5 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Sync Feeds
          </button>
        }
      />

      {/* View Mode Switcher Tabs */}
      <div className="flex items-center gap-3 border-b border-obsidian-750 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('OPERATIONS')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2 transition ${
            activeTab === 'OPERATIONS'
              ? 'bg-amber-ops text-black shadow-md'
              : 'bg-obsidian-850 hover:bg-obsidian-800 text-slate-400 border border-obsidian-700'
          }`}
        >
          <Radio className="w-3.5 h-3.5" />
          Live Emergency Operations
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('PRECEDENCE')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2 transition ${
            activeTab === 'PRECEDENCE'
              ? 'bg-emerald-600 text-white shadow-md'
              : 'bg-obsidian-850 hover:bg-obsidian-800 text-slate-400 border border-obsidian-700'
          }`}
        >
          <GitCommit className="w-3.5 h-3.5 text-emerald-400" />
          Infrastructure Precedence (CPM-PL)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('INSPECTIONS')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2 transition ${
            activeTab === 'INSPECTIONS'
              ? 'bg-purple-600 text-white shadow-md'
              : 'bg-obsidian-850 hover:bg-obsidian-800 text-slate-400 border border-obsidian-700'
          }`}
        >
          <ClipboardCheck className="w-3.5 h-3.5 text-purple-300" />
          Field Inspections Verification
        </button>
      </div>

      {/* Precedence Tab Content */}
      <div className={activeTab === 'PRECEDENCE' ? 'space-y-4' : 'hidden'}>
        <PrecedenceGraphVisualizer
          data={precedenceData || {
            is_acyclic: true,
            topological_order: [],
            critical_path_project_ids: [],
            project_makespan_periods: 0,
            total_projects: 0,
            total_dependencies: 0,
            nodes: [],
            edges: [],
            cycle_path: null
          }}
          isLoading={precedenceLoading}
          error={precedenceError ? (precedenceError as any)?.message || 'Failed to load precedence graph' : null}
          onRefresh={refetchPrecedence}
          periodDays={periodDays}
          onPeriodDaysChange={setPeriodDays}
        />
      </div>

      {/* Inspections Tab Content */}
      <div className={activeTab === 'INSPECTIONS' ? 'space-y-4 font-mono text-xs' : 'hidden'}>
        <OperationalCard
          title="Field Damage Inspection Verification Pipeline"
          subtitle="Government Engineering Gate: Certify, Dispute, or Reject Field Assessments"
            headerAction={
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500 uppercase">Filter:</span>
                {(['ALL', 'PENDING_VERIFICATION', 'VERIFIED', 'REJECTED'] as const).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setInspectionFilter(st)}
                    className={`px-2 py-0.5 rounded text-[10px] transition ${
                      inspectionFilter === st
                        ? 'bg-purple-900 text-purple-200 font-bold'
                        : 'bg-obsidian-850 text-slate-400 hover:text-white border border-obsidian-750'
                    }`}
                  >
                    {st.replace('_', ' ')}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => refetchAssessments()}
                  className="p-1 rounded bg-obsidian-800 text-slate-400 hover:text-white"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            }
          >
            {assessments.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                No field assessments recorded in the system.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-obsidian-750 text-[10px] text-slate-400 uppercase">
                      <th className="py-2 px-3">Code</th>
                      <th className="py-2 px-3">Sector</th>
                      <th className="py-2 px-3">Facility</th>
                      <th className="py-2 px-3">Damage Level</th>
                      <th className="py-2 px-3">Est. Cost</th>
                      <th className="py-2 px-3">Status</th>
                      <th className="py-2 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-800">
                    {assessments
                      .filter((a: any) => inspectionFilter === 'ALL' || a.verification_status === inspectionFilter)
                      .map((a: any) => (
                        <tr key={a.id} className="hover:bg-obsidian-900/60 transition">
                          <td className="py-2.5 px-3 font-bold text-amber-ops">{a.assessment_code}</td>
                          <td className="py-2.5 px-3">
                            <span className="px-1.5 py-0.5 rounded bg-obsidian-800 border border-obsidian-700 text-[10px]">
                              {a.sector}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="font-bold text-slate-200">{a.facility_name}</div>
                            <div className="text-[10px] text-slate-400 font-sans line-clamp-1">{a.structural_notes}</div>
                          </td>
                          <td className="py-2.5 px-3">
                            <SeverityBadge severity={a.damage_level} />
                          </td>
                          <td className="py-2.5 px-3 text-slate-300">
                            ₹{(a.estimated_reconstruction_cost || 0).toLocaleString()}
                          </td>
                          <td className="py-2.5 px-3">
                            <StatusBadge status={a.verification_status} />
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <button
                              type="button"
                              onClick={() => setInspectionModal({
                                isOpen: true,
                                assessmentId: a.id,
                                assessmentCode: a.assessment_code,
                                facilityName: a.facility_name,
                                action: 'VERIFY',
                                damageLevel: a.damage_level,
                                notes: 'Certified by Command Engineer.'
                              })}
                              className="px-2.5 py-1 bg-purple-900 hover:bg-purple-800 text-purple-200 rounded text-[11px] font-bold transition border border-purple-700"
                            >
                              Review & Certify
                            </button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </OperationalCard>
        </div>

      {/* Operations Tab Content (Map & Operational Workspace) */}
      <div className={activeTab === 'OPERATIONS' ? 'space-y-6' : 'hidden'}>
        {/* Top 6 KPI Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPIStat
          label="Active Disasters"
          value={summary?.active_disasters ?? 1}
          subtext="PostGIS Active Zones"
          icon={AlertTriangle}
          variant="critical"
        />
        <KPIStat
          label="Critical Incidents"
          value={summary?.critical_incidents ?? 0}
          subtext="Priority ≥ 80 / 100"
          icon={Activity}
          variant="high"
        />
        <KPIStat
          label="People Affected"
          value={summary?.people_affected ?? 0}
          subtext="Civilians under threat"
          icon={Users}
          variant="amber"
        />
        <KPIStat
          label="Active Volunteers"
          value={summary?.active_volunteers ?? 0}
          subtext="On-duty field responders"
          icon={Users}
          variant="emerald"
        />
        <KPIStat
          label="Shelters Online"
          value={shelters.length || 0}
          subtext="Multi-criteria capacity"
          icon={Home}
          variant="cyan"
        />
        <KPIStat
          label="Relief Units Stocked"
          value={(summary?.total_resources_available ?? 0).toLocaleString()}
          subtext="Available depot supplies"
          icon={Package}
          variant="neutral"
        />
      </div>

      {/* Main Command Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Leaflet GIS Map + Priority Incident Queue */}
        <div className="lg:col-span-7 space-y-6">
          {/* Operational Map Card */}
          <OperationalCard
            title="Operational Situation Map (EPSG:4326)"
            subtitle="PostGIS Geographic Engine • Incident Coordinates"
            headerAction={
              <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Spatial Index Synced</span>
              </div>
            }
            bodyClassName="p-0 overflow-hidden relative"
          >
            <div className="h-80 w-full relative">
              <div ref={mapContainerRef} className="w-full h-full" />
              
              {/* Floating Map Legend */}
              <div className="absolute bottom-3 left-3 z-[400] bg-obsidian-900/90 backdrop-blur border border-obsidian-700/80 rounded-lg p-2.5 text-[10px] font-mono space-y-1 shadow-lg pointer-events-auto">
                <div className="text-slate-400 font-bold uppercase tracking-wider mb-1">INCIDENT SEVERITY:</div>
                <div className="flex items-center gap-2 text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                  <span>Critical Priority (≥80)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>High / Medium Priority</span>
                </div>
              </div>

              {/* Reset View Button */}
              <button
                type="button"
                onClick={() => mapInstanceRef.current?.setView([13.0827, 80.2707], 12)}
                className="absolute top-3 left-3 z-[400] px-2.5 py-1 bg-obsidian-900/90 backdrop-blur border border-obsidian-700/80 rounded text-[10px] font-mono text-slate-300 hover:text-white hover:border-amber-ops transition flex items-center gap-1 shadow"
              >
                <Compass className="w-3 h-3 text-cyan-ops" />
                <span>Center Chennai</span>
              </button>
            </div>
          </OperationalCard>

          {/* Priority Queue Table */}
          <OperationalCard
            title={
              <div className="flex items-center gap-2">
                <span>Priority Incident Queue</span>
                <span className="text-[10px] font-mono text-slate-400 font-normal">
                  ({filteredIncidents.length} Records)
                </span>
              </div>
            }
            headerAction={
              <div className="flex items-center gap-1.5 text-xs font-mono">
                <span className="text-[10px] text-slate-500 uppercase">Filter:</span>
                {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
                  <button
                    key={sev}
                    type="button"
                    onClick={() => setFilterSeverity(sev)}
                    className={`px-2 py-0.5 rounded text-[10px] transition ${
                      filterSeverity === sev
                        ? 'bg-amber-ops text-obsidian-950 font-bold'
                        : 'bg-obsidian-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            }
          >
            {incidentsLoading ? (
              <LoadingSkeleton variant="table" lines={4} />
            ) : filteredIncidents.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-slate-500">
                No incidents matching current severity filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead>
                    <tr className="border-b border-obsidian-750 text-slate-500 text-[10px] uppercase tracking-wider">
                      <th className="pb-2.5">Code</th>
                      <th className="pb-2.5">Type</th>
                      <th className="pb-2.5">Title</th>
                      <th className="pb-2.5">Priority Gauge</th>
                      <th className="pb-2.5">Civilians</th>
                      <th className="pb-2.5">Status</th>
                      <th className="pb-2.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-800/80">
                    {filteredIncidents.map((inc: any) => {
                      const isSelected = selectedIncident?.id === inc.id;
                      return (
                        <tr 
                          key={inc.id} 
                          className={`transition hover:bg-obsidian-800/60 ${
                            isSelected ? 'bg-amber-950/20 border-l-2 border-l-amber-ops' : ''
                          }`}
                        >
                          <td className="py-3 font-bold text-amber-ops">{inc.incident_code}</td>
                          <td className="py-3 text-slate-300">{inc.disaster_type}</td>
                          <td className="py-3 font-sans text-slate-200 max-w-[140px] truncate" title={inc.title}>
                            {inc.title}
                          </td>
                          <td className="py-3">
                            <SeverityBadge severity={inc.priority_level || 'MEDIUM'} />
                          </td>
                          <td className="py-3 tabular-nums text-slate-300">
                            {inc.people_affected || 0}
                          </td>
                          <td className="py-3">
                            <StatusBadge status={inc.status || 'REPORTED'} />
                          </td>
                          <td className="py-3 text-right">
                            <button
                              type="button"
                              onClick={() => setSelectedIncident(inc)}
                              className="px-2.5 py-1 bg-obsidian-800 hover:bg-obsidian-750 text-slate-300 hover:text-white rounded text-[11px] font-mono border border-obsidian-700 transition inline-flex items-center gap-1"
                            >
                              <Eye className="w-3 h-3 text-cyan-ops" />
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </OperationalCard>
        </div>

        {/* Right Column (5 cols): AI Copilot + Selected Incident Detail Profile */}
        <div className="lg:col-span-5 space-y-6">
          {/* Grounded AI Copilot & HITL Decision Review Panel */}
          <AICopilotPanel
            selectedIncident={selectedIncident}
            onRefreshData={refetchIncidents}
          />

          {/* Selected Incident Intelligence Profile */}
          {selectedIncident ? (
            <div className="bg-obsidian-850 border border-amber-ops/60 rounded-xl p-5 space-y-4 shadow-2xl animate-in fade-in duration-200">
              {/* Header */}
              <div className="flex items-start justify-between border-b border-obsidian-750 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-amber-ops">
                      {selectedIncident.incident_code}
                    </span>
                    <SeverityBadge severity={selectedIncident.priority_level || 'CRITICAL'} />
                  </div>
                  <h3 className="font-bold text-slate-100 text-sm mt-1">
                    {selectedIncident.title}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedIncident(null)}
                  className="text-slate-500 hover:text-slate-200 p-1"
                >
                  ✕
                </button>
              </div>

              {/* Coordinates & Location Strip */}
              <div className="p-2.5 bg-obsidian-900 rounded-lg border border-obsidian-750 text-xs font-mono space-y-1">
                <div className="flex items-center gap-1.5 text-cyan-ops">
                  <MapPin className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{selectedIncident.location_address || 'Riverfront Colony, Sector 4'}</span>
                </div>
                <div className="text-[10px] text-slate-500">
                  Lat: {selectedIncident.latitude?.toFixed(4) || '13.0827'}° N • Lng: {selectedIncident.longitude?.toFixed(4) || '80.2707'}° E
                </div>
              </div>

              {/* Key Intelligence Stats Grid */}
              <div className="grid grid-cols-3 gap-2 font-mono text-center">
                <div className="p-2 bg-obsidian-900 rounded border border-obsidian-750">
                  <span className="text-[10px] text-slate-500 uppercase block">Civilians</span>
                  <span className="text-sm font-bold text-slate-200 tabular-nums">
                    {selectedIncident.people_affected || 0}
                  </span>
                </div>
                <div className="p-2 bg-obsidian-900 rounded border border-obsidian-750">
                  <span className="text-[10px] text-slate-500 uppercase block">Injuries</span>
                  <span className="text-sm font-bold text-red-400 tabular-nums">
                    {selectedIncident.injuries || 0}
                  </span>
                </div>
                <div className="p-2 bg-obsidian-900 rounded border border-obsidian-750">
                  <span className="text-[10px] text-slate-500 uppercase block">Vulnerable</span>
                  <span className="text-sm font-bold text-amber-ops tabular-nums">
                    {selectedIncident.vulnerable_count || 0}
                  </span>
                </div>
              </div>

              {/* Infrastructure Damage */}
              {selectedIncident.infrastructure_damage && (
                <div className="p-2.5 bg-obsidian-900 rounded-lg border border-obsidian-750 text-xs space-y-1">
                  <span className="text-[10px] font-mono text-amber-ops uppercase font-bold tracking-wider">
                    Infrastructure Damage Assessment:
                  </span>
                  <p className="text-slate-300 font-sans text-xs">
                    {selectedIncident.infrastructure_damage}
                  </p>
                </div>
              )}

              {/* Incident Photographic Evidence Gallery */}
              <IncidentEvidenceViewer incident={selectedIncident} />

              {/* Verification & HITL Action Strip */}
              <div className="flex items-center justify-between pt-2 border-t border-obsidian-750">
                <span className="text-[10px] font-mono text-slate-500">
                  STATUS: <StatusBadge status={selectedIncident.status || 'REPORTED'} />
                </span>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setVerifyModal({
                      isOpen: true,
                      incidentId: selectedIncident.id,
                      incidentCode: selectedIncident.incident_code,
                      action: 'REJECT'
                    })}
                    className="px-3 py-1.5 rounded-lg bg-obsidian-800 hover:bg-red-950/80 border border-obsidian-700 hover:border-red-800 text-slate-300 hover:text-red-400 text-xs font-mono flex items-center gap-1 transition"
                  >
                    <XCircle className="w-3.5 h-3.5" /> Reject
                  </button>

                  <button
                    type="button"
                    onClick={() => setVerifyModal({
                      isOpen: true,
                      incidentId: selectedIncident.id,
                      incidentCode: selectedIncident.incident_code,
                      action: 'VERIFY'
                    })}
                    className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold flex items-center gap-1.5 transition shadow"
                  >
                    <Check className="w-3.5 h-3.5" /> Verify Incident
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 bg-obsidian-850 border border-dashed border-obsidian-750 rounded-xl text-center space-y-2">
              <Eye className="w-6 h-6 mx-auto text-slate-600" />
              <p className="text-xs font-mono text-slate-300">No Incident Inspected</p>
              <p className="text-[10px] text-slate-500 font-sans">
                Click "Inspect" on any incident in the priority table or on a map node to view intelligence profile.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Response Intelligence & Realtime Telemetry Feed Strip */}
      <OperationalCard
        title="Live Mission Event Stream (/ws/feed)"
        subtitle="Realtime WebSockets Telemetry & Dispatch Audit Stream"
        bodyClassName="p-3"
      >
        <div className="flex items-center gap-4 overflow-x-auto whitespace-nowrap text-xs font-mono py-1">
          {feedEvents.slice(0, 6).map((ev) => (
            <div
              key={ev.id}
              className="flex items-center gap-2 bg-obsidian-950 px-3 py-1.5 rounded-lg border border-obsidian-750 shrink-0"
            >
              <span className="text-cyan-ops font-bold">{ev.time}</span>
              <span className="text-slate-300">{ev.text}</span>
            </div>
          ))}
        </div>
      </OperationalCard>
      </div>

      {/* Incident Verification ConfirmDialog */}
      <ConfirmDialog
        isOpen={verifyModal.isOpen}
        title={verifyModal.action === 'VERIFY' ? 'Verify Emergency Incident' : 'Reject Incident Report'}
        message={
          verifyModal.action === 'VERIFY'
            ? `Confirming verification for ${verifyModal.incidentCode}. This transitions the incident to VERIFIED status and flags it for mathematical resource allocation.`
            : `Rejecting ${verifyModal.incidentCode}. This will log the report as false or invalid in the government audit log.`
        }
        confirmLabel={verifyModal.action === 'VERIFY' ? 'Confirm Verification' : 'Confirm Rejection'}
        variant={verifyModal.action === 'VERIFY' ? 'primary' : 'danger'}
        onConfirm={handleVerifyAction}
        onCancel={() => setVerifyModal(prev => ({ ...prev, isOpen: false }))}
        isLoading={verifyLoading}
      />

      {/* Inspection Verification Modal */}
      {inspectionModal.isOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-obsidian-850 border border-obsidian-700 rounded-xl p-5 space-y-4 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-obsidian-750 pb-2">
              <span className="font-bold text-purple-300 text-sm">
                Engineering Assessment Certification Gate
              </span>
              <button
                type="button"
                onClick={() => setInspectionModal(prev => ({ ...prev, isOpen: false }))}
                className="text-slate-500 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-1">
              <div className="text-slate-200 font-bold">{inspectionModal.facilityName}</div>
              <div className="text-slate-400 text-[10px]">Assessment Code: {inspectionModal.assessmentCode}</div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-slate-400 uppercase block mb-1">
                  Verification Decision
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(['VERIFY', 'REJECT', 'DISPUTE'] as const).map(act => (
                    <button
                      key={act}
                      type="button"
                      onClick={() => setInspectionModal(prev => ({ ...prev, action: act }))}
                      className={`py-1.5 rounded font-bold text-center transition ${
                        inspectionModal.action === act
                          ? act === 'VERIFY' ? 'bg-emerald-600 text-white' : act === 'REJECT' ? 'bg-red-600 text-white' : 'bg-amber-600 text-white'
                          : 'bg-obsidian-900 text-slate-400 border border-obsidian-750'
                      }`}
                    >
                      {act}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 uppercase block mb-1">
                  Certified Damage Level
                </label>
                <select
                  value={inspectionModal.damageLevel}
                  onChange={(e) => setInspectionModal(prev => ({ ...prev, damageLevel: e.target.value }))}
                  className="w-full bg-obsidian-900 border border-obsidian-750 rounded p-2 text-slate-100 font-bold"
                >
                  <option value="NONE">NONE (Intact)</option>
                  <option value="MINOR">MINOR (&lt; 20% loss)</option>
                  <option value="MODERATE">MODERATE (20–50% loss)</option>
                  <option value="SEVERE">SEVERE (50–80% loss)</option>
                  <option value="DESTROYED">DESTROYED (&gt; 80% loss)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 uppercase block mb-1">
                  Mandatory Engineering Rationale
                </label>
                <textarea
                  rows={2}
                  value={inspectionModal.notes}
                  onChange={(e) => setInspectionModal(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Mandatory engineering notes certifying verification decision..."
                  className="w-full bg-obsidian-900 border border-obsidian-750 rounded p-2 text-slate-100"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-obsidian-750">
              <button
                type="button"
                onClick={() => setInspectionModal(prev => ({ ...prev, isOpen: false }))}
                className="px-3 py-1.5 text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleInspectionVerify}
                disabled={inspectionVerifyLoading || inspectionModal.notes.trim().length < 5}
                className="px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded flex items-center gap-1 disabled:opacity-40"
              >
                {inspectionVerifyLoading ? 'Submitting...' : 'Commit Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
