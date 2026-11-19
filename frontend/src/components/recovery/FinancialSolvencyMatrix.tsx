/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 4: Financial Solvency Matrix
 *
 * Implements strictly separate accounting ledgers for periodic solvency and district equity.
 *
 * Strict Guarantees:
 * - CCU Solvency Ledger: revenue_receipt_ccu, expenditure_ccu, cash_balance_ccu presented together.
 * - INR Liquidity Ledger: cash_balance_inr presented separately.
 * - Zero arithmetic, addition, subtraction, or conversion between CCU and INR values.
 * - Zero derivation of non-existent INR revenue or disbursement fields.
 * - The backend-provided is_solvent boolean is the sole authoritative indicator of solvency.
 * - Exact Decimal digits preserved without IEEE-754 float conversion.
 */

import React, { useState } from 'react';
import { 
  Landmark, 
  Coins, 
  IndianRupee, 
  MapPin, 
  CheckCircle2, 
  AlertOctagon, 
  Info 
} from 'lucide-react';
import { 
  PeriodSolvencyResultDTO, 
  CurrencyUnit 
} from '../../types/recoveryOptimization';
import { formatExactInrString } from './OptimizationKPIStats';

interface FinancialSolvencyMatrixProps {
  /** Planning horizon in discrete periods (T in [1, 120]) */
  horizon: number;
  /** Period solvency balance outcomes emitted by backend */
  periodicSolvency: PeriodSolvencyResultDTO[];
  /** District equity allocations in INR Decimal strings */
  districtAllocationsInr: Record<string, string>;
  /** District equity allocations in CCU integer strings */
  districtAllocationsCcu: Record<string, string>;
  /** Currency denomination of scenario (default: INR) */
  currency?: CurrencyUnit;
}

