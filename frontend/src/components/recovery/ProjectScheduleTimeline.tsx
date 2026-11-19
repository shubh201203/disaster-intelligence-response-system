/**
 * DIRS Phase 6D-B Milestone 4 Gate 2 Stage 4: Project Schedule Timeline
 *
 * Responsive discrete Gantt-style periodic timeline for recovery portfolio optimization.
 *
 * Strict Guarantees:
 * - Discrete periods are strictly 1-based [1, T].
 * - Grid column start = scheduled_start_period, column end = scheduled_completion_period + 1.
 * - Inclusive duration = completion - start + 1.
 * - Scheduled projects partitioned from unselected projects using is_selected.
 * - Unselected projects display strictly "Not selected" — zero invented rejection causes or fabricated deadlines.
 * - Tier-1 mandatory projects visually distinguished with life-safety indicators.
 * - Horizontal scrolling with sticky project code column supporting T up to 120 periods.
 */

import React, { useState, useMemo } from 'react';
import { 
  Calendar, 
  Clock, 
  ShieldCheck, 
  ShieldAlert, 
  ChevronDown, 
  ChevronRight, 
  Building2, 
  AlertTriangle,
  Info
} from 'lucide-react';
import { 
  ScheduledProjectResultDTO, 
  CurrencyUnit 
} from '../../types/recoveryOptimization';
import { formatExactInrString } from './OptimizationKPIStats';

interface ProjectScheduleTimelineProps {
  /** Planning horizon in discrete periods (T in [1, 120]) */
  horizon: number;
  /** Scheduled project results array emitted by backend */
  scheduledProjects: ScheduledProjectResultDTO[];
  /** Currency denomination (default: INR) */
  currency?: CurrencyUnit;
}

