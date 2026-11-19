import React, { useState } from 'react';
import { IndianRupee, Layers, Check, RefreshCw, AlertCircle } from 'lucide-react';
import { OperationalCard, StatusBadge } from '../design-system';
import { CurrencyUnit } from '../../types/recoveryOptimization';

interface PeriodicBudgetsEditorProps {
  horizon: number;
  periodicBudgets?: Record<number, string | number>;
  currency: CurrencyUnit;
  onChange: (budgets: Record<number, string>) => void;
}

export interface PeriodicBudgetsSummary {
  total: string | null;
  isValid: boolean;
  invalidPeriods: number[];
}

export const MONETARY_DECIMAL_REGEX = /^\d+(\.\d{1,2})?$/;

/**
 * Pure string-based decimal addition using BigInt cents to preserve exact monetary precision
 * without IEEE-754 floating point distortion.
 *
 * In accordance with Stage 2 monetary contract:
 * - Rejects values with more than 2 decimal places.
 * - Rejects negative values, scientific notation, alphabetic characters, and multiple dots.
 * - Rejects empty/whitespace-only values.
 * - Zero is valid (0, 0.0, 0.00).
 * - If any period entry is invalid, returns isValid: false and total: null rather than
 *   presenting a partial or silently truncated total.
 */
export function computePeriodicBudgetsSummary(
  horizon: number,
  periodicBudgets: Record<number, string | number> = {}
): PeriodicBudgetsSummary {
  const invalidPeriods: number[] = [];
  let totalCents = BigInt(0);

  for (let p = 1; p <= horizon; p++) {
    const raw = periodicBudgets[p];
    const str = raw !== undefined && raw !== null ? String(raw) : '0.00';

    if (!MONETARY_DECIMAL_REGEX.test(str)) {
      invalidPeriods.push(p);
      continue;
    }

    const parts = str.split('.');
    const whole = BigInt(parts[0] || '0');
    let frac = BigInt(0);
    if (parts.length === 2) {
      const fracStr = parts[1];
      if (fracStr.length === 1) {
        frac = BigInt(fracStr) * BigInt(10);
      } else if (fracStr.length === 2) {
        frac = BigInt(fracStr);
      }
    }
    totalCents += whole * BigInt(100) + frac;
  }

  if (invalidPeriods.length > 0) {
    return {
      total: null,
      isValid: false,
      invalidPeriods,
    };
  }

  const wholePart = totalCents / BigInt(100);
  const fracPart = totalCents % BigInt(100);
  return {
    total: `${wholePart.toString()}.${fracPart.toString().padStart(2, '0')}`,
    isValid: true,
    invalidPeriods: [],
  };
}

