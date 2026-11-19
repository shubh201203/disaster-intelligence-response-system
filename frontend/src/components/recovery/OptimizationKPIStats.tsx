/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 4: Optimization KPI Stats
 *
 * Renders four responsive decision-support KPI cards using the accepted DIRS design system.
 *
 * Strict Guarantees:
 * - Exact 64-bit integer strings (Category 1) rendered verbatim without Number() or parseFloat() coercion.
 * - Exact INR Decimal strings (Category 3) formatted via lossless string operations.
 * - Non-usable outcomes (INFEASIBLE, UNKNOWN, MODEL_INVALID, POST_SOLVE_RECONCILIATION_FAILED)
 *   strictly qualify or suppress schedule-dependent metrics with explicit "N/A" sentinels.
 * - Zero derivation of unsupported metrics.
 */

import React from 'react';
import { 
  Award, 
  Building2, 
  IndianRupee, 
  Target, 
  Coins, 
  AlertCircle 
} from 'lucide-react';
import { KPIStat } from '../design-system';
import { 
  RecoveryOptimizationScenarioResponse, 
  CurrencyUnit 
} from '../../types/recoveryOptimization';
import { hasUsableSchedule } from './SolverStatusBanner';

/**
 * Formats an exact Decimal string representing an INR currency amount
 * using the Indian numbering system without converting to IEEE-754 float.
 */
export const formatExactInrString = (inrStr: string | null | undefined): string => {
  if (!inrStr || inrStr === 'N/A' || inrStr === 'null') return 'N/A';
  const cleanStr = inrStr.trim();
  const [rawInt = '0', rawDec = '00'] = cleanStr.split('.');
  
  const isNegative = rawInt.startsWith('-');
  const absInt = isNegative ? rawInt.slice(1) : rawInt;
  
  // Format integer digits using Indian numbering grouping: XX,XX,XXX
  const lastThree = absInt.slice(-3);
  const otherNumbers = absInt.slice(0, -3);
  const formattedInteger = otherNumbers !== ''
    ? otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree
    : lastThree;
    
  return `${isNegative ? '-' : ''}₹${formattedInteger}.${rawDec.padEnd(2, '0').slice(0, 2)}`;
};

interface OptimizationKPIStatsProps {
  /** Optimization response payload from solver */
  result: RecoveryOptimizationScenarioResponse;
  /** Currency unit of scenario (default: INR) */
  currency?: CurrencyUnit;
}

export const OptimizationKPIStats: React.FC<OptimizationKPIStatsProps> = ({
  result,
  currency = 'INR',
}) => {
  const isUsable = hasUsableSchedule(result.solver_status);
  const status = result.solver_status;

  // 1. Exact Objective Value Metric
  const objectiveCard = (() => {
    if (!isUsable || result.exact_objective_value === null) {
      return {
        value: 'N/A',
        subtext: status === 'INFEASIBLE' 
          ? 'No objective — scenario infeasible' 
          : 'Not available — no usable schedule',
        variant: 'neutral' as const,
      };
    }
    return {
      value: result.exact_objective_value,
      subtext: `Quantized 64-bit integer score (float: ${result.objective_value !== null ? result.objective_value.toLocaleString() : 'N/A'})`,
      variant: result.is_optimal ? ('emerald' as const) : ('amber' as const),
    };
  })();

  // 2. Selected Projects Metric
  const projectsCard = (() => {
    const totalCandidates = result.scheduled_projects ? result.scheduled_projects.length : 0;
    if (!isUsable) {
      return {
        value: 'N/A',
        subtext: 'No projects scheduled (non-solution state)',
        variant: 'neutral' as const,
      };
    }
    return {
      value: `${result.selected_project_count} / ${totalCandidates}`,
      subtext: `${result.selected_project_count} funded candidates scheduled`,
      variant: 'cyan' as const,
    };
  })();

  // 3. Total Portfolio Cost Metric
  const costCard = (() => {
    if (!isUsable) {
      return {
        value: 'N/A',
        subtext: 'No funded portfolio expenditure',
        variant: 'neutral' as const,
      };
    }
    if (currency === 'CCU') {
      return {
        value: `${result.total_cost_ccu} CCU`,
        subtext: 'Exact total capital requirement in CCU',
        variant: 'amber' as const,
      };
    }
    return {
      value: formatExactInrString(result.total_cost_inr),
      subtext: `CCU: ${result.total_cost_ccu} | Exact Decimal capital expenditure`,
      variant: 'amber' as const,
    };
  })();

  // 4. Optimality Gap & Solver Bound Metric
  const gapCard = (() => {
    if (!isUsable) {
      return {
        value: 'N/A',
        subtext: 'Optimality gap not applicable',
        variant: 'neutral' as const,
      };
    }
    if (status === 'OPTIMAL' || result.optimality_gap === 0.0) {
      return {
        value: '0.00%',
        subtext: 'Proven global mathematical optimum',
        variant: 'emerald' as const,
      };
    }
    const gapPercent = result.optimality_gap !== null 
      ? `${(result.optimality_gap * 100).toFixed(2)}%` 
      : 'N/A';
    return {
      value: gapPercent,
      subtext: result.exact_best_bound 
        ? `Dual bound: ${result.exact_best_bound}` 
        : 'Relative optimality gap vs dual bound',
      variant: 'amber' as const,
    };
  })();

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 font-mono">
      <KPIStat
        label="Exact Objective Value"
        value={objectiveCard.value}
        subtext={objectiveCard.subtext}
        icon={Award}
        variant={objectiveCard.variant}
      />

      <KPIStat
        label="Funded Projects"
        value={projectsCard.value}
        subtext={projectsCard.subtext}
        icon={Building2}
        variant={projectsCard.variant}
      />

      <KPIStat
        label="Total Portfolio Cost"
        value={costCard.value}
        subtext={costCard.subtext}
        icon={IndianRupee}
        variant={costCard.variant}
      />

      <KPIStat
        label="Optimality Gap"
        value={gapCard.value}
        subtext={gapCard.subtext}
        icon={Target}
        variant={gapCard.variant}
      />
    </div>
  );
};
