import React, { useState, useMemo } from 'react';
import { 
  Cpu, 
  Layers, 
  Sliders, 
  Building2, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  RotateCcw, 
  Lock,
  Sparkles,
  ShieldCheck,
  Info
} from 'lucide-react';
import { PageHeader, StatusBadge, OperationalCard } from '../../components/design-system';
import { ScenarioParametersCard } from '../../components/recovery/ScenarioParametersCard';
import { PeriodicBudgetsEditor } from '../../components/recovery/PeriodicBudgetsEditor';
import { CandidateProjectsGrid } from '../../components/recovery/CandidateProjectsGrid';
import { SolverControlBar } from '../../components/recovery/SolverControlBar';
import { IndeterminateSolverOverlay } from '../../components/recovery/IndeterminateSolverOverlay';
import { SolverStatusBanner, hasUsableSchedule } from '../../components/recovery/SolverStatusBanner';
import { OptimizationKPIStats } from '../../components/recovery/OptimizationKPIStats';
import { ProjectScheduleTimeline } from '../../components/recovery/ProjectScheduleTimeline';
import { FinancialSolvencyMatrix } from '../../components/recovery/FinancialSolvencyMatrix';
import { InfeasibilityDiagnosticsView } from '../../components/recovery/InfeasibilityDiagnosticsView';
import { useRecoveryOptimization } from '../../hooks/useRecoveryOptimization';
import { RecoveryOptimizationScenarioRequest, ProjectOptimizationCandidateDTO } from '../../types/recoveryOptimization';
import { 
  minimalValidScenarioRequestFixture, 
  tier1MandatoryScenarioRequestFixture 
} from '../../fixtures/recoveryOptimizationFixtures';

// Default empty custom scenario generator
const createDefaultCustomScenario = (): RecoveryOptimizationScenarioRequest => ({
  scenario_name: 'Custom Recovery Portfolio Scenario',
  planning_horizon_periods: 12,
  period_length_days: 30.0,
  initial_cash: '10000000.00',
  cash_currency: 'INR',
  periodic_budgets: {
    1: '5000000.00',
    2: '5000000.00',
    3: '5000000.00',
    4: '5000000.00',
  },
  budget_currency: 'INR',
  candidates: [
    {
      project_id: 'P-001',
      project_code: 'INFRA-REPAIR-01',
      district_id: 'DIST-CENTRAL',
      estimated_cost: '4500000.00',
      duration_periods: 2,
      cost_currency: 'INR',
      release_period: 1,
      deadline_period: 6,
      is_tier1_mandatory: false,
      raw_mcpi_score: 0.82,
    },
  ],
  deterministic_seed: 42,
  num_workers: 1,
  max_solve_time_seconds: 30.0,
});

