/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 4: Infeasibility Diagnostics View
 *
 * Renders structured diagnostic conflict findings and assumption-core metadata
 * across the four formal diagnostic tiers.
 *
 * Strict Guarantees:
 * - Diagnostic Tiers: Proven Causes, Necessary-Condition Violations, Solver Hypotheses, Warnings.
 * - Zero fabricated severity fields — tiered strictly by DTO array membership.
 * - Exact DTO fields preserved: category, classification, message, mathematical_condition,
 *   affected_projects, conflicting_periods, details.
 * - Assumption-core minimality and sufficiency metadata accurately represented.
 * - Null diagnostics handled without fabricated reports or false infeasibility claims for UNKNOWN.
 */

import React, { useState } from 'react';
import { 
  AlertOctagon, 
  AlertTriangle, 
  HelpCircle, 
  ShieldAlert, 
  Info, 
  ChevronDown, 
  ChevronRight, 
  Tag, 
  Calendar, 
  Layers, 
  FileCode2,
  CheckCircle2
} from 'lucide-react';
import { 
  InfeasibilityDiagnosticReportDTO, 
  InfeasibilityFindingDTO, 
  SolverOutcomeStatus 
} from '../../types/recoveryOptimization';

interface InfeasibilityDiagnosticsViewProps {
  /** Structured infeasibility diagnostic report from solver */
  diagnostics: InfeasibilityDiagnosticReportDTO | null;
  /** Overall solver outcome status */
  solverStatus: SolverOutcomeStatus;
}

