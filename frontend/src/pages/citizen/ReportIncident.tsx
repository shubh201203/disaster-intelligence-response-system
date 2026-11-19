import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../api/client';
import { 
  AlertTriangle, 
  MapPin, 
  CheckCircle2, 
  ArrowLeft, 
  Compass, 
  Send,
  Users,
  Shield,
  Activity,
  Save,
  WifiOff,
  UploadCloud,
  X,
  Image as ImageIcon
} from 'lucide-react';
import { OperationalCard, PageHeader } from '../../components/design-system';
import { useOfflineDrafts } from '../../hooks/useOfflineDrafts';
import { OfflineBanner } from '../../components/offline/OfflineBanner';
import { DraftSyncManager } from '../../components/offline/DraftSyncManager';
import { OfflineDraft } from '../../utils/offlineDraftStore';
import { useAuth } from '../../context/AuthContext';

export const ReportIncident: React.FC = () => {
  const { user } = useAuth();
  const [title, setTitle] = useState('');
  const [disasterType, setDisasterType] = useState('FLOOD');
  const [description, setDescription] = useState('');
  const [lat, setLat] = useState<number>(13.0827);
  const [lng, setLng] = useState<number>(80.2707);
  const [address, setAddress] = useState('Riverfront Colony, Sector 4');
  const [peopleAffected, setPeopleAffected] = useState(10);
  const [injuries, setInjuries] = useState(0);
  const [vulnerableCount, setVulnerableCount] = useState(2);
  const [infraDamage, setInfraDamage] = useState('Submerged access road, electrical feeder offline');
  const [activeDraftId, setActiveDraftId] = useState<string | undefined>(undefined);
  const [submitted, setSubmitted] = useState(false);
  const [submittedOffline, setSubmittedOffline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusNotification, setStatusNotification] = useState<string | null>(null);

  // Image Upload State
  interface AttachedImage {
    id: string;
    file?: File;
    preview: string;
    name: string;
    size?: number;
  }
  const [attachedImages, setAttachedImages] = useState<AttachedImage[]>([]);
  const [imageError, setImageError] = useState<string | null>(null);

  const navigate = useNavigate();

  const {
    drafts,
    loading: draftsLoading,
    isOnline,
    saveCurrentDraft,
    syncDraft,
    syncAllPending,
    removeDraft,
    clearCompleted
  } = useOfflineDrafts('INCIDENT_REPORT');

  const pendingDraftCount = drafts.filter(d => d.sync_status === 'DRAFT' || d.sync_status === 'FAILED').length;

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude);
          setLng(pos.coords.longitude);
        },
        () => {
          alert('Could not acquire device GPS. Using default coordinates.');
        }
      );
    }
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setImageError(null);
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // Validate MIME types and extensions
    const allowedMime = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    const allowedExts = ['.jpg', '.jpeg', '.png', '.webp'];

    Array.from(files).forEach((file) => {
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();

      if (!allowedMime.includes(file.type) && !allowedExts.includes(fileExt)) {
        setImageError(`Unsupported image format: ${file.name}. Allowed: JPG, JPEG, PNG, WEBP.`);
        return;
      }

      // Validate 10MB limit
      if (file.size > 10 * 1024 * 1024) {
        setImageError(`Image exceeds maximum 10MB limit: ${file.name}`);
        return;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        setAttachedImages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            file,
            preview: event.target?.result as string,
            name: file.name,
            size: file.size
          }
        ]);
      };
      reader.readAsDataURL(file);
    });

    e.target.value = '';
  };

  const handleRemoveImage = (id: string) => {
    setAttachedImages((prev) => prev.filter((img) => img.id !== id));
  };

  const getTargetDashboard = () => {
    if (user?.role === 'VOLUNTEER') return '/volunteer';
    if (user?.role === 'GOVT') return '/admin';
    return '/citizen';
  };

  const getPayload = () => ({
    title: title.trim() || `${disasterType} incident reported near ${address}`,
    disaster_type: disasterType,
    description: description.trim() || 'Citizen reported emergency observation.',
    latitude: lat,
    longitude: lng,
    location_address: address,
    people_affected: Number(peopleAffected),
    injuries: Number(injuries),
    vulnerable_count: Number(vulnerableCount),
    infrastructure_damage: infraDamage,
    image_preview: attachedImages[0]?.preview || undefined,
    image_filename: attachedImages[0]?.name || undefined,
    image_previews: attachedImages.map((img) => ({ preview: img.preview, name: img.name, size: img.size })),
    media_urls: attachedImages.map((img) => img.preview)
  });

  const handleSaveDraft = async () => {
    try {
      const payload = getPayload();
      const saved = await saveCurrentDraft(payload, activeDraftId);
      setActiveDraftId(saved.client_draft_id);
      setStatusNotification('Draft successfully saved to local device storage (IndexedDB).');
      setTimeout(() => setStatusNotification(null), 4000);
    } catch (e: any) {
      alert('Failed to save local draft: ' + e.message);
    }
  };

  const handleLoadDraft = (draft: OfflineDraft) => {
    setActiveDraftId(draft.client_draft_id);
    const p = draft.payload;
    if (p.title) setTitle(p.title);
    if (p.disaster_type) setDisasterType(p.disaster_type);
    if (p.description) setDescription(p.description);
    if (p.latitude) setLat(p.latitude);
    if (p.longitude) setLng(p.longitude);
    if (p.location_address) setAddress(p.location_address);
    if (p.people_affected !== undefined) setPeopleAffected(p.people_affected);
    if (p.injuries !== undefined) setInjuries(p.injuries);
    if (p.vulnerable_count !== undefined) setVulnerableCount(p.vulnerable_count);
    if (p.infrastructure_damage) setInfraDamage(p.infrastructure_damage);
    if (p.image_previews && Array.isArray(p.image_previews)) {
      setAttachedImages(
        p.image_previews.map((item: any) => ({
          id: crypto.randomUUID(),
          preview: item.preview || item,
          name: item.name || 'Saved Draft Photo',
          size: item.size
        }))
      );
    } else if (p.image_preview) {
      setAttachedImages([
        {
          id: crypto.randomUUID(),
          preview: p.image_preview,
          name: p.image_filename || 'Saved Draft Photo'
        }
      ]);
    }
    setStatusNotification(`Loaded draft #${draft.client_draft_id.slice(0, 8)} into form.`);
    setTimeout(() => setStatusNotification(null), 3000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return; // Prevent duplicate submissions
    setLoading(true);
    const payload = getPayload();

    // 1. If currently offline, save directly to IndexedDB as queued draft
    if (!navigator.onLine) {
      try {
        await saveCurrentDraft(payload, activeDraftId);
        setSubmittedOffline(true);
      } catch (err: any) {
        alert('Failed to queue offline draft: ' + err.message);
      } finally {
        setLoading(false);
      }
      return;
    }

    // 2. If online, dispatch to backend
    try {
      const res = await apiClient.post('/incidents', {
        ...payload,
        client_draft_id: activeDraftId
      });
      const incidentId = res.data?.id;

      // If images were selected, upload each to the incident media endpoint
      if (incidentId && attachedImages.length > 0) {
        for (const img of attachedImages) {
          try {
            const formData = new FormData();
            if (img.file) {
              formData.append('file', img.file);
            } else if (img.preview && img.preview.startsWith('data:image/')) {
              // Convert base64 data URL to Blob for draft sync
              const [header, b64] = img.preview.split(',', 2);
              const mime = header.split(';')[0].replace('data:', '') || 'image/png';
              const byteChars = atob(b64);
              const byteNumbers = new Array(byteChars.length);
              for (let i = 0; i < byteChars.length; i++) {
                byteNumbers[i] = byteChars.charCodeAt(i);
              }
              const byteArray = new Uint8Array(byteNumbers);
              const blob = new Blob([byteArray], { type: mime });
              formData.append('file', blob, img.name || 'draft_photo.png');
            }
            await apiClient.post(`/incidents/${incidentId}/media`, formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
            });
          } catch (mediaErr) {
            console.warn(`Failed to upload media item ${img.name}:`, mediaErr);
          }
        }
      }

      if (activeDraftId) {
        await removeDraft(activeDraftId);
      }
      setSubmitted(true);
      setTimeout(() => {
        navigate(getTargetDashboard());
      }, 2000);
    } catch (err: any) {
      // If network fails during post, automatically rescue form by saving locally
      if (!err.response || err.message?.includes('Network Error')) {
        await saveCurrentDraft(payload, activeDraftId);
        setSubmittedOffline(true);
      } else {
        alert('Error submitting report: ' + (err.response?.data?.detail || err.message));
      }
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-md mx-auto my-16 bg-obsidian-850 border border-emerald-800 rounded-2xl p-8 text-center space-y-4 shadow-2xl">
        <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center text-emerald-400 mx-auto">
          <CheckCircle2 className="w-10 h-10" />
        </div>
        <h2 className="text-xl font-mono font-bold text-slate-100">
          Disaster Report Submitted
        </h2>
        <p className="text-xs text-slate-400 font-sans leading-relaxed">
          Report received by DIRS AI triage engine. AI Severity Classifier & Priority scorer are evaluating your incident for government verification.
        </p>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-3 py-1 rounded-full border border-emerald-800 inline-block">
          Redirecting to {user?.role === 'VOLUNTEER' ? 'Volunteer Hub' : user?.role === 'GOVT' ? 'Command Center' : 'Citizen Dashboard'}...
        </span>
      </div>
    );
  }

  if (submittedOffline) {
    return (
      <div className="max-w-md mx-auto my-16 bg-obsidian-850 border border-amber-800 rounded-2xl p-8 text-center space-y-4 shadow-2xl">
        <div className="w-16 h-16 rounded-full bg-amber-500/20 border border-amber-500/50 flex items-center justify-center text-amber-400 mx-auto">
          <WifiOff className="w-10 h-10" />
        </div>
        <h2 className="text-xl font-mono font-bold text-slate-100">
          Report Saved Locally (Offline)
        </h2>
        <p className="text-xs text-slate-300 font-sans leading-relaxed">
          You are currently offline. Your disaster report has been securely saved to your browser&apos;s local IndexedDB storage. It is queued for automatic synchronization as soon as internet connectivity returns.
        </p>
        <div className="pt-2 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => {
              setSubmittedOffline(false);
              navigate(getTargetDashboard());
            }}
            className="px-4 py-2 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold text-xs rounded-lg font-mono transition"
          >
            Go to Dashboard
          </button>
          <button
            type="button"
            onClick={() => setSubmittedOffline(false)}
            className="px-4 py-2 bg-obsidian-800 hover:bg-obsidian-750 text-slate-200 text-xs rounded-lg font-mono border border-obsidian-700 transition"
          >
            Submit Another Report
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12 font-sans">
      <OfflineBanner
        pendingDraftCount={pendingDraftCount}
        onSyncNow={syncAllPending}
      />

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/citizen')}
          className="text-xs font-mono text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>
        <div className="flex items-center gap-2">
          {activeDraftId && (
            <span className="text-[10px] font-mono text-cyan-ops bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
              EDITING DRAFT #{activeDraftId.slice(0, 6)}
            </span>
          )}
          <span className="text-[10px] font-mono text-amber-ops bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800">
            INCIDENT INTAKE FORM
          </span>
        </div>
      </div>

      {statusNotification && (
        <div className="p-3 bg-obsidian-850 border border-emerald-700/80 rounded-xl text-xs font-mono text-emerald-300 flex items-center justify-between">
          <span>{statusNotification}</span>
          <button type="button" onClick={() => setStatusNotification(null)} className="text-slate-400 hover:text-white font-bold">×</button>
        </div>
      )}

      <OperationalCard
        title="Report Emergency Disaster Incident"
        subtitle="Submit factual field telemetry to trigger AI verification and priority rescue allocation"
        headerAction={
          <button
            type="button"
            onClick={handleSaveDraft}
            className="px-3 py-1 bg-obsidian-800 hover:bg-obsidian-750 text-slate-300 rounded text-xs font-mono border border-obsidian-700 flex items-center gap-1 transition"
          >
            <Save className="w-3.5 h-3.5 text-amber-ops" />
            <span>Save Draft</span>
          </button>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4 font-mono text-xs">
          {/* Disaster Type & Title */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Disaster Type
              </label>
              <select
                value={disasterType}
                onChange={(e) => setDisasterType(e.target.value)}
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 font-bold focus:outline-none focus:border-amber-ops"
              >
                <option value="FLOOD">FLOOD</option>
                <option value="FIRE">FIRE</option>
                <option value="CYCLONE">CYCLONE</option>
                <option value="EARTHQUAKE">EARTHQUAKE</option>
                <option value="LANDSLIDE">LANDSLIDE</option>
                <option value="CHEMICAL">CHEMICAL HAZARD</option>
              </select>
            </div>

            <div className="sm:col-span-2">
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Incident Title / Headline
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Rising flood water inundating Ground Floor"
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Detailed Observation / Urgent Situation
            </label>
            <textarea
              required
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe current danger level, trapped persons, rising water rate, or immediate medical threats..."
              className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops"
            />
          </div>

          {/* Location details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
                Location Address / Landmark
              </label>
              <input
                type="text"
                required
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Street address, block, or prominent nearby landmark"
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops"
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
                  <Compass className="w-3 h-3" /> Auto-Detect GPS
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="any"
                  value={lat}
                  onChange={(e) => setLat(parseFloat(e.target.value))}
                  className="bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-amber-ops"
                />
                <input
                  type="number"
                  step="any"
                  value={lng}
                  onChange={(e) => setLng(parseFloat(e.target.value))}
                  className="bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-amber-ops"
                />
              </div>
            </div>
          </div>

          {/* Demographic impacts */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 space-y-1">
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block">
                Estimated Affected
              </label>
              <input
                type="number"
                min="1"
                value={peopleAffected}
                onChange={(e) => setPeopleAffected(parseInt(e.target.value) || 0)}
                className="w-full bg-obsidian-950 border border-obsidian-800 rounded px-2.5 py-1.5 text-slate-100 font-bold"
              />
            </div>

            <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 space-y-1">
              <label className="text-[10px] text-red-400 uppercase tracking-wider block">
                Known Injuries
              </label>
              <input
                type="number"
                min="0"
                value={injuries}
                onChange={(e) => setInjuries(parseInt(e.target.value) || 0)}
                className="w-full bg-obsidian-950 border border-obsidian-800 rounded px-2.5 py-1.5 text-slate-100 font-bold"
              />
            </div>

            <div className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 space-y-1">
              <label className="text-[10px] text-amber-ops uppercase tracking-wider block">
                Vulnerable (Elderly/Children)
              </label>
              <input
                type="number"
                min="0"
                value={vulnerableCount}
                onChange={(e) => setVulnerableCount(parseInt(e.target.value) || 0)}
                className="w-full bg-obsidian-950 border border-obsidian-800 rounded px-2.5 py-1.5 text-slate-100 font-bold"
              />
            </div>
          </div>

          {/* Infrastructure Damage */}
          <div>
            <label className="block text-[11px] text-slate-400 uppercase tracking-wider mb-1">
              Infrastructure Damage Notes
            </label>
            <input
              type="text"
              value={infraDamage}
              onChange={(e) => setInfraDamage(e.target.value)}
              placeholder="e.g. Bridge submerged, transformer blown, power cut..."
              className="w-full bg-obsidian-900 border border-obsidian-750 rounded-lg px-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-amber-ops"
            />
          </div>

          {/* Photographic Evidence Image Upload */}
          <div className="p-4 bg-obsidian-900/80 rounded-lg border border-obsidian-750 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-[11px] text-slate-300 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <UploadCloud className="w-4 h-4 text-cyan-ops" />
                <span>Photographic Evidence</span>
              </label>
              <span className="text-[10px] text-slate-500 font-mono">
                {attachedImages.length > 0 ? `${attachedImages.length} attached • ` : ''}JPG, PNG, WEBP (Max 10MB)
              </span>
            </div>

            {attachedImages.length > 0 ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {attachedImages.map((img) => (
                    <div key={img.id} className="relative group border border-cyan-800/80 rounded-lg p-2 bg-obsidian-950 flex flex-col justify-between">
                      <div className="relative h-28 flex items-center justify-center overflow-hidden rounded bg-black/40">
                        <img
                          src={img.preview}
                          alt={img.name}
                          className="max-h-full max-w-full object-contain rounded"
                        />
                        <button
                          type="button"
                          onClick={() => handleRemoveImage(img.id)}
                          className="absolute top-1 right-1 p-1 bg-red-600 hover:bg-red-500 text-white rounded-full transition shadow-lg"
                          title="Remove image"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <div className="text-[10px] font-mono text-cyan-ops mt-1.5 truncate flex items-center gap-1">
                        <ImageIcon className="w-3 h-3 shrink-0" />
                        <span className="truncate" title={img.name}>{img.name}</span>
                        {img.size && <span className="text-slate-500 shrink-0">({(img.size / 1024).toFixed(0)}KB)</span>}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Add More Images Button */}
                {attachedImages.length < 5 && (
                  <div>
                    <input
                      type="file"
                      id="incident-image-input-more"
                      accept="image/jpeg,image/png,image/webp,image/jpg"
                      multiple
                      onChange={handleImageSelect}
                      className="hidden"
                    />
                    <label
                      htmlFor="incident-image-input-more"
                      className="cursor-pointer border border-dashed border-obsidian-700 hover:border-cyan-ops/60 rounded-lg p-2 text-center text-xs font-mono text-cyan-ops flex items-center justify-center gap-1.5 hover:bg-obsidian-950/80 transition"
                    >
                      <UploadCloud className="w-3.5 h-3.5" />
                      <span>+ Attach Another Image ({5 - attachedImages.length} slots remaining)</span>
                    </label>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  id="incident-image-input"
                  accept="image/jpeg,image/png,image/webp,image/jpg"
                  multiple
                  onChange={handleImageSelect}
                  className="hidden"
                />
                <label
                  htmlFor="incident-image-input"
                  className="cursor-pointer border-2 border-dashed border-obsidian-750 hover:border-cyan-ops/60 rounded-lg p-4 flex flex-col items-center justify-center gap-1.5 text-center transition bg-obsidian-950/60 hover:bg-obsidian-950"
                >
                  <UploadCloud className="w-6 h-6 text-slate-500" />
                  <span className="text-xs text-slate-300 font-bold">Upload Incident Photos</span>
                  <span className="text-[10px] text-slate-500 font-sans">
                    Optional photographic proof verified by computer vision damage assessment (supports multiple photos)
                  </span>
                </label>
              </div>
            )}

            {imageError && (
              <p className="text-[11px] text-red-400 font-mono font-semibold">{imageError}</p>
            )}
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="w-full sm:flex-1 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold py-3 rounded-lg text-xs font-mono transition flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
            >
              {loading ? (
                <span>Submitting to Dispatch AI...</span>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>
                    {!isOnline ? 'SAVE OFFLINE DRAFT (QUEUED FOR SYNC)' : 'SUBMIT DISASTER REPORT FOR VERIFICATION'}
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

      {/* Offline Draft Management Queue */}
      <DraftSyncManager
        drafts={drafts}
        loading={draftsLoading}
        isOnline={isOnline}
        onSyncDraft={syncDraft}
        onSyncAll={syncAllPending}
        onDeleteDraft={removeDraft}
        onClearCompleted={clearCompleted}
        onLoadDraft={handleLoadDraft}
        title="Local Incident Report Drafts (IndexedDB)"
      />
    </div>
  );
};

export default ReportIncident;
