/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 4: Solver Status Banner
 *
 * Displays top-level execution status, usability determination, kernel timing,
 * and cryptographic verification metadata for recovery portfolio optimization results.
 *
 * Strict Guarantees:
 * - hasUsableSchedule(status) returns true exclusively for OPTIMAL and FEASIBLE.
 * - POST_SOLVE_RECONCILIATION_FAILED clearly declares schedule rejected.
 * - UNKNOWN status communicates indeterminate state without fabricated timeout or infeasibility claims.
 */

import React from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  AlertOctagon, 
  HelpCircle, 
  XCircle, 
  ShieldAlert, 
  Clock, 
  Hash, 
  Cpu, 
  Fingerprint,
  Check,
  Ban
} from 'lucide-react';
import { 
  RecoveryOptimizationScenarioResponse, 
  SolverOutcomeStatus 
} from '../../types/recoveryOptimization';

/**
 * Authoritative predicate determining whether an optimization response
 * contains a valid, usable schedule approved for decision support.
 */
export const hasUsableSchedule = (status: SolverOutcomeStatus): boolean => {
  return status === 'OPTIMAL' || status === 'FEASIBLE';
};

interface SolverStatusBannerProps {
  /** Optimization response payload from solver */
  result: RecoveryOptimizationScenarioResponse;
  /** Request correlation ID extracted from HTTP headers */
  correlationId: string | null;
}

