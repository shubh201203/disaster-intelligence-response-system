/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 3: Solver Control Bar
 *
 * User execution control for synchronous recovery portfolio optimization.
 * Requires human-in-the-loop confirmation before dispatching the evaluation request.
 * Displays live execution states, normalized error details, and safe retry controls.
 *
 * Strict Guarantees:
 * - Decision Support Only notice explicitly communicated.
 * - Zero automatic schedule application or persistence.
 * - Disabled when configuration constraints are violated or execution is pending.
 */

import React, { useState } from 'react';
import { 
  Cpu, 
  Play, 
  RotateCcw, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  ShieldAlert, 
  Info,
  AlertCircle,
  Hash
} from 'lucide-react';
import { ConfirmDialog } from '../design-system';
import { 
  EvaluatedScenarioResult, 
  OptimizationApiError 
} from '../../types/recoveryOptimization';

interface SolverControlBarProps {
  /** Whether the current scenario configuration passes all mathematical constraints */
  isValid: boolean;
  /** True while the synchronous backend solver execution is in progress */
  isPending: boolean;
  /** True if the last execution completed successfully */
  isSuccess: boolean;
  /** True if the last execution failed */
  isError: boolean;
  /** Result payload from the successful API execution */
  result: EvaluatedScenarioResult | null;
  /** Normalized error from the failed API execution */
  error: OptimizationApiError | null;
  /** Dispatches confirmed optimization request to API */
  onRunOptimization: () => void;
  /** Resets execution state to idle */
  onReset: () => void;
}