export const ProjectScheduleTimeline: React.FC<ProjectScheduleTimelineProps> = ({
  horizon,
  scheduledProjects,
  currency = 'INR',
}) => {
  const [isUnscheduledOpen, setIsUnscheduledOpen] = useState(false);

  // Partition scheduled vs unselected projects
  const { scheduledList, unselectedList } = useMemo(() => {
    const scheduled: ScheduledProjectResultDTO[] = [];
    const unselected: ScheduledProjectResultDTO[] = [];

    for (const p of scheduledProjects) {
      if (p.is_selected) {
        scheduled.push(p);
      } else {
        unselected.push(p);
      }
    }

    // Sort scheduled by start period ascending, then project code
    scheduled.sort((a, b) => {
      const startA = a.scheduled_start_period ?? 0;
      const startB = b.scheduled_start_period ?? 0;
      if (startA !== startB) return startA - startB;
      return a.project_code.localeCompare(b.project_code);
    });

    // Sort unselected by raw_mcpi_score descending
    unselected.sort((a, b) => b.raw_mcpi_score - a.raw_mcpi_score);

    return { scheduledList: scheduled, unselectedList: unselected };
  }, [scheduledProjects]);

  // Array of 1-based period numbers [1 .. T]
  const periodNumbers = useMemo(() => {
    return Array.from({ length: horizon }, (_, i) => i + 1);
  }, [horizon]);

  // Count unselected mandatory projects for warning banner
  const unselectedMandatoryCount = useMemo(() => {
    return unselectedList.filter((p) => p.is_tier1_mandatory).length;
  }, [unselectedList]);

  return (
    <div className="rounded-xl border border-obsidian-750 bg-obsidian-900 overflow-hidden font-mono text-xs shadow-xl space-y-0">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-obsidian-750 bg-obsidian-850 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-obsidian-800 border border-obsidian-700 text-amber-ops">
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Project Schedule Timeline
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800/60 font-semibold">
                Horizon T = {horizon} Periods
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Discrete 1-based periodic Gantt schedule derived from CP-SAT integer optimization
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-slate-400">
            Scheduled: <strong className="text-emerald-400">{scheduledList.length}</strong> / {scheduledProjects.length}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">
            Unscheduled: <strong className="text-amber-400">{unselectedList.length}</strong>
          </span>
        </div>
      </div>

      {/* Unselected Mandatory Warning if Any */}
      {unselectedMandatoryCount > 0 && (
        <div className="p-3 bg-red-950/40 border-b border-red-800/80 flex items-center gap-2 text-red-300 text-xs">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          <span>
            <strong>Warning:</strong> {unselectedMandatoryCount} Tier-1 mandatory life-safety project(s) were not selected in this schedule.
          </span>
        </div>
      )}

      {/* Discrete Timeline Gantt Table */}
      <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-obsidian-700 scrollbar-track-obsidian-900">
        <div className="min-w-max">
          {/* Header Track: Project Info column + Discrete Period Columns */}
          <div className="flex items-center border-b border-obsidian-750 bg-obsidian-850/90 text-slate-400 text-[11px] select-none sticky top-0 z-10">
            <div className="w-64 sm:w-72 px-4 py-2.5 shrink-0 border-r border-obsidian-750 font-semibold tracking-wider uppercase text-slate-300">
              Candidate Project
            </div>
            <div 
              className="grid gap-1 px-3 py-2 shrink-0"
              style={{
                gridTemplateColumns: `repeat(${horizon}, minmax(44px, 1fr))`,
                width: `${Math.max(horizon * 48, 600)}px`,
              }}
            >
              {periodNumbers.map((p) => (
                <div 
                  key={p} 
                  className="text-center font-bold text-[10px] py-1 rounded bg-obsidian-800/60 border border-obsidian-700/60 text-slate-300"
                  title={`Planning Period ${p}`}
                >
                  P{p}
                </div>
              ))}
            </div>
          </div>

          {/* Scheduled Projects Rows */}
          {scheduledList.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              No candidate projects were scheduled in this portfolio.
            </div>
          ) : (
            <div className="divide-y divide-obsidian-800/60">
              {scheduledList.map((project) => {
                const start = project.scheduled_start_period!;
                const comp = project.scheduled_completion_period!;
                const duration = comp - start + 1;

                return (
                  <div 
                    key={project.project_id}
                    className="flex items-center hover:bg-obsidian-850/40 transition group"
                  >
                    {/* Sticky-like Left Info Panel */}
                    <div className="w-64 sm:w-72 px-4 py-3 shrink-0 border-r border-obsidian-750 flex flex-col justify-center">
                      <div className="flex items-center justify-between gap-1.5">
                        <span className="font-bold text-slate-200 truncate" title={project.project_code}>
                          {project.project_code}
                        </span>
                        {project.is_tier1_mandatory && (
                          <span 
                            className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-950 text-amber-300 border border-amber-700/80 shrink-0 flex items-center gap-0.5"
                            title="Tier-1 Mandatory Life-Safety Project"
                          >
                            <ShieldCheck className="w-2.5 h-2.5 text-amber-400" />
                            T1
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between gap-2 mt-1 text-[10px] text-slate-400">
                        <span className="text-slate-400 truncate">{project.district_id}</span>
                        <span className="text-emerald-400 font-semibold shrink-0">
                          {currency === 'CCU' 
                            ? `${project.cost_ccu} CCU`
                            : formatExactInrString(project.cost_inr)}
                        </span>
                      </div>
                    </div>

                    {/* Gantt Grid Track */}
                    <div 
                      className="grid gap-1 px-3 py-2.5 shrink-0 relative items-center"
                      style={{
                        gridTemplateColumns: `repeat(${horizon}, minmax(44px, 1fr))`,
                        width: `${Math.max(horizon * 48, 600)}px`,
                      }}
                    >
                      {/* Background period grid lines */}
                      {periodNumbers.map((p) => (
                        <div 
                          key={p} 
                          className="h-8 border-r border-obsidian-800/40 pointer-events-none"
                        />
                      ))}

                      {/* Project Active Schedule Bar */}
                      <div
                        className={`absolute h-7 rounded-md border flex items-center justify-between px-2 text-[10px] font-bold shadow-md transition ${
                          project.is_tier1_mandatory
                            ? 'bg-amber-950/80 border-amber-600/90 text-amber-200'
                            : 'bg-cyan-950/80 border-cyan-700/90 text-cyan-200'
                        }`}
                        style={{
                          /* Strictly 1-based CSS grid positioning */
                          gridColumnStart: start,
                          gridColumnEnd: comp + 1,
                          left: `${((start - 1) / horizon) * 100}%`,
                          width: `${(duration / horizon) * 100}%`,
                        }}
                        title={`${project.project_code} | Active Periods: [P${start}..P${comp}] (${duration} period${duration > 1 ? 's' : ''}) | MCPI: ${project.raw_mcpi_score}`}
                      >
                        <span className="truncate">
                          {project.project_code}
                        </span>
                        <span className="text-[9px] font-normal text-slate-300 opacity-90 shrink-0 ml-1">
                          {duration}P
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Unscheduled Candidate Registry Drawer */}
      <div className="border-t border-obsidian-750 bg-obsidian-850/60">
        <button
          type="button"
          onClick={() => setIsUnscheduledOpen((prev) => !prev)}
          className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-obsidian-800/60 transition text-xs select-none"
        >
          <div className="flex items-center gap-2">
            {isUnscheduledOpen ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
            <span className="font-bold text-slate-300 uppercase tracking-wider text-[11px]">
              Unscheduled Candidate Registry ({unselectedList.length} Projects)
            </span>
          </div>
          <span className="text-[10px] text-slate-400">
            {isUnscheduledOpen ? 'Collapse Registry' : 'Expand to View Unselected Candidates'}
          </span>
        </button>

        {isUnscheduledOpen && (
          <div className="p-4 border-t border-obsidian-750/70 bg-obsidian-900/80 space-y-3">
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <Info className="w-3.5 h-3.5 text-cyan-ops shrink-0" />
              <span>
                The following candidate projects were evaluated by the solver but were not selected in the optimal portfolio.
              </span>
            </div>

            {unselectedList.length === 0 ? (
              <p className="text-slate-500 text-xs py-2">
                All submitted candidates were successfully scheduled in this portfolio.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-obsidian-750">
                <table className="w-full text-left text-[11px] font-mono">
                  <thead className="bg-obsidian-800 text-slate-300 uppercase text-[10px] tracking-wider border-b border-obsidian-700">
                    <tr>
                      <th className="px-3 py-2">Project ID</th>
                      <th className="px-3 py-2">Project Code</th>
                      <th className="px-3 py-2">District</th>
                      <th className="px-3 py-2">Cost</th>
                      <th className="px-3 py-2 text-center">Priority (MCPI)</th>
                      <th className="px-3 py-2 text-center">Mandatory</th>
                      <th className="px-3 py-2 text-center">Outcome Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-800">
                    {unselectedList.map((project) => (
                      <tr key={project.project_id} className="hover:bg-obsidian-850/60 transition">
                        <td className="px-3 py-2 font-bold text-slate-300">{project.project_id}</td>
                        <td className="px-3 py-2 text-slate-200">{project.project_code}</td>
                        <td className="px-3 py-2 text-slate-400">{project.district_id}</td>
                        <td className="px-3 py-2 text-slate-300">
                          {currency === 'CCU' 
                            ? `${project.cost_ccu} CCU`
                            : formatExactInrString(project.cost_inr)}
                        </td>
                        <td className="px-3 py-2 text-center text-slate-300">
                          {project.raw_mcpi_score.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {project.is_tier1_mandatory ? (
                            <span className="px-1.5 py-0.5 rounded text-[9px] bg-red-950 text-red-300 border border-red-700 font-bold">
                              Tier-1
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-obsidian-800 text-slate-400 border border-obsidian-700">
                            Not selected
                          </span>
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
    </div>
  );
};