export const InfeasibilityDiagnosticsView: React.FC<InfeasibilityDiagnosticsViewProps> = ({
  diagnostics,
  solverStatus,
}) => {
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});

  const toggleDetails = (key: string) => {
    setExpandedDetails((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // When diagnostics payload is null or absent
  if (!diagnostics) {
    if (solverStatus === 'INFEASIBLE') {
      return (
        <div className="rounded-xl border border-red-800/80 bg-red-950/30 p-5 font-mono text-xs text-red-200 space-y-2">
          <div className="flex items-center gap-2 text-sm font-bold text-red-400">
            <AlertOctagon className="w-5 h-5 text-red-400" />
            <span>Proven Mathematical Infeasibility</span>
          </div>
          <p className="text-xs text-red-300 leading-relaxed">
            The OR-Tools solver proved that no feasible schedule exists meeting all budget, precedence, and safety constraints. No structured diagnostic conflict report was returned by the engine.
          </p>
        </div>
      );
    }

    if (solverStatus === 'UNKNOWN') {
      return (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5 font-mono text-xs text-slate-300 space-y-2">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
            <HelpCircle className="w-5 h-5 text-slate-400" />
            <span>Indeterminate Solver State (UNKNOWN)</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            The solver terminated without establishing feasibility or proving infeasibility. No diagnostic conflict report is available for this indeterminate run.
          </p>
        </div>
      );
    }

    if (solverStatus === 'MODEL_INVALID') {
      return (
        <div className="rounded-xl border border-red-800 bg-red-950/30 p-5 font-mono text-xs text-red-200 space-y-2">
          <div className="flex items-center gap-2 text-sm font-bold text-red-400">
            <AlertOctagon className="w-5 h-5 text-red-400" />
            <span>Model Formulation Invalid</span>
          </div>
          <p className="text-xs text-red-300 leading-relaxed">
            The scenario model specification contained invalid parameters or inconsistent boundary conditions prior to solver invocation.
          </p>
        </div>
      );
    }

    if (solverStatus === 'POST_SOLVE_RECONCILIATION_FAILED') {
      return (
        <div className="rounded-xl border border-red-600 bg-red-950/60 p-5 font-mono text-xs text-red-100 space-y-2">
          <div className="flex items-center gap-2 text-sm font-bold text-red-300">
            <ShieldAlert className="w-5 h-5 text-red-400" />
            <span>Post-Solve Safety Reconciliation Failed</span>
          </div>
          <p className="text-xs text-red-200 leading-relaxed">
            CRITICAL: The backend safety verification gate rejected the solution due to an integrity constraint violation. The schedule must not be utilized.
          </p>
        </div>
      );
    }

    // Default or optimal run without diagnostics
    return null;
  }

  // Diagnostic Tiers from DTO
  const tiers = [
    {
      title: 'Tier 1: Proven Causes',
      description: 'Mathematically closed contradictions where no assignment exists.',
      findings: diagnostics.proven_causes || [],
      badgeColor: 'bg-red-950 text-red-300 border-red-800',
      cardBorder: 'border-red-800/80',
      icon: AlertOctagon,
      iconColor: 'text-red-400',
    },
    {
      title: 'Tier 2: Necessary-Condition Violations',
      description: 'Aggregate structural violations proven without full branch-and-bound search.',
      findings: diagnostics.necessary_condition_violations || [],
      badgeColor: 'bg-orange-950 text-orange-300 border-orange-800',
      cardBorder: 'border-orange-800/80',
      icon: AlertTriangle,
      iconColor: 'text-orange-400',
    },
    {
      title: 'Tier 3: Solver Hypotheses',
      description: 'Conflict sets identified through relaxation heuristics and assumption analysis.',
      findings: diagnostics.solver_hypotheses || [],
      badgeColor: 'bg-cyan-950 text-cyan-300 border-cyan-800',
      cardBorder: 'border-cyan-800/80',
      icon: HelpCircle,
      iconColor: 'text-cyan-400',
    },
    {
      title: 'Tier 4: Advisory Warnings',
      description: 'Tight constraint thresholds, boundary conditions, or execution notices.',
      findings: diagnostics.warnings || [],
      badgeColor: 'bg-slate-850 text-slate-300 border-slate-700',
      cardBorder: 'border-slate-700/80',
      icon: Info,
      iconColor: 'text-slate-400',
    },
  ];

  const totalFindings = tiers.reduce((acc, t) => acc + t.findings.length, 0);

  return (
    <div className="rounded-xl border border-obsidian-750 bg-obsidian-900 overflow-hidden font-mono text-xs shadow-xl space-y-0">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-obsidian-750 bg-obsidian-850 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-red-950/80 border border-red-800 text-red-400">
            <AlertOctagon className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Infeasibility Diagnostics & Assumption Core
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] bg-red-950 text-red-300 border border-red-800/80 font-semibold">
                {totalFindings} Diagnostic Finding{totalFindings !== 1 ? 's' : ''}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Structured mathematical conflict analysis across four authoritative diagnostic tiers
            </p>
          </div>
        </div>

        {/* Assumption Core Metadata Badges */}
        <div className="flex flex-wrap items-center gap-2 text-[10px]">
          <div className="px-2.5 py-1 rounded bg-obsidian-800 border border-obsidian-700 flex items-center gap-1.5">
            <span className="text-slate-400">Proven Infeasibility:</span>
            <strong className={diagnostics.has_proven_infeasibility ? 'text-red-400' : 'text-slate-300'}>
              {diagnostics.has_proven_infeasibility ? 'TRUE' : 'FALSE'}
            </strong>
          </div>

          <div className="px-2.5 py-1 rounded bg-obsidian-800 border border-obsidian-700 flex items-center gap-1.5">
            <span className="text-slate-400">Core Minimal (IIS):</span>
            <strong className={diagnostics.is_assumption_core_minimal ? 'text-emerald-400' : 'text-slate-400'}>
              {diagnostics.is_assumption_core_minimal ? 'YES' : 'NO'}
            </strong>
          </div>

          <div className="px-2.5 py-1 rounded bg-obsidian-800 border border-obsidian-700 flex items-center gap-1.5">
            <span className="text-slate-400">Core Sufficient:</span>
            <strong className={diagnostics.is_assumption_core_sufficient ? 'text-emerald-400' : 'text-amber-400'}>
              {diagnostics.is_assumption_core_sufficient ? 'YES' : 'NO'}
            </strong>
          </div>
        </div>
      </div>

      {/* Diagnostic Tiers Content */}
      <div className="p-4 sm:p-5 space-y-5">
        {tiers.map((tier, tierIdx) => {
          if (tier.findings.length === 0) return null;
          const TierIcon = tier.icon;

          return (
            <div key={tierIdx} className="space-y-3">
              <div className="flex items-center gap-2 pb-1.5 border-b border-obsidian-800">
                <TierIcon className={`w-4 h-4 ${tier.iconColor}`} />
                <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  {tier.title} ({tier.findings.length})
                </h4>
                <span className="text-[10px] text-slate-500 font-normal">
                  — {tier.description}
                </span>
              </div>

              <div className="space-y-3">
                {tier.findings.map((finding: InfeasibilityFindingDTO, findingIdx: number) => {
                  const compositeKey = `${tierIdx}-${finding.category}-${findingIdx}`;
                  const isExpanded = !!expandedDetails[compositeKey];

                  return (
                    <div 
                      key={compositeKey}
                      className={`p-3.5 rounded-lg border bg-obsidian-850/70 ${tier.cardBorder} space-y-2.5`}
                    >
                      {/* Finding Category & Classification Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${tier.badgeColor}`}>
                            {finding.category}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] bg-obsidian-800 text-slate-300 border border-obsidian-700">
                            {finding.classification}
                          </span>
                        </div>
                      </div>

                      {/* Diagnostic Statement */}
                      <p className="text-xs text-slate-200 leading-relaxed font-sans">
                        {finding.message}
                      </p>

                      {/* Mathematical Condition */}
                      {finding.mathematical_condition && (
                        <div className="p-2 rounded bg-obsidian-950 border border-obsidian-800 text-[11px] font-mono text-amber-300 flex items-start gap-2">
                          <FileCode2 className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                          <span className="break-all">{finding.mathematical_condition}</span>
                        </div>
                      )}

                      {/* Affected Projects & Conflicting Periods Tags */}
                      <div className="flex flex-wrap items-center gap-3 pt-1 text-[10px] text-slate-400">
                        {finding.affected_projects && finding.affected_projects.length > 0 && (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <Tag className="w-3 h-3 text-cyan-400 shrink-0" />
                            <span>Affected:</span>
                            {finding.affected_projects.map((pid) => (
                              <span 
                                key={pid} 
                                className="px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800 font-bold"
                              >
                                {pid}
                              </span>
                            ))}
                          </div>
                        )}

                        {finding.conflicting_periods && finding.conflicting_periods.length > 0 && (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <Calendar className="w-3 h-3 text-amber-400 shrink-0" />
                            <span>Periods:</span>
                            {finding.conflicting_periods.map((periodNum) => (
                              <span 
                                key={periodNum} 
                                className="px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800 font-bold"
                              >
                                P{periodNum}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Expandable Details Block */}
                      {finding.details && Object.keys(finding.details).length > 0 && (
                        <div className="pt-1.5 border-t border-obsidian-800">
                          <button
                            type="button"
                            onClick={() => toggleDetails(compositeKey)}
                            className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200 transition"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-3 h-3" />
                            ) : (
                              <ChevronRight className="w-3 h-3" />
                            )}
                            <span>{isExpanded ? 'Hide Parameter Details' : 'View Parameter Details'}</span>
                          </button>

                          {isExpanded && (
                            <pre className="mt-2 p-2.5 rounded bg-obsidian-950 border border-obsidian-800 text-[10px] text-slate-300 overflow-x-auto">
                              {JSON.stringify(finding.details, null, 2)}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