export const FinancialSolvencyMatrix: React.FC<FinancialSolvencyMatrixProps> = ({
  horizon,
  periodicSolvency,
  districtAllocationsInr,
  districtAllocationsCcu,
  currency = 'INR',
}) => {
  const [activeLedger, setActiveLedger] = useState<'ccu' | 'inr' | 'district'>('ccu');

  // Sorted list of districts from allocations
  const districtIds = Object.keys(districtAllocationsInr).sort();

  return (
    <div className="rounded-xl border border-obsidian-750 bg-obsidian-900 overflow-hidden font-mono text-xs shadow-xl space-y-0">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-obsidian-750 bg-obsidian-850 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-obsidian-800 border border-obsidian-700 text-emerald-400">
            <Landmark className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Financial Solvency & District Equity Ledgers
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800/60 font-semibold">
                Dual-Ledger Governance
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Authoritative periodic liquidity accounting and geographical distribution ledgers
            </p>
          </div>
        </div>

        {/* Tab Switcher for Ledgers */}
        <div className="flex items-center gap-1.5 p-1 rounded-lg bg-obsidian-900 border border-obsidian-750 text-[11px]">
          <button
            type="button"
            onClick={() => setActiveLedger('ccu')}
            className={`px-3 py-1.5 rounded-md transition flex items-center gap-1.5 ${
              activeLedger === 'ccu'
                ? 'bg-obsidian-800 text-emerald-400 font-bold border border-obsidian-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Coins className="w-3.5 h-3.5" />
            1. CCU Solvency Ledger
          </button>

          <button
            type="button"
            onClick={() => setActiveLedger('inr')}
            className={`px-3 py-1.5 rounded-md transition flex items-center gap-1.5 ${
              activeLedger === 'inr'
                ? 'bg-obsidian-800 text-cyan-400 font-bold border border-obsidian-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <IndianRupee className="w-3.5 h-3.5" />
            2. INR Liquidity Ledger
          </button>

          <button
            type="button"
            onClick={() => setActiveLedger('district')}
            className={`px-3 py-1.5 rounded-md transition flex items-center gap-1.5 ${
              activeLedger === 'district'
                ? 'bg-obsidian-800 text-amber-ops font-bold border border-obsidian-700 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            3. District Equity Ledger
          </button>
        </div>
      </div>

      {/* Main Ledger Content Panels */}
      <div className="p-4 sm:p-5 space-y-3">
        {/* LEDGER 1: CCU Solvency Ledger */}
        {activeLedger === 'ccu' && (
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <Info className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>
                Internal mathematical accounting ledger denominated strictly in Cost Currency Units (CCU). Period solvency is verified authoritatively by the backend solver.
              </span>
            </div>

            {periodicSolvency.length === 0 ? (
              <p className="text-slate-500 text-xs py-4 text-center">
                No periodic solvency records returned.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-obsidian-750">
                <table className="w-full text-left text-[11px] font-mono">
                  <thead className="bg-obsidian-850 text-slate-300 uppercase text-[10px] tracking-wider border-b border-obsidian-750">
                    <tr>
                      <th className="px-3.5 py-2.5">Period (t)</th>
                      <th className="px-3.5 py-2.5 text-right">Revenue Inflow (CCU)</th>
                      <th className="px-3.5 py-2.5 text-right">Disbursement (CCU)</th>
                      <th className="px-3.5 py-2.5 text-right">Cash Reserve (CCU)</th>
                      <th className="px-3.5 py-2.5 text-center">Solvency Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-800">
                    {periodicSolvency.map((row) => (
                      <tr key={row.period} className="hover:bg-obsidian-850/60 transition">
                        <td className="px-3.5 py-2.5 font-bold text-slate-200">
                          Period {row.period}
                        </td>
                        <td className="px-3.5 py-2.5 text-right text-slate-300">
                          {row.revenue_receipt_ccu}
                        </td>
                        <td className="px-3.5 py-2.5 text-right text-amber-300">
                          {row.expenditure_ccu}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-bold text-slate-100">
                          {row.cash_balance_ccu}
                        </td>
                        <td className="px-3.5 py-2.5 text-center">
                          {row.is_solvent ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              SOLVENT
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-red-300 border border-red-800">
                              <AlertOctagon className="w-3 h-3 text-red-400" />
                              DEFICIT
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* LEDGER 2: INR Liquidity Ledger */}
        {activeLedger === 'inr' && (
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              <span>
                Cumulative cash liquidity reserve denominated in Indian Rupees (INR). Exact decimal cents are preserved without floating-point arithmetic.
              </span>
            </div>

            {periodicSolvency.length === 0 ? (
              <p className="text-slate-500 text-xs py-4 text-center">
                No periodic liquidity records returned.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-obsidian-750">
                <table className="w-full text-left text-[11px] font-mono">
                  <thead className="bg-obsidian-850 text-slate-300 uppercase text-[10px] tracking-wider border-b border-obsidian-750">
                    <tr>
                      <th className="px-3.5 py-2.5">Period (t)</th>
                      <th className="px-3.5 py-2.5 text-right">Cumulative Cash Reserve (INR)</th>
                      <th className="px-3.5 py-2.5 text-center">Authoritative Solvency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-800">
                    {periodicSolvency.map((row) => (
                      <tr key={row.period} className="hover:bg-obsidian-850/60 transition">
                        <td className="px-3.5 py-2.5 font-bold text-slate-200">
                          Period {row.period}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-bold text-cyan-300">
                          {formatExactInrString(row.cash_balance_inr)}
                        </td>
                        <td className="px-3.5 py-2.5 text-center">
                          {row.is_solvent ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              SOLVENT
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-red-300 border border-red-800">
                              <AlertOctagon className="w-3 h-3 text-red-400" />
                              DEFICIT
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* LEDGER 3: District Equity Ledger */}
        {activeLedger === 'district' && (
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <Info className="w-3.5 h-3.5 text-amber-ops shrink-0" />
              <span>
                Geographical portfolio equity allocations across districts. CCU and INR values are presented as separate audit columns without cross-unit calculation.
              </span>
            </div>

            {districtIds.length === 0 ? (
              <p className="text-slate-500 text-xs py-4 text-center">
                No district equity allocation records returned.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-obsidian-750">
                <table className="w-full text-left text-[11px] font-mono">
                  <thead className="bg-obsidian-850 text-slate-300 uppercase text-[10px] tracking-wider border-b border-obsidian-750">
                    <tr>
                      <th className="px-3.5 py-2.5">District Identifier</th>
                      <th className="px-3.5 py-2.5 text-right">Allocated Expenditure (CCU)</th>
                      <th className="px-3.5 py-2.5 text-right">Allocated Expenditure (INR)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-800">
                    {districtIds.map((distId) => (
                      <tr key={distId} className="hover:bg-obsidian-850/60 transition">
                        <td className="px-3.5 py-2.5 font-bold text-slate-200">
                          {distId}
                        </td>
                        <td className="px-3.5 py-2.5 text-right text-slate-300">
                          {districtAllocationsCcu[distId] ? `${districtAllocationsCcu[distId]} CCU` : '0 CCU'}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-bold text-amber-300">
                          {formatExactInrString(districtAllocationsInr[distId] || '0.00')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Notice */}
      <div className="px-5 py-3 border-t border-obsidian-750/70 bg-obsidian-850/60 text-[10px] text-slate-500 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <span>
          Mathematical Guarantee: No cross-currency subtraction or float conversion applied.
        </span>
        <span className="text-slate-400">
          Horizon: {horizon} Periods
        </span>
      </div>
    </div>
  );
};