export const SolverControlBar: React.FC<SolverControlBarProps> = ({
  isValid,
  isPending,
  isSuccess,
  isError,
  result,
  error,
  onRunOptimization,
  onReset,
}) => {
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  const handleOpenConfirm = () => {
    if (!isValid || isPending) return;
    setIsConfirmOpen(true);
  };

  const handleConfirm = () => {
    setIsConfirmOpen(false);
    onRunOptimization();
  };

  const handleCancel = () => {
    setIsConfirmOpen(false);
  };

  return (
    <>
      <div className="p-5 rounded-xl bg-obsidian-900 border border-obsidian-750 space-y-4 font-mono">
        {/* Main Header & Execution Controls */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg border transition ${
              isPending
                ? 'bg-amber-950/80 border-amber-800 text-amber-400 animate-pulse'
                : isSuccess
                ? 'bg-emerald-950/80 border-emerald-800 text-emerald-400'
                : isError
                ? 'bg-red-950/80 border-red-800 text-red-400'
                : 'bg-obsidian-800 border-obsidian-700 text-slate-300'
            }`}>
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Synchronous Solver Execution Engine
                </h3>
                <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60 uppercase font-semibold">
                  OR-Tools CP-SAT
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Evaluates optimal project sequencing and financial solvency over discrete planning horizon
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2.5">
            {isSuccess && (
              <button
                type="button"
                onClick={onReset}
                className="px-3 py-2 bg-obsidian-850 hover:bg-obsidian-800 text-slate-400 hover:text-slate-200 border border-obsidian-700 rounded-lg text-xs font-mono transition flex items-center gap-1.5"
                title="Clear current evaluation result"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Clear Result
              </button>
            )}

            {isError && (
              <button
                type="button"
                onClick={onReset}
                className="px-3 py-2 bg-obsidian-850 hover:bg-obsidian-800 text-slate-400 hover:text-slate-200 border border-obsidian-700 rounded-lg text-xs font-mono transition flex items-center gap-1.5"
                title="Dismiss error and return to configuration"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Dismiss Error
              </button>
            )}

            <button
              type="button"
              onClick={handleOpenConfirm}
              disabled={!isValid || isPending}
              className={`px-5 py-2.5 rounded-lg text-xs font-bold transition flex items-center gap-2 shadow-lg ${
                !isValid || isPending
                  ? 'bg-obsidian-800 text-slate-500 border border-obsidian-750 cursor-not-allowed opacity-60 shadow-none'
                  : isError
                  ? 'bg-amber-600 hover:bg-amber-500 text-obsidian-950 border border-amber-500'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-obsidian-950 border border-emerald-500'
              }`}
              title={
                !isValid
                  ? 'Resolve scenario configuration issues before executing solver'
                  : isPending
                  ? 'Solver execution is in progress'
                  : 'Click to confirm and run mathematical optimization'
              }
            >
              {isPending ? (
                <>
                  <Clock className="w-4 h-4 animate-spin text-obsidian-950" />
                  <span>Solver Kernel Executing...</span>
                </>
              ) : isError ? (
                <>
                  <RotateCcw className="w-4 h-4 text-obsidian-950" />
                  <span>Retry Optimization Evaluation</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current text-obsidian-950" />
                  <span>Run Optimization Evaluation</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Minimal Execution Success Acknowledgement (Stage 3 Scope) */}
        {isSuccess && result && (
          <div className="p-3.5 rounded-lg bg-emerald-950/30 border border-emerald-800/80 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs text-emerald-300 font-semibold">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>Synchronous Optimization Evaluation Succeeded</span>
              </div>
              <div className="flex items-center gap-2 text-[10px]">
                <span className="px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-200 border border-emerald-700/60 font-bold uppercase">
                  Status: {result.data.solver_status}
                </span>
                {result.correlationId && (
                  <span className="px-2 py-0.5 rounded bg-obsidian-900 text-slate-300 border border-obsidian-700 flex items-center gap-1 font-mono">
                    <Hash className="w-3 h-3 text-emerald-400" />
                    CID: {result.correlationId}
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] pt-1 border-t border-emerald-800/40 text-slate-300">
              <div>
                <span className="text-slate-500 text-[10px] block">Solver Time:</span>
                <span className="font-bold text-emerald-300">{result.data.solve_time_seconds.toFixed(2)}s</span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">Scheduled Projects:</span>
                <span className="font-bold text-emerald-300">{result.data.scheduled_projects.length}</span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">Exact Objective:</span>
                <span className="font-bold text-emerald-300 font-mono">{result.data.exact_objective_value ?? 'N/A'}</span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">Optimality Gap:</span>
                <span className="font-bold text-emerald-300">
                  {result.data.optimality_gap !== null && result.data.optimality_gap !== undefined
                    ? `${(result.data.optimality_gap * 100).toFixed(2)}%`
                    : '0.00%'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Normalized Error Display */}
        {isError && error && (
          <div className="p-3.5 rounded-lg bg-red-950/30 border border-red-800/80 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs text-red-300 font-semibold">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span>Solver Evaluation Failed ({error.detail.error_type})</span>
              </div>
              <div className="flex items-center gap-2 text-[10px]">
                <span className="px-2 py-0.5 rounded bg-red-900/60 text-red-200 border border-red-700/60 font-bold">
                  HTTP {error.status}
                </span>
                {error.correlationId && (
                  <span className="px-2 py-0.5 rounded bg-obsidian-900 text-slate-300 border border-obsidian-700 flex items-center gap-1 font-mono">
                    <Hash className="w-3 h-3 text-red-400" />
                    CID: {error.correlationId}
                  </span>
                )}
              </div>
            </div>

            <p className="text-xs text-red-200 leading-relaxed">
              {error.detail.message}
            </p>

            {/* Validation Failures Detail if Present (422) */}
            {error.detail.validation_failures && error.detail.validation_failures.length > 0 && (
              <div className="pt-2 border-t border-red-800/50 space-y-1">
                <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider block">
                  Validation Failures ({error.detail.validation_failures.length}):
                </span>
                <ul className="text-[11px] text-red-300 list-disc list-inside space-y-0.5">
                  {error.detail.validation_failures.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Decision Support & Architecture Notice */}
        <div className="pt-2 border-t border-obsidian-800 text-[10px] text-slate-500 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-cyan-ops shrink-0" />
            <span>
              Decision Support Only — synchronous evaluation calculates mathematical recommendations and does not persist schedules.
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span>Execution Cap: 120s</span>
            <span>•</span>
            <span>Client Timeout: 130s</span>
          </div>
        </div>
      </div>

      {/* Human-In-The-Loop Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isConfirmOpen}
        title="Confirm Optimization Evaluation"
        message="You are about to initiate synchronous mathematical recovery portfolio optimization on the backend cluster. This process executes an OR-Tools CP-SAT MILP solver kernel with an execution cap of 120 seconds.

Notice: This is decision support only and does not automatically commit or apply the resulting schedule to live incident response data."
        confirmLabel="Execute Optimization"
        cancelLabel="Cancel"
        variant="primary"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        isLoading={isPending}
      />
    </>
  );
};
