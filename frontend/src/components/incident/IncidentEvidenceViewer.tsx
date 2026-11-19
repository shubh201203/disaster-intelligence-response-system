import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  Eye, 
  ExternalLink, 
  X, 
  Image as ImageIcon, 
  AlertCircle, 
  Loader2, 
  ZoomIn 
} from 'lucide-react';
import { resolveMediaUrl, apiClient } from '../../api/client';

export interface IncidentEvidenceViewerProps {
  incident: {
    id: string;
    incident_code?: string;
    title?: string;
    media_urls?: string[];
  } | null;
  className?: string;
}

interface MediaItem {
  url: string;
  id?: string;
  fileName?: string;
  fileSize?: number;
}

export const IncidentEvidenceViewer: React.FC<IncidentEvidenceViewerProps> = ({
  incident,
  className = ''
}) => {
  const [mediaList, setMediaList] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMap, setErrorMap] = useState<Record<string, boolean>>({});
  const [activeModalImage, setActiveModalImage] = useState<MediaItem | null>(null);

  // Fetch or extract media items whenever selected incident changes
  useEffect(() => {
    let isMounted = true;
    setErrorMap({});
    setActiveModalImage(null);

    if (!incident || !incident.id) {
      setMediaList([]);
      return;
    }

    const loadMedia = async () => {
      setLoading(true);
      try {
        // Try fetching rich media records from backend detail endpoint
        const res = await apiClient.get(`/incidents/${incident.id}/media`);
        if (isMounted && Array.isArray(res.data) && res.data.length > 0) {
          const items: MediaItem[] = res.data.map((m: any) => ({
            url: resolveMediaUrl(m.file_path),
            id: m.id,
            fileName: m.file_name || 'incident_photo.jpg',
            fileSize: m.file_size
          }));
          setMediaList(items);
          setLoading(false);
          return;
        }
      } catch (err) {
        // Fallback gracefully to incident.media_urls if /media endpoint call fails
      }

      // Fallback: use incident.media_urls array directly
      if (isMounted) {
        const fallbackUrls = incident.media_urls || [];
        const items: MediaItem[] = fallbackUrls.map((rawUrl, idx) => ({
          url: resolveMediaUrl(rawUrl),
          id: `fallback-${idx}`,
          fileName: `evidence_photo_${idx + 1}.jpg`
        }));
        setMediaList(items);
        setLoading(false);
      }
    };

    loadMedia();

    return () => {
      isMounted = false;
    };
  }, [incident?.id, incident?.media_urls]);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveModalImage(null);
      }
    };
    if (activeModalImage) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeModalImage]);

  const handleImageError = (url: string) => {
    setErrorMap((prev) => ({ ...prev, [url]: true }));
  };

  if (!incident) {
    return null;
  }

  return (
    <div className={`p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 space-y-2.5 ${className}`}>
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono text-cyan-ops uppercase font-bold tracking-wider flex items-center gap-1.5">
          <Camera className="w-3.5 h-3.5" />
          <span>Evidence / Incident Photographic Evidence</span>
        </span>
        {mediaList.length > 0 && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800">
            {mediaList.length} {mediaList.length === 1 ? 'ATTACHMENT' : 'ATTACHMENTS'}
          </span>
        )}
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="p-4 bg-obsidian-950/80 rounded border border-obsidian-800 flex items-center justify-center gap-2 text-xs font-mono text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin text-cyan-ops" />
          <span>Retrieving verified incident media...</span>
        </div>
      ) : mediaList.length === 0 ? (
        /* Empty State */
        <div className="p-4 bg-obsidian-950/60 rounded border border-dashed border-obsidian-800 text-center space-y-1">
          <ImageIcon className="w-5 h-5 mx-auto text-slate-600" />
          <p className="text-[11px] font-mono text-slate-400 font-semibold">
            No Photographic Evidence Attached
          </p>
          <p className="text-[10px] text-slate-600 font-sans">
            Citizen or field reporter did not include media attachments with this dispatch.
          </p>
        </div>
      ) : (
        /* Image Thumbnails Grid */
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {mediaList.map((item, index) => {
            const hasError = errorMap[item.url];
            return (
              <div
                key={item.id || item.url || index}
                className="group relative bg-obsidian-950 border border-obsidian-800 hover:border-cyan-ops/80 rounded-lg overflow-hidden transition shadow-sm"
              >
                {hasError ? (
                  /* Error State */
                  <div className="h-24 flex flex-col items-center justify-center p-2 text-center bg-red-950/20 text-red-400 space-y-1">
                    <AlertCircle className="w-4 h-4" />
                    <span className="text-[9px] font-mono leading-tight">Image unavailable</span>
                  </div>
                ) : (
                  /* Image Thumbnail */
                  <div 
                    onClick={() => setActiveModalImage(item)}
                    className="cursor-pointer relative h-24 overflow-hidden bg-black/40 flex items-center justify-center"
                    title="Click to view full-resolution evidence"
                  >
                    <img
                      src={item.url}
                      alt={item.fileName || `Incident Evidence ${index + 1}`}
                      onError={() => handleImageError(item.url)}
                      className="w-full h-full object-cover transition duration-200 group-hover:scale-105"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-1.5 text-white">
                      <ZoomIn className="w-4 h-4 text-cyan-ops" />
                      <span className="text-[10px] font-mono font-bold">Inspect</span>
                    </div>
                  </div>
                )}

                {/* Subtitle / File Information */}
                <div className="p-1.5 bg-obsidian-900 border-t border-obsidian-800 text-[10px] font-mono text-slate-400 flex items-center justify-between">
                  <span className="truncate max-w-[90px]" title={item.fileName}>
                    {item.fileName}
                  </span>
                  {!hasError && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(item.url, '_blank', 'noopener,noreferrer');
                      }}
                      className="text-slate-500 hover:text-cyan-ops p-0.5 transition"
                      title="Open full image in new tab"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Lightbox / Modal for Full Size Inspection */}
      {activeModalImage && (
        <div 
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setActiveModalImage(null)}
        >
          <div 
            className="relative max-w-4xl w-full bg-obsidian-900 border border-cyan-800/80 rounded-xl overflow-hidden shadow-2xl space-y-3 p-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-obsidian-750 pb-2.5">
              <div className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-cyan-ops" />
                <span className="text-xs font-mono font-bold text-slate-100">
                  {incident.incident_code ? `[${incident.incident_code}] ` : ''}
                  {activeModalImage.fileName || 'Incident Photographic Evidence'}
                </span>
                {activeModalImage.fileSize && (
                  <span className="text-[10px] font-mono text-slate-500">
                    ({(activeModalImage.fileSize / 1024).toFixed(1)} KB)
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={activeModalImage.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1 bg-obsidian-800 hover:bg-obsidian-750 text-cyan-ops text-xs font-mono rounded border border-obsidian-700 flex items-center gap-1 transition"
                  title="Open full image in raw tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Raw View</span>
                </a>
                <button
                  type="button"
                  onClick={() => setActiveModalImage(null)}
                  className="p-1 rounded-lg bg-obsidian-800 hover:bg-red-900/60 text-slate-400 hover:text-red-300 transition"
                  title="Close viewer (Esc)"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Modal Image Display */}
            <div className="flex items-center justify-center bg-obsidian-950 rounded-lg p-2 min-h-[300px] max-h-[70vh] overflow-hidden">
              <img
                src={activeModalImage.url}
                alt={activeModalImage.fileName || 'Full size incident evidence'}
                className="max-h-[68vh] max-w-full rounded object-contain"
              />
            </div>

            {/* Modal Footer */}
            <div className="text-[10px] font-mono text-slate-500 flex items-center justify-between pt-1">
              <span>Incident Reference: {incident.title || incident.id}</span>
              <span className="text-slate-400">Click anywhere outside or press ESC to exit</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IncidentEvidenceViewer;