export const SolverStatusBanner: React.FC<SolverStatusBannerProps> = ({
  result,
  correlationId,
}) => {
  const isUsable = hasUsableSchedule(result.solver_status);
  const status = result.solver_status;

  // Status configuration mapping
  const statusConfig = (() => {
    switch (status) {
      case 'OPTIMAL':
        return {
          badgeText: 'OPTIMAL',
          badgeClass: 'bg-emerald-950 text-emerald-300 border-emerald-800',
          cardBorder: 'border-emerald-700/80',
          cardBg: 'bg-emerald-950/30',
          icon: CheckCircle2,
          iconColor: 'text-emerald-400',
          title: 'Global Mathematical Optimum Proven',
          description: 'The solver proved mathematical optimality. All Tier-1 mandatory safety constraints and periodic solvency requirements are fully satisfied.',
          usabilityBadge: 'USABLE SCHEDULE AVAILABLE',
          usabilityClass: 'bg-emerald-900/80 text-emerald-200 border-emerald-700',
          usabilityIcon: Check,
        };
      case 'FEASIBLE':
        return {
          badgeText: 'FEASIBLE',
          badgeClass: 'bg-amber-950 text-amber-300 border-amber-800',
          cardBorder: 'border-amber-700/80',
          cardBg: 'bg-amber-950/30',
          icon: AlertTriangle,
          iconColor: 'text-amber-400',
          title: 'Feasible Portfolio Schedule Identified',
          description: 'A valid feasible solution was found within the allotted execution time. The schedule satisfies all constraints; relative optimality gap is reported.',
          usabilityBadge: 'USABLE SCHEDULE AVAILABLE',
          usabilityClass: 'bg-amber-900/80 text-amber-200 border-amber-700',
          usabilityIcon: Check,
        };
      case 'INFEASIBLE':
        return {
          badgeText: 'INFEASIBLE',
          badgeClass: 'bg-red-950 text-red-300 border-red-800',
          cardBorder: 'border-red-700/80',
          cardBg: 'bg-red-950/30',
          icon: AlertOctagon,
          iconColor: 'text-red-400',
          title: 'Proven Mathematical Infeasibility',
          description: 'The solver proved that no project sequencing can simultaneously satisfy all candidate safety deadlines, periodic budgets, and precedence constraints.',
          usabilityBadge: 'NO USABLE SCHEDULE GENERATED',
          usabilityClass: 'bg-red-900/80 text-red-200 border-red-700',
          usabilityIcon: Ban,
        };
      case 'UNKNOWN':
        return {
          badgeText: 'UNKNOWN',
          badgeClass: 'bg-slate-900 text-slate-300 border-slate-700',
          cardBorder: 'border-slate-700/80',
          cardBg: 'bg-slate-900/40',
          icon: HelpCircle,
          iconColor: 'text-slate-400',
          title: 'Indeterminate Solver State (UNKNOWN)',
          description: 'The solver terminated in an indeterminate state without finding an integer solution or establishing infeasibility. No usable schedule was produced.',
          usabilityBadge: 'NO USABLE SCHEDULE AVAILABLE',
          usabilityClass: 'bg-slate-800 text-slate-300 border-slate-700',
          usabilityIcon: Ban,
        };
      case 'MODEL_INVALID':
        return {
          badgeText: 'MODEL_INVALID',
          badgeClass: 'bg-red-950 text-red-300 border-red-800',
          cardBorder: 'border-red-800/80',
          cardBg: 'bg-red-950/30',
          icon: XCircle,
          iconColor: 'text-red-400',
          title: 'Invalid Model Formulation',
          description: 'The mathematical model formulation contained invalid parameters, circular precedence, or contradictory boundary conditions prior to solve.',
          usabilityBadge: 'NO USABLE SCHEDULE GENERATED',
          usabilityClass: 'bg-red-900/80 text-red-200 border-red-700',
          usabilityIcon: Ban,
        };
      case 'POST_SOLVE_RECONCILIATION_FAILED':
        return {
          badgeText: 'RECONCILIATION FAILED',
          badgeClass: 'bg-red-950 text-red-200 border-red-600',
          cardBorder: 'border-red-600',
          cardBg: 'bg-red-950/60',
          icon: ShieldAlert,
          iconColor: 'text-red-400',
          title: 'Post-Solve Safety Reconciliation Failed',
          description: 'CRITICAL: The backend post-solve verification gate rejected the solution due to an integrity constraint violation. The schedule is rejected and must not be used.',
          usabilityBadge: 'SCHEDULE REJECTED — NOT USABLE',
          usabilityClass: 'bg-red-900 text-red-100 border-red-500 font-bold',
          usabilityIcon: Ban,
        };
      default:
        return {
          badgeText: status,
          badgeClass: 'bg-obsidian-800 text-slate-300 border-obsidian-700',
          cardBorder: 'border-obsidian-700',
          cardBg: 'bg-obsidian-900',
          icon: HelpCircle,
          iconColor: 'text-slate-400',
          title: `Solver Status: ${status}`,
          description: 'Solver outcome received.',
          usabilityBadge: 'NO USABLE SCHEDULE',
          usabilityClass: 'bg-obsidian-800 text-slate-300 border-obsidian-700',
          usabilityIcon: Ban,
        };
    }
  })();

  const StatusIcon = statusConfig.icon;
  const UsabilityIcon = statusConfig.usabilityIcon;

  return (
    <div className={`p-4 sm:p-5 rounded-xl border ${statusConfig.cardBorder} ${statusConfig.cardBg} space-y-3.5 font-mono`}>
      {/* Top Bar: Usability Declaration & Status Badge */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-obsidian-900/80 border border-obsidian-750">
            <StatusIcon className={`w-5 h-5 ${statusConfig.iconColor}`} />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded text-xs font-bold border ${statusConfig.badgeClass}`}>
                {statusConfig.badgeText}
              </span>
              <span className={`px-2.5 py-0.5 rounded text-[11px] font-semibold border flex items-center gap-1.5 ${statusConfig.usabilityClass}`}>
                <UsabilityIcon className="w-3.5 h-3.5" />
                {statusConfig.usabilityBadge}
              </span>
            </div>
            <h3 className="text-sm font-bold text-slate-100 mt-1">
              {statusConfig.title}
            </h3>
          </div>
        </div>

        {/* Timing and Correlation ID */}
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400 self-end sm:self-auto">
          <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-obsidian-900/90 border border-obsidian-750">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Solve Time:</span>
            <span className="font-bold text-slate-200">{result.solve_time_seconds.toFixed(2)}s</span>
          </div>
          {correlationId && (
            <div className="flex items-center gap-1 px-2.5 py-1 rounded bg-obsidian-900/90 border border-obsidian-750">
              <Hash className="w-3.5 h-3.5 text-amber-400" />
              <span>CID:</span>
              <span className="font-bold text-slate-200">{correlationId}</span>
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="text-xs text-slate-300 leading-relaxed">
        {statusConfig.description}
      </p>

      {/* Engine & Cryptographic Provenance Bar */}
      <div className="pt-2.5 border-t border-obsidian-750/70 flex flex-col md:flex-row items-start md:items-center justify-between gap-2 text-[10px] text-slate-400">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-cyan-ops" />
            <span>Engine: OR-Tools {result.ortools_version || '9.8'} CP-SAT</span>
          </span>
          <span>•</span>
          <span>Scenario: <strong className="text-slate-300">{result.scenario_name}</strong></span>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[10px] truncate max-w-full">
          <Fingerprint className="w-3 h-3 text-slate-500 shrink-0" />
          <span className="text-slate-500">Input SHA-256:</span>
          <span className="text-slate-400 truncate" title={result.input_fingerprint_sha256}>
            {result.input_fingerprint_sha256 ? `${result.input_fingerprint_sha256.slice(0, 16)}...` : 'N/A'}
          </span>
        </div>
      </div>
    </div>
  );
};
