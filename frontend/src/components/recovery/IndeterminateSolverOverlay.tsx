/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 3: Indeterminate Solver Overlay
 *
 * Fullscreen indeterminate execution modal rendered while synchronous optimization evaluation
 * is actively running on the backend CP-SAT solver kernel.
 *
 * Strict Stopwatch & State Invariants:
 * - Uses performance.now() timestamp-based elapsed time calculation.
 * - Starts timing when mutation initiates; stops immediately on success or error.
 * - Interval is cleaned up deterministically upon resolution or unmount.
 * - Indeterminate spinner with zero fabricated progress percentages or countdown timers.
 * - Clear warning against page refresh or navigation during synchronous solver evaluation.
 */

import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Cpu, AlertTriangle, ShieldCheck, Loader2 } from 'lucide-react';

interface IndeterminateSolverOverlayProps {
  /** True while the synchronous backend solver execution is actively pending */
  isPending: boolean;
}

export const IndeterminateSolverOverlay: React.FC<IndeterminateSolverOverlayProps> = ({
  isPending,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isPending) {
      startTimeRef.current = null;
      setElapsedSeconds(0);
      return;
    }

    // Capture starting wall-clock timestamp with sub-millisecond precision
    startTimeRef.current = performance.now();
    setElapsedSeconds(0);

    const intervalId = setInterval(() => {
      if (startTimeRef.current !== null) {
        const now = performance.now();
        setElapsedSeconds((now - startTimeRef.current) / 1000);
      }
    }, 100);

    return () => {
      clearInterval(intervalId);
    };
  }, [isPending]);

  if (!isPending) return null;

  const content = (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-obsidian-950/85 backdrop-blur-md animate-in fade-in duration-200 select-none"
      role="dialog"
      aria-modal="true"
      aria-label="Optimization Solver Execution"
    >
      <div className="w-full max-w-lg bg-obsidian-900 border border-obsidian-700/80 rounded-2xl shadow-2xl p-6 sm:p-8 space-y-6 font-mono text-center">
        {/* Animated Solver Kernel Visual */}
        <div className="relative flex items-center justify-center mx-auto w-20 h-20">
          <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20 border-t-cyan-400 animate-spin" />
          <div className="absolute inset-2 rounded-full border-2 border-amber-500/20 border-b-amber-400 animate-spin [animation-duration:3s]" />
          <div className="p-4 rounded-full bg-obsidian-950 border border-obsidian-800 text-cyan-ops shadow-inner">
            <Cpu className="w-8 h-8 animate-pulse text-cyan-400" />
          </div>
        </div>

        {/* Title & Telemetry Status */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-[11px] font-bold uppercase tracking-wider">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>SOLVER KERNEL ACTIVE</span>
          </div>

          <h2 className="text-sm font-bold text-slate-100 uppercase tracking-widest pt-1">
            Synchronous Mathematical Optimization
          </h2>

          <p className="text-xs text-slate-400 leading-relaxed max-w-sm mx-auto">
            Disaster recovery portfolio MILP/CP-SAT kernel is evaluating branch-and-bound project sequences.
          </p>
        </div>

        {/* Live Elapsed Stopwatch Panel */}
        <div className="p-4 rounded-xl bg-obsidian-950 border border-obsidian-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Elapsed Solver Time:</span>
            <span className="text-base font-bold text-amber-ops font-mono tabular-nums">
              {elapsedSeconds.toFixed(1)}s
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-obsidian-850">
            <span>Server Execution Cap:</span>
            <span className="font-semibold text-slate-400">120.0s</span>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span>Frontend Client Timeout:</span>
            <span className="font-semibold text-slate-400">130.0s</span>
          </div>
        </div>

        {/* Indeterminate Execution Guarantee Notice */}
        <div className="text-[11px] text-slate-400 bg-obsidian-850/60 p-3 rounded-lg border border-obsidian-800 space-y-1 text-left">
          <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-ops shrink-0" />
            <span>Indeterminate synchronous evaluation</span>
          </div>
          <p className="text-[10px] text-slate-500 leading-normal">
            No fabricated progress estimate or countdown is displayed. The CP-SAT solver explores combinatorial search trees synchronously on the DIRS computational backend.
          </p>
        </div>

        {/* Anti-Navigation Warning */}
        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-300 text-[10px] text-left">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            Please do not refresh, close, or navigate away from this page. Awaiting synchronous solver outcome.
          </span>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
};
