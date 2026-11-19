import React from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle, ShieldCheck, X } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'primary';
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm Action',
  cancelLabel = 'Cancel',
  variant = 'primary',
  onConfirm,
  onCancel,
  isLoading = false
}) => {
  if (!isOpen) return null;

  const variantBtn = {
    danger: 'bg-red-600 hover:bg-red-500 text-white',
    warning: 'bg-amber-600 hover:bg-amber-500 text-white',
    primary: 'bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-semibold',
  }[variant];

  const dialogContent = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-md bg-obsidian-850 border border-obsidian-700 rounded-xl shadow-2xl overflow-hidden p-6 space-y-4"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg border ${
              variant === 'danger' 
                ? 'bg-red-950/80 border-red-800 text-red-400' 
                : 'bg-amber-950/80 border-amber-800 text-amber-400'
            }`}>
              {variant === 'danger' ? <AlertTriangle className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-100">
                {title}
              </h3>
              <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mt-0.5">
                Human-In-The-Loop Authority Confirmation
              </p>
            </div>
          </div>
          <button 
            onClick={onCancel}
            disabled={isLoading}
            className="text-slate-400 hover:text-slate-200 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300 font-sans leading-relaxed bg-obsidian-900/60 p-3 rounded-lg border border-obsidian-750">
          {message}
        </p>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-3.5 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-obsidian-800 rounded-lg border border-obsidian-700 transition"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 text-xs font-mono rounded-lg transition flex items-center gap-2 ${variantBtn} disabled:opacity-50`}
          >
            {isLoading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );

  return typeof document !== 'undefined'
    ? createPortal(dialogContent, document.body)
    : dialogContent;
};
