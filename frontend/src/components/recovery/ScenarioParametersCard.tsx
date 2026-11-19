import React from 'react';
import { Sliders, AlertTriangle, ShieldAlert, Clock, IndianRupee } from 'lucide-react';
import { OperationalCard, StatusBadge } from '../design-system';
import { RecoveryOptimizationScenarioRequest, CurrencyUnit } from '../../types/recoveryOptimization';

interface ScenarioParametersCardProps {
  scenario: RecoveryOptimizationScenarioRequest;
  onChange: (updated: Partial<RecoveryOptimizationScenarioRequest>) => void;
  hasTier1Candidates: boolean;
  validationWarnings?: string[];
}

export const ScenarioParametersCard: React.FC<ScenarioParametersCardProps> = ({
  scenario,
  onChange,
  hasTier1Candidates,
  validationWarnings = [],
}) => {
  const handleHorizonChange = (val: number) => {
    const horizon = isNaN(val) ? 1 : Math.max(1, Math.min(120, Math.floor(val)));
    onChange({ planning_horizon_periods: horizon });
  };

  const handlePeriodDaysChange = (val: number) => {
    const days = isNaN(val) ? 30.0 : Math.max(1.0, Math.min(365.0, val));
    onChange({ period_length_days: days });
  };

  const handleInitialCashChange = (val: string) => {
    // Sanitize to valid non-negative decimal string
    const cleaned = val.replace(/[^0-9.]/g, '');
    onChange({ initial_cash: cleaned });
  };

  const handleMaxSafetyPeriodChange = (val: string) => {
    if (val === '') {
      onChange({ max_safety_start_period: null });
    } else {
      const p = parseInt(val, 10);
      onChange({ max_safety_start_period: isNaN(p) ? null : Math.max(1, p) });
    }
  };

  return (
    <OperationalCard
      title={
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-amber-ops" />
          <span>Core Scenario Parameters</span>
        </div>
      }
      subtitle="Planning horizon, temporal discretization, and liquidity parameters (1-based discrete indexing)"
      level={2}
      accent="amber"
    >
      <div className="space-y-6">
        {/* Scenario Name */}
        <div>
          <label className="block text-[11px] font-mono text-slate-300 uppercase tracking-wider mb-1.5">
            Scenario Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={scenario.scenario_name}
            maxLength={100}
            onChange={(e) => onChange({ scenario_name: e.target.value })}
            placeholder="e.g. Q4 Post-Disaster Infrastructure Rehabilitation"
            className="w-full px-3 py-2 bg-obsidian-950 border border-obsidian-700 rounded-lg text-xs font-mono text-slate-100 focus:outline-none focus:border-amber-ops transition"
          />
        </div>

        {/* Primary Parameter Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Planning Horizon (T) */}
          <div className="bg-obsidian-900/60 p-3.5 rounded-lg border border-obsidian-750">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-mono text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-ops" />
                Horizon periods (T)
              </label>
              <span className="text-[10px] font-mono text-slate-500">1 ≤ T ≤ 120</span>
            </div>
            <input
              type="number"
              min={1}
              max={120}
              step={1}
              value={scenario.planning_horizon_periods}
              onChange={(e) => handleHorizonChange(parseInt(e.target.value, 10))}
              className="w-full px-3 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-ops transition"
            />
            <p className="text-[10px] font-mono text-slate-500 mt-1">
              Discrete 1-based periods: [1, {scenario.planning_horizon_periods}]
            </p>
          </div>

          {/* Period Length (Days) */}
          <div className="bg-obsidian-900/60 p-3.5 rounded-lg border border-obsidian-750">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-mono text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-ops" />
                Period Length (Days)
              </label>
              <span className="text-[10px] font-mono text-slate-500">1.0 ≤ Δt ≤ 365.0</span>
            </div>
            <input
              type="number"
              min={1.0}
              max={365.0}
              step={0.5}
              value={scenario.period_length_days ?? 30.0}
              onChange={(e) => handlePeriodDaysChange(parseFloat(e.target.value))}
              className="w-full px-3 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-ops transition"
            />
            <p className="text-[10px] font-mono text-slate-500 mt-1">
              Total duration: {((scenario.period_length_days ?? 30.0) * scenario.planning_horizon_periods).toFixed(0)} days
            </p>
          </div>

          {/* Initial Liquidity Cash Balance */}
          <div className="bg-obsidian-900/60 p-3.5 rounded-lg border border-obsidian-750">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-mono text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <IndianRupee className="w-3.5 h-3.5 text-emerald-400" />
                Initial Cash ({scenario.cash_currency || 'INR'})
              </label>
              <span className="text-[10px] font-mono text-slate-500">Decimal string</span>
            </div>
            <input
              type="text"
              value={String(scenario.initial_cash ?? '0.00')}
              onChange={(e) => handleInitialCashChange(e.target.value)}
              placeholder="0.00"
              className="w-full px-3 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-xs font-mono text-slate-100 focus:outline-none focus:border-emerald-500 transition"
            />
            <p className="text-[10px] font-mono text-slate-500 mt-1">
              Opening liquidity pool at period t = 1
            </p>
          </div>
        </div>

        {/* Currency & Safety Window Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
          {/* Currency Configuration */}
          <div className="bg-obsidian-900/40 p-3 rounded-lg border border-obsidian-800 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-mono text-slate-300 block">Currency Denomination</span>
              <span className="text-[10px] font-mono text-slate-500">Standard accounting units</span>
            </div>
            <div className="flex items-center gap-2">
              {(['INR', 'CCU'] as CurrencyUnit[]).map((cur) => (
                <button
                  key={cur}
                  type="button"
                  onClick={() => onChange({ cash_currency: cur, budget_currency: cur })}
                  className={`px-3 py-1 rounded text-xs font-mono font-semibold transition border ${
                    (scenario.cash_currency || 'INR') === cur
                      ? 'bg-amber-ops/20 text-amber-300 border-amber-600/80'
                      : 'bg-obsidian-950 text-slate-400 border-obsidian-700 hover:text-slate-200'
                  }`}
                >
                  {cur}
                </button>
              ))}
            </div>
          </div>

          {/* Tier-1 Mandatory Safety Window */}
          <div className="bg-obsidian-900/40 p-3 rounded-lg border border-obsidian-800">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-mono text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert className={`w-3.5 h-3.5 ${hasTier1Candidates ? 'text-red-400' : 'text-slate-500'}`} />
                Max Safety Start Period (T<sub>s</sub>)
              </label>
              {hasTier1Candidates ? (
                <StatusBadge status="MANDATORY" variant="danger" />
              ) : (
                <span className="text-[10px] font-mono text-slate-500">Optional</span>
              )}
            </div>
            <input
              type="number"
              min={1}
              max={scenario.planning_horizon_periods}
              step={1}
              value={scenario.max_safety_start_period ?? ''}
              onChange={(e) => handleMaxSafetyPeriodChange(e.target.value)}
              placeholder={`1 .. ${scenario.planning_horizon_periods}`}
              className={`w-full px-3 py-1.5 bg-obsidian-950 border rounded text-xs font-mono text-slate-100 focus:outline-none transition ${
                hasTier1Candidates && (!scenario.max_safety_start_period || scenario.max_safety_start_period > scenario.planning_horizon_periods)
                  ? 'border-red-600 focus:border-red-500'
                  : 'border-obsidian-700 focus:border-amber-ops'
              }`}
            />
            <p className="text-[10px] font-mono text-slate-500 mt-1">
              {hasTier1Candidates
                ? `Safety deadline constraint: All Tier-1 mandatory projects must start on or before period Ts (1 ≤ Ts ≤ ${scenario.planning_horizon_periods})`
                : 'No Tier-1 mandatory projects currently in candidate portfolio'}
            </p>
          </div>
        </div>

        {/* Dynamic Horizon Reduction Warnings */}
        {validationWarnings.length > 0 && (
          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="text-[11px] font-mono font-bold text-amber-300 uppercase">
                Horizon Boundary Warnings
              </span>
              <ul className="text-[10px] font-mono text-amber-200/90 list-disc list-inside space-y-0.5">
                {validationWarnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </OperationalCard>
  );
};