export const PeriodicBudgetsEditor: React.FC<PeriodicBudgetsEditorProps> = ({
  horizon,
  periodicBudgets = {},
  currency,
  onChange,
}) => {
  const [quickAmount, setQuickAmount] = useState<string>('5000000.00');

  // Handle single period budget edit
  const handleBudgetChange = (period: number, rawVal: string) => {
    const updated: Record<number, string> = {};
    for (let p = 1; p <= horizon; p++) {
      if (p === period) {
        updated[p] = rawVal;
      } else {
        updated[p] = String(periodicBudgets[p] ?? '0.00');
      }
    }
    onChange(updated);
  };

  // Quick fill all periods with a uniform amount
  const handleApplyUniform = () => {
    const targetVal = quickAmount.trim() || '0.00';
    const updated: Record<number, string> = {};
    for (let p = 1; p <= horizon; p++) {
      updated[p] = targetVal;
    }
    onChange(updated);
  };

  // Clear all to 0.00
  const handleClearAll = () => {
    const updated: Record<number, string> = {};
    for (let p = 1; p <= horizon; p++) {
      updated[p] = '0.00';
    }
    onChange(updated);
  };

  const summary = computePeriodicBudgetsSummary(horizon, periodicBudgets);

  return (
    <OperationalCard
      title={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-ops" />
            <span>Periodic Liquidity Budgets (B<sub>t</sub>)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-400">Total Available:</span>
            {summary.isValid ? (
              <span className="text-xs font-mono font-bold text-emerald-400 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60">
                {currency} {summary.total}
              </span>
            ) : (
              <span
                className="text-xs font-mono font-bold text-red-400 px-2 py-0.5 rounded bg-red-950/60 border border-red-800/60 flex items-center gap-1"
                title={`Invalid budget entry in period(s): ${summary.invalidPeriods.map((p) => `t=${p}`).join(', ')}`}
              >
                <AlertCircle className="w-3 h-3 text-red-400 inline" />
                INVALID ({summary.invalidPeriods.length} {summary.invalidPeriods.length === 1 ? 'period' : 'periods'})
              </span>
            )}
          </div>
        </div>
      }
      subtitle={`Configure discrete periodic public funds disbursement for periods t = 1 .. ${horizon}`}
      level={2}
      accent="cyan"
    >
      <div className="space-y-4">
        {/* Quick Bulk Allocation Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-obsidian-900/60 rounded-lg border border-obsidian-750 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-[11px]">Uniform Amount:</span>
            <div className="relative">
              <span className="absolute left-2.5 top-1.5 text-slate-500 text-[10px]">{currency}</span>
              <input
                type="text"
                value={quickAmount}
                onChange={(e) => setQuickAmount(e.target.value)}
                className="pl-9 pr-3 py-1 bg-obsidian-950 border border-obsidian-700 rounded text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-ops w-36"
              />
            </div>
            <button
              type="button"
              onClick={handleApplyUniform}
              className="px-3 py-1 bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/80 rounded transition flex items-center gap-1.5 text-xs font-mono"
            >
              <Check className="w-3.5 h-3.5" />
              Apply to All Periods
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleClearAll}
              className="px-3 py-1 bg-obsidian-800 hover:bg-obsidian-750 text-slate-400 hover:text-slate-200 border border-obsidian-700 rounded transition text-xs font-mono"
            >
              Reset to Zero
            </button>
          </div>
        </div>

        {/* Periodic Grid: 1-based columns */}
        <div className="max-h-72 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {Array.from({ length: horizon }, (_, idx) => {
              const p = idx + 1; // 1-based index
              const rawVal = periodicBudgets[p];
              const valStr = rawVal !== undefined && rawVal !== null ? String(rawVal) : '0.00';
              const isInvalid = !MONETARY_DECIMAL_REGEX.test(valStr);

              return (
                <div
                  key={p}
                  className={`p-2.5 rounded-lg border transition ${
                    isInvalid
                      ? 'bg-red-950/30 border-red-800/80'
                      : 'bg-obsidian-900/50 border-obsidian-750 hover:border-obsidian-600'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono font-bold text-slate-300">
                      Period t = {p}
                    </span>
                    {isInvalid && (
                      <span title="Invalid budget amount (expected non-negative decimal, e.g. 5000000.00)">
                        <AlertCircle className="w-3 h-3 text-red-400" />
                      </span>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      type="text"
                      value={valStr}
                      onChange={(e) => handleBudgetChange(p, e.target.value)}
                      placeholder="0.00"
                      className="w-full px-2 py-1 bg-obsidian-950 border border-obsidian-700 rounded text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-ops text-right"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Invalid entries alert */}
        {summary.invalidPeriods.length > 0 && (
          <div className="flex items-center gap-2 p-2 rounded bg-red-950/40 border border-red-800/60 text-xs font-mono text-red-300">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>
              Invalid or non-conforming budget values in period(s):{' '}
              <span className="font-bold text-red-200">
                {summary.invalidPeriods.map((p) => `t=${p}`).join(', ')}
              </span>
              . Amounts must be non-negative decimals with at most 2 fractional digits (e.g. 5000000.00).
            </span>
          </div>
        )}

        {/* Boundary Notice */}
        <div className="flex items-center justify-between pt-1 text-[10px] font-mono text-slate-500">
          <span>Periods index range: [1, {horizon}]</span>
          <span>Zero-based period indexes strictly rejected by contract schema</span>
        </div>
      </div>
    </OperationalCard>
  );
};
