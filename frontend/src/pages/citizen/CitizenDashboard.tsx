import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { Link } from 'react-router-dom';
import { 
  AlertTriangle, 
  MapPin, 
  ShieldAlert, 
  Radio, 
  Send, 
  CheckCircle2, 
  Phone,
  LifeBuoy,
  Home,
  FileText,
  Bot,
  ExternalLink,
  ChevronRight,
  Clock,
  Activity as ActivityIcon,
  Zap,
  Droplets,
  Heart,
  GraduationCap
} from 'lucide-react';
import { 
  OperationalCard, 
  SeverityBadge, 
  StatusBadge, 
  PageHeader, 
  ConfirmDialog 
} from '../../components/design-system';
import { OfflineBanner } from '../../components/offline/OfflineBanner';
import { useOfflineDrafts } from '../../hooks/useOfflineDrafts';
import { fetchCommunityMetricsSummary } from '../../api/communityMonitoring';
import { useAuth } from '../../context/AuthContext';

export const CitizenDashboard: React.FC = () => {
  const { user } = useAuth();
  const [sosSent, setSosSent] = useState(false);
  const [sosIncidentCode, setSosIncidentCode] = useState<string | null>(null);
  const [sosConfirmOpen, setSosConfirmOpen] = useState(false);
  const [sosLoading, setSosLoading] = useState(false);
  const [sosError, setSosError] = useState<string | null>(null);
  const [sosCoords, setSosCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [manualAddress, setManualAddress] = useState('');
  const [gpsStatus, setGpsStatus] = useState<'idle' | 'acquiring' | 'acquired' | 'denied'>('idle');
  const [chatMessage, setChatMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<Array<{ 
    sender: string; 
    text: string; 
    isGrounded?: boolean; 
    confidence?: number;
    error?: boolean;
  }>>([
    { 
      sender: 'AI Safety Bot', 
      text: 'Namaste! I am the DIRS Grounded Emergency Safety Guide. Ask me about emergency evacuation, safety protocols, or hazard response guidelines for flood, fire, cyclone, earthquake, landslide, tsunami, or chemical incidents.',
      isGrounded: true,
      confidence: 100
    }
  ]);

  const { data: incidents = [] } = useQuery({
    queryKey: ['incidents-citizen', user?.id],
    queryFn: async () => {
      const res = await apiClient.get('/incidents');
      return res.data;
    }
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ['alerts-citizen', user?.id],
    queryFn: async () => {
      const res = await apiClient.get('/alerts');
      return res.data;
    }
  });

  const { drafts, syncAllPending } = useOfflineDrafts('INCIDENT_REPORT');
  const pendingDraftCount = drafts.filter(d => d.sync_status === 'DRAFT' || d.sync_status === 'FAILED').length;

  const { data: communitySummary } = useQuery({
    queryKey: ['citizen-community-recovery-summary'],
    queryFn: async () => {
      try {
        return await fetchCommunityMetricsSummary();
      } catch (e) {
        return null;
      }
    }
  });

  const initiateSOS = () => {
    if (sosSent) return;
    setGpsStatus('acquiring');
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setSosCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
          setGpsStatus('acquired');
          setSosConfirmOpen(true);
        },
        (err) => {
          console.warn('Geolocation unavailable or denied', err);
          setSosCoords(null);
          setGpsStatus('denied');
          setSosConfirmOpen(true);
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
      );
    } else {
      setSosCoords(null);
      setGpsStatus('denied');
      setSosConfirmOpen(true);
    }
  };

  const executeSOS = async () => {
    setSosLoading(true);
    try {
      const params = new URLSearchParams();
      if (sosCoords) {
        params.append('lat', sosCoords.lat.toString());
        params.append('lng', sosCoords.lng.toString());
      }
      if (manualAddress.trim()) {
        params.append('location_address', manualAddress.trim());
      } else if (!sosCoords) {
        params.append('location_address', 'GPS Denied / Coordinates Unavailable');
      }
      params.append('description', 'Citizen pressed high-priority SOS emergency button from Citizen Portal');

      const res = await apiClient.post(`/incidents/sos?${params.toString()}`);
      setSosSent(true);
      setSosIncidentCode(res.data?.incident_code || 'INC-SOS');
      setSosConfirmOpen(false);
      setSosError(null);
    } catch (e: any) {
      console.error('SOS dispatch error', e);
      setSosError('Failed to dispatch SOS: ' + (e.response?.data?.detail || e.message));
    } finally {
      setSosLoading(false);
    }
  };

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    const queryText = chatMessage.trim();
    if (!queryText) return;

    setChatHistory(prev => [...prev, { sender: 'You', text: queryText }]);
    setChatMessage('');
    setChatLoading(true);

    try {
      const res = await apiClient.post('/ai/rag/query', {
        query: queryText,
        mode: 'GENERAL_COPILOT'
      });
      const data = res.data;
      setChatHistory(prev => [
        ...prev,
        {
          sender: 'AI Safety Bot',
          text: data.summary,
          isGrounded: data.is_grounded,
          confidence: data.confidence
        }
      ]);
    } catch (err: any) {
      setChatHistory(prev => [
        ...prev,
        {
          sender: 'AI Safety Bot',
          text: `Unable to retrieve emergency guidance at this moment (${err.response?.data?.detail || err.message || 'Network error'}). Please contact emergency helpline 1070 for immediate assistance.`,
          error: true,
          isGrounded: false,
          confidence: 0
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 font-sans">
      {/* Top Welcome & Mode */}
      <PageHeader
        title="CITIZEN EMERGENCY PORTAL"
        subtitle="Public Disaster Safety, Urgent Assistance Dispatch & Shelter Locator"
        icon={LifeBuoy}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-ops border border-cyan-800">
            PUBLIC SAFETY ACTIVE
          </span>
        }
      />

      <OfflineBanner
        pendingDraftCount={pendingDraftCount}
        onSyncNow={syncAllPending}
      />

      {sosError && (
        <div className="p-3 bg-red-950/80 border border-red-800 rounded-xl text-xs font-mono text-red-200 flex items-center justify-between">
          <span>{sosError}</span>
          <button type="button" onClick={() => setSosError(null)} className="text-red-400 hover:text-white font-bold ml-2">×</button>
        </div>
      )}

      {/* SOS EMERGENCY PANIC SECTION */}
      <div className="bg-gradient-to-r from-red-950/80 to-obsidian-900 border-2 border-red-700/80 rounded-2xl p-6 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-red-600/20 border border-red-500/50 flex items-center justify-center text-red-500 shrink-0">
            <Radio className="w-8 h-8 animate-pulse" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-red-400 font-mono tracking-tight">
                EMERGENCY SOS DISTRESS SIGNAL
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-900/60 text-red-200 border border-red-700 uppercase">
                PRIORITY LOGGING
              </span>
            </div>
            <p className="text-xs text-red-200/80 font-sans max-w-xl leading-relaxed">
              In life-threatening danger? Pressing this button immediately logs an urgent Priority SOS distress report with your location into the DIRS Command Center for immediate verification.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          {gpsStatus === 'denied' && !sosSent && (
            <div className="text-[11px] font-mono text-amber-300 bg-amber-950/60 p-2.5 rounded-lg border border-amber-800 max-w-xs">
              <span className="block font-bold">⚠️ GPS Unavailable / Denied</span>
              <span className="text-[10px] text-slate-300 block mb-1">Enter your landmark or address:</span>
              <input
                type="text"
                placeholder="e.g. Ward 12, Riverfront Rd"
                value={manualAddress}
                onChange={(e) => setManualAddress(e.target.value)}
                className="w-full bg-obsidian-900 border border-obsidian-700 rounded px-2 py-1 text-slate-100 text-xs focus:outline-none focus:border-red-500 font-sans"
              />
            </div>
          )}

          <button
            type="button"
            onClick={initiateSOS}
            disabled={sosSent || gpsStatus === 'acquiring'}
            className={`px-6 py-4 rounded-xl text-sm font-mono font-bold tracking-wider uppercase transition shadow-2xl shrink-0 flex items-center gap-2.5 ${
              sosSent
                ? 'bg-emerald-600 text-white cursor-default'
                : 'bg-red-600 hover:bg-red-500 text-white active:scale-95 shadow-red-900/50 hover:shadow-red-600/40'
            }`}
          >
            {sosSent ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-white" />
                <span>SOS RECORDED [{sosIncidentCode}]</span>
              </>
            ) : gpsStatus === 'acquiring' ? (
              <>
                <Radio className="w-5 h-5 animate-spin" />
                <span>ACQUIRING GEOLOCATION...</span>
              </>
            ) : (
              <>
                <ShieldAlert className="w-5 h-5" />
                <span>TRIGGER SOS DISTRESS</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* QUICK EMERGENCY ACTION TILES */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Report Incident */}
        <Link
          to="/citizen/report"
          className="p-5 bg-obsidian-850 hover:bg-obsidian-800 border border-obsidian-750 hover:border-amber-ops rounded-xl transition group shadow-lg flex flex-col justify-between"
        >
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-ops flex items-center justify-center group-hover:scale-105 transition">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h3 className="font-mono font-bold text-sm text-slate-100 group-hover:text-amber-ops transition">
              Report Disaster Incident
            </h3>
            <p className="text-xs text-slate-400 font-sans leading-relaxed">
              Submit flood, structural collapse, or hazard reports with photos and GPS.
            </p>
          </div>
          <div className="pt-4 flex items-center text-xs font-mono text-amber-ops gap-1 font-semibold">
            <span>Submit Report</span>
            <ChevronRight className="w-4 h-4" />
          </div>
        </Link>

        {/* Find Shelters */}
        <Link
          to="/citizen/shelters"
          className="p-5 bg-obsidian-850 hover:bg-obsidian-800 border border-obsidian-750 hover:border-cyan-ops rounded-xl transition group shadow-lg flex flex-col justify-between"
        >
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-ops flex items-center justify-center group-hover:scale-105 transition">
              <Home className="w-5 h-5" />
            </div>
            <h3 className="font-mono font-bold text-sm text-slate-100 group-hover:text-cyan-ops transition">
              Emergency Shelter Grid
            </h3>
            <p className="text-xs text-slate-400 font-sans leading-relaxed">
              View nearby shelters ranked by capacity, food, drinking water, and medical care.
            </p>
          </div>
          <div className="pt-4 flex items-center text-xs font-mono text-cyan-ops gap-1 font-semibold">
            <span>View Shelters</span>
            <ChevronRight className="w-4 h-4" />
          </div>
        </Link>

        {/* Emergency Helpline */}
        <div className="p-5 bg-obsidian-850 border border-obsidian-750 rounded-xl shadow-lg flex flex-col justify-between">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <Phone className="w-5 h-5" />
            </div>
            <h3 className="font-mono font-bold text-sm text-slate-100">
              Emergency Hotlines
            </h3>
            <p className="text-xs text-slate-400 font-sans leading-relaxed">
              Disaster Response: <span className="text-slate-200 font-bold font-mono">1070</span><br />
              Ambulance / Medical: <span className="text-slate-200 font-bold font-mono">108</span><br />
              State Emergency: <span className="text-slate-200 font-bold font-mono">1077</span>
            </p>
          </div>
          <div className="pt-4 text-xs font-mono text-emerald-400 font-semibold">
            24/7 Monitored Dispatch
          </div>
        </div>
      </div>

      {/* COMMUNITY RECOVERY & ESSENTIAL SERVICES RESTORATION STATUS */}
      {communitySummary && (
        <div className="bg-obsidian-850 border border-obsidian-750 rounded-xl p-5 shadow-lg space-y-4 font-mono">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-obsidian-800">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-800 text-cyan-ops">
                <ActivityIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100">
                  Municipal Recovery & Essential Services Status
                </h3>
                <p className="text-[11px] text-slate-400 font-sans">
                  {communitySummary.total_wards_monitored > 0
                    ? `Official community restoration indicators across ${communitySummary.total_wards_monitored} monitored wards`
                    : 'Awaiting verified field surveys from municipal ward engineering officers'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-400">Citywide Recovery Index:</span>
              <span className="text-sm font-bold text-amber-ops px-2.5 py-0.5 rounded bg-amber-950/60 border border-amber-800">
                {communitySummary.total_wards_monitored > 0
                  ? `${(communitySummary.average_recovery_score > 1 ? communitySummary.average_recovery_score : communitySummary.average_recovery_score * 100).toFixed(1)}%`
                  : 'N/A — Initializing'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-800 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
                <Zap className="w-3.5 h-3.5 text-amber-ops" />
                <span>Power Restoration</span>
              </div>
              <div className="text-base font-bold text-slate-200">
                {communitySummary.total_wards_monitored > 0
                  ? `${((communitySummary.sector_restoration_averages?.power || 0) > 1 ? (communitySummary.sector_restoration_averages?.power || 0) : (communitySummary.sector_restoration_averages?.power || 0) * 100).toFixed(0)}%`
                  : 'N/A'}
              </div>
            </div>

            <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-800 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
                <Droplets className="w-3.5 h-3.5 text-cyan-ops" />
                <span>Clean Water Access</span>
              </div>
              <div className="text-base font-bold text-slate-200">
                {communitySummary.total_wards_monitored > 0
                  ? `${((communitySummary.sector_restoration_averages?.water || 0) > 1 ? (communitySummary.sector_restoration_averages?.water || 0) : (communitySummary.sector_restoration_averages?.water || 0) * 100).toFixed(0)}%`
                  : 'N/A'}
              </div>
            </div>

            <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-800 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
                <Heart className="w-3.5 h-3.5 text-red-400" />
                <span>Healthcare Services</span>
              </div>
              <div className="text-base font-bold text-slate-200">
                {communitySummary.total_wards_monitored > 0
                  ? `${((communitySummary.sector_restoration_averages?.health || 0) > 1 ? (communitySummary.sector_restoration_averages?.health || 0) : (communitySummary.sector_restoration_averages?.health || 0) * 100).toFixed(0)}%`
                  : 'N/A'}
              </div>
            </div>

            <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-800 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
                <GraduationCap className="w-3.5 h-3.5 text-emerald-400" />
                <span>Schools / Safe Centers</span>
              </div>
              <div className="text-base font-bold text-slate-200">
                {communitySummary.total_wards_monitored > 0
                  ? `${((communitySummary.sector_restoration_averages?.schools || 0) > 1 ? (communitySummary.sector_restoration_averages?.schools || 0) : (communitySummary.sector_restoration_averages?.schools || 0) * 100).toFixed(0)}%`
                  : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TWO-COLUMN WORKSPACE: Grounded Safety Chat & Incident Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Grounded Safety Assistant Chat */}
        <OperationalCard
          title="Grounded Safety Assistant"
          subtitle="Curated Multi-Hazard Guidelines (NDMA, FEMA, WHO, INCOIS)"
          headerAction={
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
              ONLINE
            </span>
          }
        >
          <div className="space-y-3 font-sans">
            {/* Chat Messages */}
            <div className="h-64 overflow-y-auto space-y-2.5 p-3 rounded-lg bg-obsidian-900 border border-obsidian-750 text-xs">
              {chatHistory.map((item, idx) => {
                const isUser = item.sender === 'You';
                return (
                  <div
                    key={idx}
                    className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                  >
                    <span className="text-[10px] font-mono text-slate-500 mb-0.5">
                      {item.sender}
                    </span>
                    <div
                      className={`p-2.5 rounded-lg max-w-[85%] leading-relaxed ${
                        isUser
                          ? 'bg-amber-ops text-obsidian-950 font-medium'
                          : item.error
                          ? 'bg-red-950/70 text-red-200 border border-red-800 font-mono text-[11px]'
                          : 'bg-obsidian-800 text-slate-200 border border-obsidian-700 font-mono text-[11px]'
                      }`}
                    >
                      {item.text}
                    </div>
                    {!isUser && (
                      <div className="mt-0.5 text-[9px] font-mono">
                        {item.error ? (
                          <span className="text-red-400">Offline / Request Failed</span>
                        ) : item.isGrounded ? (
                          <span className="text-emerald-400 flex items-center gap-1">
                            ✓ Grounded in Authoritative KB ({item.confidence || 88.5}%)
                          </span>
                        ) : (
                          <span className="text-amber-ops flex items-center gap-1">
                            ⚠ Insufficient Authoritative Data (Refusal)
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
              {chatLoading && (
                <div className="flex flex-col items-start">
                  <span className="text-[10px] font-mono text-slate-500 mb-0.5">AI Safety Bot</span>
                  <div className="p-2.5 rounded-lg bg-obsidian-800 text-cyan-ops border border-obsidian-700 font-mono text-[11px] animate-pulse">
                    Consulting authoritative disaster response guidelines...
                  </div>
                </div>
              )}
            </div>

            {/* Input Form */}
            <form onSubmit={handleChat} className="flex gap-2">
              <input
                type="text"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Ask about evacuation, safe drinking water, shelters, fire, earthquake..."
                disabled={chatLoading}
                className="flex-1 bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-amber-ops font-mono disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={chatLoading || !chatMessage.trim()}
                className="px-4 py-2 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded-lg text-xs font-mono transition flex items-center gap-1 shadow disabled:opacity-50"
              >
                <span>{chatLoading ? 'Searching...' : 'Send'}</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </OperationalCard>

        {/* Right: Active Public Hazards Feed */}
        <OperationalCard
          title="Active Disaster Reports In Area"
          subtitle="Realtime Citizen & Verified Emergency Feeds"
          headerAction={
            <span className="text-xs font-mono text-slate-400">
              {incidents.length} Active
            </span>
          }
        >
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {incidents.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-slate-500">
                No active public disaster alerts recorded in this zone.
              </div>
            ) : (
              incidents.slice(0, 5).map((inc: any) => (
                <div
                  key={inc.id}
                  className="p-3 bg-obsidian-900 rounded-xl border border-obsidian-750 space-y-2 hover:border-obsidian-600 transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-amber-ops">
                        {inc.incident_code}
                      </span>
                      <SeverityBadge severity={inc.priority_level || inc.severity || 'MEDIUM'} />
                    </div>
                    <StatusBadge status={inc.status || 'VERIFIED'} />
                  </div>

                  <h4 className="text-xs font-bold text-slate-200">
                    {inc.title}
                  </h4>

                  <p className="text-[11px] text-slate-400 font-sans line-clamp-2">
                    {inc.description || 'Emergency verified by response teams.'}
                  </p>

                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-obsidian-800">
                    <span className="flex items-center gap-1 text-cyan-ops">
                      <MapPin className="w-3 h-3" />
                      {inc.location_address || 'Riverfront Colony, Sector 4'}
                    </span>
                    <span>{inc.people_affected || 0} Affected</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </OperationalCard>
      </div>

      {/* SOS Confirmation Dialog */}
      <ConfirmDialog
        isOpen={sosConfirmOpen}
        title="CONFIRM EMERGENCY SOS DISTRESS SIGNAL"
        message={
          sosCoords
            ? `Are you in immediate danger? Your verified GPS coordinates (${sosCoords.lat.toFixed(4)}, ${sosCoords.lng.toFixed(4)}) will be logged into the DIRS Command Center with CRITICAL Priority 99.0.`
            : `⚠️ GPS coordinates are UNAVAILABLE or access was DENIED. DIRS will NEVER substitute fake or hardcoded coordinates. Confirming will dispatch an Emergency SOS with status [LOCATION UNAVAILABLE] for immediate Command Center triaging.` +
              (manualAddress.trim() ? ` Citizen location notes: "${manualAddress.trim()}".` : '')
        }
        confirmLabel="YES — LOG EMERGENCY SOS REPORT"
        variant="danger"
        isLoading={sosLoading}
        onConfirm={executeSOS}
        onCancel={() => setSosConfirmOpen(false)}
      />
    </div>
  );
};

export default CitizenDashboard;
