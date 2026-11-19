import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  TrendingUp,
  AlertTriangle,
  Activity,
  Sliders,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Users,
  Building2,
  Layers,
  Sparkles,
  Zap,
  Droplet,
  HeartPulse,
  GraduationCap,
  Briefcase
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid
} from 'recharts';
import {
  fetchCommunityMetricsSummary,
  simulateRecoveryWhatIf,
  rescoreVulnerability
} from '../../api/communityMonitoring';
import {
  RecoveryWhatIfSimulationRequest,
  RecoveryWhatIfSimulationResponse,
  VulnerabilityRescoreRequest,
  VulnerabilityRescoreResponse
} from '../../types/communityMonitoring';
import { OperationalCard, KPIStat, StatusBadge } from '../design-system';

export const RecoverySimulationWorkbench: React.FC = () => {
  // 1. Community Recovery Monitoring Query
  const { data: summary, isLoading: isSummaryLoading, refetch: refetchSummary } = useQuery({
    queryKey: ['community-metrics-summary'],
    queryFn: () => fetchCommunityMetricsSummary(),
  });

  // 2. What-If Simulation State
  const [scenarioName, setScenarioName] = useState('Coastal Ward Multi-Sector Restoration Shock');
  const [horizonPeriods, setHorizonPeriods] = useState(12);
  const [initialBudget, setInitialBudget] = useState(15000000);
  const [budgetMultiplier, setBudgetMultiplier] = useState(1.0);
  const [materialSupplyFactor, setMaterialSupplyFactor] = useState(1.0);
  const [disasterRecurrenceShock, setDisasterRecurrenceShock] = useState(false);
  const [shockPeriod, setShockPeriod] = useState(3);
  const [shockDamageFactor, setShockDamageFactor] = useState(0.25);
  const [simulationResult, setSimulationResult] = useState<RecoveryWhatIfSimulationResponse | null>(null);

  // 3. Vulnerability Rescoring Interactive State
  const [wardCode, setWardCode] = useState('WARD-04-NORTH');
  const [affectedPop, setAffectedPop] = useState(1500);
  const [accessibleNeeds, setAccessibleNeeds] = useState(45);
  const [chronicMed, setChronicMed] = useState(35);
  const [intersectional, setIntersectional] = useState(15);
  const [censusBaseline, setCensusBaseline] = useState(10000);
  const [powerRestored, setPowerRestored] = useState(65);
  const [waterRestored, setWaterRestored] = useState(70);
  const [healthRestored, setHealthRestored] = useState(80);
  const [schoolsRestored, setSchoolsRestored] = useState(55);
  const [livelihoodsRestored, setLivelihoodsRestored] = useState(40);
  const [displacedPersons, setDisplacedPersons] = useState(180);
  const [rescoreResult, setRescoreResult] = useState<VulnerabilityRescoreResponse | null>(null);

  // Mutation: What-If Simulation
  const simulationMutation = useMutation({
    mutationFn: (req: RecoveryWhatIfSimulationRequest) => simulateRecoveryWhatIf(req),
    onSuccess: (data) => {
      setSimulationResult(data);
    },
  });

  // Mutation: Vulnerability Rescore
  const rescoreMutation = useMutation({
    mutationFn: (req: VulnerabilityRescoreRequest) => rescoreVulnerability(req),
    onSuccess: (data) => {
      setRescoreResult(data);
    },
  });

  const handleRunSimulation = () => {
    const payload: RecoveryWhatIfSimulationRequest = {
      scenario_name: scenarioName,
      planning_horizon_periods: horizonPeriods,
      period_length_days: 30.0,
      initial_budget: initialBudget,
      periodic_budget_inflow: 2000000,
      perturbation: {
        budget_multiplier: budgetMultiplier,
        material_supply_factor: materialSupplyFactor,
        disaster_recurrence_shock: disasterRecurrenceShock,
        shock_period: shockPeriod,
        shock_damage_factor: shockDamageFactor,
        sector_priorities: { WASH: 1.3, HEALTH: 1.2 },
      },
    };
    simulationMutation.mutate(payload);
  };

  const handleCalculateRescore = () => {
    const payload: VulnerabilityRescoreRequest = {
      ward_code: wardCode,
      district: 'Central District',
      total_affected_population: affectedPop,
      n_accessible_needs: accessibleNeeds,
      n_chronic_medical: chronicMed,
      n_intersectional: intersectional,
      census_baseline_population: censusBaseline > 0 ? censusBaseline : undefined,
      power_grid_restoration_pct: powerRestored,
      potable_water_access_pct: waterRestored,
      healthcare_facility_operational_pct: healthRestored,
      schools_open_pct: schoolsRestored,
      livelihoods_resumed_pct: livelihoodsRestored,
      remaining_displaced_persons: displacedPersons,
    };
    rescoreMutation.mutate(payload);
  };

  return (
    <div className="space-y-6" data-testid="recovery-simulation-workbench">
      {/* Non-Mutating Policy Safeguard Banner */}
      <div className="bg-slate-900/80 border border-emerald-500/30 rounded-xl p-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100">
              Non-Mutating Forward Simulation Mode Active
            </h4>
            <p className="text-xs text-slate-400">
              Simulations evaluate scenario parameters purely in-memory. Zero database records are modified or committed.
            </p>
          </div>
        </div>
        <span className="px-2.5 py-1 rounded bg-emerald-950/80 border border-emerald-700/50 text-[11px] font-mono font-medium text-emerald-300">
          READ-ONLY SAFEGUARD CERTIFIED
        </span>
      </div>

      {/* 1. Community Recovery Monitoring KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <OperationalCard className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs text-slate-400 font-medium">Wards Monitored</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">
            {summary?.total_wards_monitored ?? 0}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Longitudinal tracking</div>
        </OperationalCard>

        <OperationalCard className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs text-slate-400 font-medium">Avg Recovery Score</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {summary?.average_recovery_score ?? 0}%
          </div>
          <div className="text-[11px] text-emerald-500/80 mt-0.5">Weighted multi-sector</div>
        </OperationalCard>

        <OperationalCard className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs text-slate-400 font-medium">Data Confidence</div>
          <div className="text-2xl font-bold text-blue-400 mt-1">
            {summary?.average_confidence ?? 100}%
          </div>
          <div className="text-[11px] text-blue-500/80 mt-0.5">Decay rate λ=0.05/day</div>
        </OperationalCard>

        <OperationalCard className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs text-slate-400 font-medium">Active Shelters</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {summary?.total_active_shelters ?? 0}
          </div>
          <div className="text-[11px] text-amber-500/80 mt-0.5">Across monitored wards</div>
        </OperationalCard>

        <OperationalCard className="p-4 bg-slate-900/60 border-slate-800">
          <div className="text-xs text-slate-400 font-medium">Remaining Displaced</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">
            {summary?.total_remaining_displaced ?? 0}
          </div>
          <div className="text-[11px] text-rose-500/80 mt-0.5">Displacement pressure</div>
        </OperationalCard>
      </div>

      {/* 2. Main Workbench Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Parameter Control Panel (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <OperationalCard className="p-5 bg-slate-900/70 border-slate-800">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-slate-100">Scenario Perturbation Controls</h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400">WHAT-IF ENGINE</span>
            </div>

            <div className="space-y-4 pt-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Scenario Name</label>
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Budget Multiplier Slider */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Capital Budget Multiplier (β)</span>
                  <span className="font-mono text-cyan-400 font-bold">{(budgetMultiplier * 100).toFixed(0)}% ({budgetMultiplier >= 1.0 ? `+${((budgetMultiplier - 1.0) * 100).toFixed(0)}%` : `${((budgetMultiplier - 1.0) * 100).toFixed(0)}%`})</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.05"
                  value={budgetMultiplier}
                  onChange={(e) => setBudgetMultiplier(parseFloat(e.target.value))}
                  className="w-full accent-cyan-500 bg-slate-800"
                />
                <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
                  <span>-50% Austerity</span>
                  <span>Nominal (1.0x)</span>
                  <span>+50% Surge</span>
                </div>
              </div>

              {/* Material Supply Factor Slider */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Material Supply Factor (μ)</span>
                  <span className="font-mono text-amber-400 font-bold">{(materialSupplyFactor * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0.3"
                  max="1.0"
                  step="0.05"
                  value={materialSupplyFactor}
                  onChange={(e) => setMaterialSupplyFactor(parseFloat(e.target.value))}
                  className="w-full accent-amber-500 bg-slate-800"
                />
                <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
                  <span>30% Bottleneck</span>
                  <span>70% Constrained</span>
                  <span>100% Unconstrained</span>
                </div>
              </div>

              {/* Disaster Recurrence Shock Toggle */}
              <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    <span className="text-xs font-semibold text-slate-200">Secondary Hazard Shock</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={disasterRecurrenceShock}
                      onChange={(e) => setDisasterRecurrenceShock(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-rose-600"></div>
                  </label>
                </div>

                {disasterRecurrenceShock && (
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-800/80">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Occurs at Period</label>
                      <input
                        type="number"
                        min="1"
                        max={horizonPeriods}
                        value={shockPeriod}
                        onChange={(e) => setShockPeriod(parseInt(e.target.value) || 1)}
                        className="w-full px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Damage Setback</label>
                      <input
                        type="number"
                        min="0.1"
                        max="0.5"
                        step="0.05"
                        value={shockDamageFactor}
                        onChange={(e) => setShockDamageFactor(parseFloat(e.target.value) || 0.1)}
                        className="w-full px-2 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200"
                      />
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={handleRunSimulation}
                disabled={simulationMutation.isPending}
                className="w-full py-2.5 px-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-semibold rounded-lg shadow-md flex items-center justify-center gap-2 transition disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-current" />
                {simulationMutation.isPending ? 'Simulating Dynamic Trajectory...' : 'Run What-If Forward Simulation'}
              </button>
            </div>
          </OperationalCard>

          {/* Interactive Vulnerability Rescoring Module */}
          <OperationalCard className="p-5 bg-slate-900/70 border-slate-800">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-400" />
                <h3 className="text-sm font-semibold text-slate-100">Vulnerability Rescoring Engine</h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400">MATH MODEL</span>
            </div>

            <div className="space-y-3 pt-3">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-slate-400 block mb-1">Ward Code</label>
                  <input
                    type="text"
                    value={wardCode}
                    onChange={(e) => setWardCode(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Census Baseline Pop</label>
                  <input
                    type="number"
                    value={censusBaseline}
                    onChange={(e) => setCensusBaseline(parseInt(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded text-slate-200"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-300">
                  <span>Power Grid Restored:</span>
                  <span className="font-mono text-cyan-400">{powerRestored}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={powerRestored}
                  onChange={(e) => setPowerRestored(parseInt(e.target.value))}
                  className="w-full accent-cyan-500 bg-slate-800"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-300">
                  <span>Potable Water Restored:</span>
                  <span className="font-mono text-blue-400">{waterRestored}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={waterRestored}
                  onChange={(e) => setWaterRestored(parseInt(e.target.value))}
                  className="w-full accent-blue-500 bg-slate-800"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-300">
                  <span>Healthcare Operational:</span>
                  <span className="font-mono text-emerald-400">{healthRestored}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={healthRestored}
                  onChange={(e) => setHealthRestored(parseInt(e.target.value))}
                  className="w-full accent-emerald-500 bg-slate-800"
                />
              </div>

              <button
                onClick={handleCalculateRescore}
                disabled={rescoreMutation.isPending}
                className="w-full mt-2 py-2 px-3 bg-violet-600/80 hover:bg-violet-600 text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-2 transition"
              >
                <Zap className="w-3.5 h-3.5" />
                {rescoreMutation.isPending ? 'Calculating Rescore...' : 'Calculate Rescored Vulnerability (φ)'}
              </button>

              {rescoreResult && (
                <div className="mt-3 p-3 bg-slate-950 border border-violet-500/30 rounded-lg space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400">Demographic Baseline φ_V:</span>
                    <span className="font-mono font-bold text-slate-300">
                      {rescoreResult.base_demographic_vulnerability.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400">Rescored Vulnerability φ_res:</span>
                    <span className="font-mono font-bold text-violet-400">
                      {rescoreResult.rescored_vulnerability.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-400">Net Delta:</span>
                    <span className={`font-mono font-bold ${rescoreResult.vulnerability_delta <= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {rescoreResult.vulnerability_delta > 0 ? `+${rescoreResult.vulnerability_delta.toFixed(4)}` : rescoreResult.vulnerability_delta.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs pt-1 border-t border-slate-900">
                    <span className="text-slate-400">Data Freshness:</span>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/50">
                      {rescoreResult.freshness_status} ({rescoreResult.data_confidence}% conf)
                    </span>
                  </div>
                </div>
              )}
            </div>
          </OperationalCard>
        </div>

        {/* Right Column: Dynamic Simulation Visualizations & Results (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <OperationalCard className="p-5 bg-slate-900/70 border-slate-800">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-100">Projected Recovery Trajectory</h3>
              </div>
              {simulationResult?.periods_to_target_80pct && (
                <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">
                  80% Target Reached: Period {simulationResult.periods_to_target_80pct}
                </span>
              )}
            </div>

            <div className="pt-4 h-72">
              {simulationResult ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={simulationResult.trajectory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="period" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} stroke="#94a3b8" tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', fontSize: '12px' }}
                      labelStyle={{ color: '#f1f5f9' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                    <Line
                      type="monotone"
                      dataKey="projected_recovery_score"
                      name="Recovery Score (%)"
                      stroke="#10b981"
                      strokeWidth={2.5}
                      dot={{ r: 3 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="unmet_needs_score"
                      name="Unmet Needs Deficit (%)"
                      stroke="#f43f5e"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
                  <Activity className="w-8 h-8 text-slate-600 animate-pulse" />
                  <p className="text-xs">Adjust perturbation parameters and click "Run What-If Forward Simulation"</p>
                </div>
              )}
            </div>

            {/* Simulation Comparison Metrics Footer */}
            {simulationResult && (
              <div className="mt-4 pt-4 border-t border-slate-800 grid grid-cols-3 gap-3 text-center">
                <div className="p-2.5 bg-slate-950 rounded-lg">
                  <div className="text-[11px] text-slate-400">Baseline Final Score</div>
                  <div className="text-base font-bold text-slate-300 mt-0.5">
                    {simulationResult.baseline_final_recovery_score}%
                  </div>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-lg">
                  <div className="text-[11px] text-slate-400">Simulated Final Score</div>
                  <div className="text-base font-bold text-cyan-400 mt-0.5">
                    {simulationResult.simulated_final_recovery_score}%
                  </div>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-lg">
                  <div className="text-[11px] text-slate-400">Net Score Delta</div>
                  <div className={`text-base font-bold mt-0.5 ${simulationResult.recovery_score_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {simulationResult.recovery_score_delta >= 0 ? `+${simulationResult.recovery_score_delta}%` : `${simulationResult.recovery_score_delta}%`}
                  </div>
                </div>
              </div>
            )}
          </OperationalCard>

          {/* Bottleneck Resources & Displaced Persons Trajectory */}
          {simulationResult && (
            <OperationalCard className="p-5 bg-slate-900/70 border-slate-800">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-slate-100">Supply Bottlenecks & Operational Constraints</h3>
              </div>

              <div className="pt-3 space-y-3">
                {simulationResult.bottleneck_resources.length > 0 ? (
                  <div className="space-y-2">
                    {simulationResult.bottleneck_resources.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-amber-950/30 border border-amber-600/30 rounded-lg flex items-center justify-between"
                      >
                        <div>
                          <div className="text-xs font-semibold text-amber-300">{item.material_category}</div>
                          <div className="text-[11px] text-slate-400">
                            Demand: {item.demand_quantity} | Available: {item.available_supply}
                          </div>
                        </div>
                        <span className="px-2 py-0.5 bg-rose-950/80 border border-rose-700/50 text-[10px] font-mono font-bold text-rose-300 rounded">
                          DEFICIT -{item.deficit_quantity} ({item.impact_level})
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-emerald-950/30 border border-emerald-600/30 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    Zero material bottlenecks detected under current scenario configuration.
                  </div>
                )}
              </div>
            </OperationalCard>
          )}
        </div>
      </div>
    </div>
  );
};
