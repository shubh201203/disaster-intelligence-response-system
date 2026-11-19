import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import { 
  Navigation, 
  MapPin, 
  ExternalLink, 
  Copy, 
  Check, 
  X, 
  Compass, 
  Smartphone, 
  AlertCircle 
} from 'lucide-react';

export interface NavigationModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  address: string;
  latitude: number;
  longitude: number;
  distanceKm?: number;
  badge?: React.ReactNode;
}

export const NavigationModal: React.FC<NavigationModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle = 'Destination Coordinates & Navigation Links',
  address,
  latitude,
  longitude,
  distanceKm,
  badge
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const validLat = typeof latitude === 'number' && !isNaN(latitude) ? latitude : 0.0;
  const validLng = typeof longitude === 'number' && !isNaN(longitude) ? longitude : 0.0;
  const coordString = `${validLat.toFixed(6)}, ${validLng.toFixed(6)}`;

  // External Navigation URLs
  const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${validLat},${validLng}`;
  const geoUri = `geo:${validLat},${validLng}?q=${validLat},${validLng}(${encodeURIComponent(title)})`;

  const handleCopy = () => {
    navigator.clipboard.writeText(coordString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return ReactDOM.createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-sm animate-fade-in font-sans">
      <div 
        className="w-full max-w-lg bg-obsidian-900 border border-obsidian-700/90 rounded-2xl shadow-2xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nav-modal-title"
      >
        {/* Header */}
        <div className="p-4 bg-obsidian-850 border-b border-obsidian-750 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-950/80 border border-cyan-800 text-cyan-ops">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 id="nav-modal-title" className="text-sm font-bold text-slate-100 font-mono tracking-tight">
                  {title}
                </h3>
                {badge}
              </div>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                {subtitle}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-obsidian-800 transition"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 space-y-4 font-mono text-xs">
          {/* Waypoint Address & Distance */}
          <div className="p-3.5 bg-obsidian-950 rounded-xl border border-obsidian-800 space-y-2">
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-cyan-ops shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Target Location</span>
                <p className="text-slate-200 font-sans text-xs mt-0.5 font-medium">{address}</p>
              </div>
              {distanceKm !== undefined && (
                <div className="text-right shrink-0">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Est. Proximity</span>
                  <span className="text-amber-ops font-bold">{distanceKm.toFixed(1)} km</span>
                </div>
              )}
            </div>

            {/* Coordinates Row */}
            <div className="pt-2 border-t border-obsidian-850 flex items-center justify-between gap-2">
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">WGS-84 Coordinates</span>
                <span className="text-slate-300 font-bold tracking-wider">{coordString}</span>
              </div>
              <button
                type="button"
                onClick={handleCopy}
                className="px-2.5 py-1 rounded bg-obsidian-800 hover:bg-obsidian-750 text-slate-300 hover:text-white border border-obsidian-700 flex items-center gap-1.5 transition text-[11px]"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-cyan-ops" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* External Navigation Launchers */}
          <div className="space-y-2">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-bold">
              Launch External Navigation:
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {/* Google Maps Link */}
              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-3 rounded-xl bg-cyan-950/60 hover:bg-cyan-950/90 border border-cyan-800 text-cyan-ops flex items-center justify-between transition group shadow"
              >
                <div className="flex items-center gap-2">
                  <Navigation className="w-4 h-4 shrink-0 group-hover:scale-110 transition" />
                  <div className="text-left">
                    <span className="font-bold block text-xs">Google Maps</span>
                    <span className="text-[10px] text-cyan-300/70 block font-sans">Open directions in browser</span>
                  </div>
                </div>
                <ExternalLink className="w-3.5 h-3.5 shrink-0 opacity-70 group-hover:opacity-100" />
              </a>

              {/* Mobile Geo URI Link */}
              <a
                href={geoUri}
                className="p-3 rounded-xl bg-amber-950/60 hover:bg-amber-950/90 border border-amber-800 text-amber-ops flex items-center justify-between transition group shadow"
              >
                <div className="flex items-center gap-2">
                  <Smartphone className="w-4 h-4 shrink-0 group-hover:scale-110 transition" />
                  <div className="text-left">
                    <span className="font-bold block text-xs">Device Maps App</span>
                    <span className="text-[10px] text-amber-300/70 block font-sans">Open native geo: app</span>
                  </div>
                </div>
                <ExternalLink className="w-3.5 h-3.5 shrink-0 opacity-70 group-hover:opacity-100" />
              </a>
            </div>
          </div>

          {/* Explicit Operational Notice */}
          <div className="p-3 bg-obsidian-950 rounded-xl border border-obsidian-800 flex items-start gap-2 text-slate-400 text-[11px] font-sans leading-relaxed">
            <AlertCircle className="w-4 h-4 text-amber-ops shrink-0 mt-0.5" />
            <p>
              <span className="font-semibold text-slate-200">DIRS Navigation Notice:</span> DIRS provides verified destination coordinates and direct external navigation integration. Turn-by-turn routing, road traffic conditions, and GPS positioning are handled via your external mapping provider.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-obsidian-850 border-t border-obsidian-750 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-obsidian-800 hover:bg-obsidian-750 text-slate-200 text-xs font-mono font-bold transition border border-obsidian-700"
          >
            Close Waypoint
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};