export const RecoveryOptimizationView: React.FC = () => {
  // In-memory scenario state (zero localStorage/sessionStorage persistence)
  const [scenario, setScenario] = useState<RecoveryOptimizationScenarioRequest>(() =>
    JSON.parse(JSON.stringify(minimalValidScenarioRequestFixture))
  );

  const [activeTemplateName, setActiveTemplateName] = useState<string>('Minimal Valid Recovery Scenario');
  const [activeTab, setActiveTab] = useState<'params' | 'budgets' | 'candidates'>('params');

  // Synchronous solver evaluation mutation hook
  const {
    evaluateScenario,
    result,
    error,
    isPending,
    isSuccess,
    isError,
    reset,
  } = useRecoveryOptimization();

  // Check if any candidate is Tier-1 mandatory
  const hasTier1Candidates = useMemo(
    () => scenario.candidates.some((c) => c.is_tier1_mandatory),
    [scenario.candidates]
  );

  // Template loaders with deep copy (guarded against concurrent execution)
  const handleLoadMinimalTemplate = () => {
    if (isPending) return;
    reset();
    setScenario(JSON.parse(JSON.stringify(minimalValidScenarioRequestFixture)));
    setActiveTemplateName('Minimal Valid Recovery Scenario');
  };

  const handleLoadTier1Template = () => {
    if (isPending) return;
    reset();
    setScenario(JSON.parse(JSON.stringify(tier1MandatoryScenarioRequestFixture)));
    setActiveTemplateName('Tier-1 Mandatory Safety Scenario');
  };

  const handleLoadStandard5ProjectTemplate = () => {
    if (isPending) return;
    reset();
    setScenario({
      scenario_name: 'Controlled 5-Project Benchmark Scenario (₹10 Cr / 6 Periods)',
      planning_horizon_periods: 6,
      period_length_days: 30.0,
      initial_cash: '20000000.00',
      cash_currency: 'INR',
      periodic_budgets: {
        1: '20000000.00',
        2: '20000000.00',
        3: '20000000.00',
        4: '15000000.00',
        5: '15000000.00',
        6: '10000000.00',
      },
      budget_currency: 'INR',
      allow_uniform_weight_fallback: true,
      candidates: [
        {
          project_id: 'PRJ-A-ROAD',
          project_code: 'ROAD-CLEAR-01',
          district_id: 'DIST-CENTRAL',
          estimated_cost: '15000000.00',
          duration_periods: 1,
          cost_currency: 'INR',
          release_period: 1,
          deadline_period: 3,
          is_tier1_mandatory: true,
          raw_mcpi_score: 0.90,
          expenditure_weights: [1.0],
          eligible_funds: ['FUND-STATE-SDRF']
        },
        {
          project_id: 'PRJ-B-ELEC',
          project_code: 'GRID-SUBSTATION-02',
          district_id: 'DIST-CENTRAL',
          estimated_cost: '20000000.00',
          duration_periods: 1,
          cost_currency: 'INR',
          release_period: 1,
          deadline_period: 4,
          is_tier1_mandatory: true,
          raw_mcpi_score: 0.85,
          expenditure_weights: [1.0],
          eligible_funds: ['FUND-STATE-SDRF']
        },
        {
          project_id: 'PRJ-C-WATER',
          project_code: 'WATER-TRUNK-03',
          district_id: 'DIST-SOUTH',
          estimated_cost: '15000000.00',
          duration_periods: 1,
          cost_currency: 'INR',
          release_period: 1,
          deadline_period: 5,
          is_tier1_mandatory: false,
          raw_mcpi_score: 0.80,
          expenditure_weights: [1.0],
          eligible_funds: ['FUND-STATE-SDRF']
        },
        {
          project_id: 'PRJ-D-HOSP',
          project_code: 'CLINIC-REOPEN-04',
          district_id: 'DIST-CENTRAL',
          estimated_cost: '10000000.00',
          duration_periods: 1,
          cost_currency: 'INR',
          release_period: 2,
          deadline_period: 5,
          is_tier1_mandatory: true,
          raw_mcpi_score: 0.95,
          expenditure_weights: [1.0],
          eligible_funds: ['FUND-STATE-SDRF']
        },
        {
          project_id: 'PRJ-E-TRANS',
          project_code: 'BUS-TRANSIT-05',
          district_id: 'DIST-SOUTH',
          estimated_cost: '10000000.00',
          duration_periods: 1,
          cost_currency: 'INR',
          release_period: 2,
          deadline_period: 6,
          is_tier1_mandatory: false,
          raw_mcpi_score: 0.75,
          expenditure_weights: [1.0],
          eligible_funds: ['FUND-STATE-SDRF']
        },
      ],
      funding_sources: [
        {
          fund_id: 'FUND-STATE-SDRF',
          capacity: '100000000.00',
          currency: 'INR'
        }
      ],
      max_safety_start_period: 3,
      resource_capacities: {},
      dependencies: [
        { predecessor_id: 'PRJ-A-ROAD', successor_id: 'PRJ-B-ELEC', lag_periods: 0 },
        { predecessor_id: 'PRJ-A-ROAD', successor_id: 'PRJ-C-WATER', lag_periods: 0 },
        { predecessor_id: 'PRJ-B-ELEC', successor_id: 'PRJ-D-HOSP', lag_periods: 0 },
        { predecessor_id: 'PRJ-C-WATER', successor_id: 'PRJ-D-HOSP', lag_periods: 0 },
        { predecessor_id: 'PRJ-B-ELEC', successor_id: 'PRJ-E-TRANS', lag_periods: 0 },
      ]
    });
    setActiveTemplateName('Controlled 5-Project Benchmark Scenario');
  };

  const handleResetToCustom = () => {
    if (isPending) return;
    reset();
    setScenario(createDefaultCustomScenario());
    setActiveTemplateName('Custom Scenario');
  };

  // State updates (disabled while evaluation is in progress)
  const handleUpdateScenarioParams = (updated: Partial<RecoveryOptimizationScenarioRequest>) => {
    if (isPending) return;
    setScenario((prev) => {
      const next = { ...prev, ...updated };
      if (updated.planning_horizon_periods !== undefined && updated.planning_horizon_periods !== prev.planning_horizon_periods) {
        const newHorizon = updated.planning_horizon_periods;
        const newBudgets: Record<number, string> = {};
        for (let p = 1; p <= newHorizon; p++) {
          newBudgets[p] = prev.periodic_budgets?.[p] !== undefined ? String(prev.periodic_budgets[p]) : '2000000.00';
        }
        next.periodic_budgets = newBudgets;

        // Clamp candidate deadline_period if it exceeds the new horizon
        next.candidates = prev.candidates.map(c => {
          if (c.deadline_period && c.deadline_period > newHorizon) {
            return { ...c, deadline_period: newHorizon };
          }
          return c;
        });
      }
      return next;
    });
  };

  const handleUpdateBudgets = (budgets: Record<number, string>) => {
    if (isPending) return;
    setScenario((prev) => ({ ...prev, periodic_budgets: budgets }));
  };

  const handleUpdateCandidates = (candidates: ProjectOptimizationCandidateDTO[]) => {
    if (isPending) return;
    setScenario((prev) => ({ ...prev, candidates }));
  };

  // Dispatch confirmed optimization evaluation to API
  const handleRunOptimization = async () => {
    if (!validationFindings.isValid || isPending) return;
    try {
      await evaluateScenario(scenario);
    } catch {
      // Error state is captured and exposed via useRecoveryOptimization
    }
  };

  // Validation rules
  const validationFindings = useMemo(() => {
    const issues: string[] = [];
    const warnings: string[] = [];
    const T = scenario.planning_horizon_periods;

    if (!scenario.scenario_name.trim()) {
      issues.push('Scenario name cannot be empty.');
    }
    if (T < 1 || T > 120) {
      issues.push(`Planning horizon periods (T=${T}) must be an integer between 1 and 120.`);
    }
    if ((scenario.period_length_days ?? 30.0) < 1.0 || (scenario.period_length_days ?? 30.0) > 365.0) {
      issues.push('Period length must be between 1.0 and 365.0 days.');
    }
    if (scenario.candidates.length > 500) {
      issues.push(`Candidate count (${scenario.candidates.length}) exceeds policy limit of 500.`);
    }
    if (scenario.candidates.length === 0) {
      issues.push('Scenario must contain at least 1 candidate project.');
    }

    // Tier-1 safety check
    if (hasTier1Candidates) {
      if (!scenario.max_safety_start_period) {
        issues.push('Scenario contains Tier-1 mandatory safety projects but Max Safety Start Period (Ts) is not set.');
      } else if (scenario.max_safety_start_period > T) {
        issues.push(`Max Safety Start Period (Ts=${scenario.max_safety_start_period}) exceeds planning horizon T=${T}.`);
      }
    }

    // Boundary warnings for horizon shrinkage
    scenario.candidates.forEach((c) => {
      if ((c.release_period ?? 1) > T) {
        warnings.push(`Project ${c.project_id} release period (${c.release_period}) exceeds current horizon T=${T}.`);
      }
      if (c.deadline_period && c.deadline_period > T) {
        warnings.push(`Project ${c.project_id} deadline (${c.deadline_period}) exceeds current horizon T=${T}.`);
      }
    });

    return { issues, warnings, isValid: issues.length === 0 };
  }, [scenario, hasTier1Candidates]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <PageHeader
        title="Recovery Portfolio Optimization"
        subtitle="Mathematical Decision Support & Pre-Disaster Rehabilitation Portfolio Planning (Phase 6D-B)"
        icon={Cpu}
        badge={
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/70 text-amber-300 border border-amber-800/80 uppercase font-bold">
              MILP / CP-SAT
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-850 text-slate-400 border border-obsidian-700 uppercase">
              Decision Support Only
            </span>
          </div>
        }
        actions={
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Template:</span>
            <span className="px-2.5 py-1 rounded bg-obsidian-900 border border-obsidian-750 text-amber-ops font-semibold">
              {activeTemplateName}
            </span>
          </div>
        }
      />

      {/* Scenario Template Selector Strip */}
      <div className="p-4 bg-obsidian-900 rounded-xl border border-obsidian-750 space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <h2 className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-ops" />
              Scenario Template Catalog
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              Load curated benchmark recovery scenarios from verified fixtures or create custom portfolios
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={isPending}
              onClick={handleLoadMinimalTemplate}
              className={`px-3 py-1.5 rounded text-xs font-mono transition border ${
                isPending ? 'opacity-50 cursor-not-allowed ' : ''
              }${
                activeTemplateName === 'Minimal Valid Recovery Scenario'
                  ? 'bg-amber-ops text-obsidian-950 font-bold border-amber-ops'
                  : 'bg-obsidian-850 hover:bg-obsidian-800 text-slate-300 border-obsidian-700'
              }`}
            >
              Minimal Valid Template
            </button>
            <button
              type="button"
              disabled={isPending}
              onClick={handleLoadTier1Template}
              className={`px-3 py-1.5 rounded text-xs font-mono transition border ${
                isPending ? 'opacity-50 cursor-not-allowed ' : ''
              }${
                activeTemplateName === 'Tier-1 Mandatory Safety Scenario'
                  ? 'bg-amber-ops text-obsidian-950 font-bold border-amber-ops'
                  : 'bg-obsidian-850 hover:bg-obsidian-800 text-slate-300 border-obsidian-700'
              }`}
            >
              Tier-1 Safety Template
            </button>
            <button
              type="button"
              disabled={isPending}
              onClick={handleLoadStandard5ProjectTemplate}
              className={`px-3 py-1.5 rounded text-xs font-mono transition border ${
                isPending ? 'opacity-50 cursor-not-allowed ' : ''
              }${
                activeTemplateName === 'Controlled 5-Project Benchmark Scenario'
                  ? 'bg-emerald-600 text-white font-bold border-emerald-500'
                  : 'bg-obsidian-850 hover:bg-obsidian-800 text-slate-300 border-obsidian-700'
              }`}
            >
              Standard 5-Project Benchmark
            </button>
            <button
              type="button"
              disabled={isPending}
              onClick={handleResetToCustom}
              className={`px-3 py-1.5 rounded bg-obsidian-850 hover:bg-obsidian-800 text-slate-400 hover:text-slate-200 border border-obsidian-700 text-xs font-mono transition flex items-center gap-1.5 ${
                isPending ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset to Custom
            </button>
          </div>
        </div>

        {/* Validation Status Indicator */}
        <div className="pt-2 border-t border-obsidian-800/80 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            {validationFindings.isValid ? (
              <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <CheckCircle2 className="w-4 h-4" />
                Scenario Configuration Valid for Optimization
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-red-400 font-semibold">
                <AlertTriangle className="w-4 h-4" />
                {validationFindings.issues.length} Configuration Issues Detected
              </span>
            )}
          </div>
          <div className="text-slate-400 text-[11px]">
            {scenario.candidates.length} Candidate Projects | Horizon T = {scenario.planning_horizon_periods}
          </div>
        </div>

        {/* Issues List if Invalid */}
        {!validationFindings.isValid && (
          <div className="p-3 rounded-lg bg-red-950/30 border border-red-800/80 space-y-1">
            <span className="text-[10px] font-mono font-bold text-red-400 uppercase tracking-wider">
              Constraint Invalidation Warnings:
            </span>
            <ul className="text-[11px] font-mono text-red-300 list-disc list-inside space-y-0.5">
              {validationFindings.issues.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Configuration Section Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-obsidian-750 pb-2 text-xs font-mono select-none">
        <button
          type="button"
          onClick={() => setActiveTab('params')}
          className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
            activeTab === 'params'
              ? 'bg-obsidian-800 text-amber-ops font-bold border border-obsidian-700 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-obsidian-900'
          }`}
        >
          <Sliders className="w-4 h-4" />
          1. Parameters & Horizon
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('budgets')}
          className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
            activeTab === 'budgets'
              ? 'bg-obsidian-800 text-amber-ops font-bold border border-obsidian-700 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-obsidian-900'
          }`}
        >
          <Layers className="w-4 h-4" />
          2. Periodic Budgets
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('candidates')}
          className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
            activeTab === 'candidates'
              ? 'bg-obsidian-800 text-amber-ops font-bold border border-obsidian-700 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-obsidian-900'
          }`}
        >
          <Building2 className="w-4 h-4" />
          3. Candidate Projects ({scenario.candidates.length})
        </button>
      </div>

      {/* Active Tab Panel */}
      <div>
        {activeTab === 'params' && (
          <ScenarioParametersCard
            scenario={scenario}
            onChange={handleUpdateScenarioParams}
            hasTier1Candidates={hasTier1Candidates}
            validationWarnings={validationFindings.warnings}
          />
        )}

        {activeTab === 'budgets' && (
          <PeriodicBudgetsEditor
            horizon={scenario.planning_horizon_periods}
            periodicBudgets={scenario.periodic_budgets}
            currency={scenario.budget_currency || 'INR'}
            onChange={handleUpdateBudgets}
          />
        )}

        {activeTab === 'candidates' && (
          <CandidateProjectsGrid
            candidates={scenario.candidates}
            horizon={scenario.planning_horizon_periods}
            currency={scenario.budget_currency || 'INR'}
            onChange={handleUpdateCandidates}
          />
        )}
      </div>

      {/* Solver Execution Section (Stage 3 Integration) */}
      <SolverControlBar
        isValid={validationFindings.isValid}
        isPending={isPending}
        isSuccess={isSuccess}
        isError={isError}
        result={result}
        error={error}
        onRunOptimization={handleRunOptimization}
        onReset={reset}
      />

      {/* Stage 4: Results Visualization & Decision Support Layer */}
      {isSuccess && result?.data && (
        <div className="space-y-6 pt-4 border-t border-obsidian-750">
          {/* 1. Top-Level Solver Status Banner */}
          <SolverStatusBanner
            result={result.data}
            correlationId={result.correlationId}
          />

          {/* 2. Optimization KPI Stats Cards */}
          <OptimizationKPIStats
            result={result.data}
            currency={scenario.budget_currency || 'INR'}
          />

          {/* 3. Project Schedule Timeline (Only for Usable Schedules: OPTIMAL / FEASIBLE) */}
          {hasUsableSchedule(result.data.solver_status) && (
            <ProjectScheduleTimeline
              horizon={scenario.planning_horizon_periods}
              scheduledProjects={result.data.scheduled_projects}
              currency={scenario.budget_currency || 'INR'}
            />
          )}

          {/* 4. Financial Solvency & District Equity Ledgers (Only for Usable Schedules) */}
          {hasUsableSchedule(result.data.solver_status) && (
            <FinancialSolvencyMatrix
              horizon={scenario.planning_horizon_periods}
              periodicSolvency={result.data.periodic_solvency}
              districtAllocationsInr={result.data.district_equity_allocation_inr}
              districtAllocationsCcu={result.data.district_equity_allocation_ccu}
              currency={scenario.budget_currency || 'INR'}
            />
          )}

          {/* 5. Infeasibility Diagnostics View (When diagnostics present or schedule non-usable) */}
          {(result.data.infeasibility_diagnostics || !hasUsableSchedule(result.data.solver_status)) && (
            <InfeasibilityDiagnosticsView
              diagnostics={result.data.infeasibility_diagnostics}
              solverStatus={result.data.solver_status}
            />
          )}
        </div>
      )}

      {/* Indeterminate Solver Overlay with Real Stopwatch */}
      <IndeterminateSolverOverlay isPending={isPending} />
    </div>
  );
};
