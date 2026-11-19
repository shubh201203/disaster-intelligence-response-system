import React, { useState, useMemo } from 'react';
import { 
  Building2, 
  Search, 
  Plus, 
  Trash2, 
  Edit3, 
  ShieldAlert, 
  ChevronLeft, 
  ChevronRight, 
  ArrowUpDown, 
  X, 
  Check, 
  Inbox,
  AlertTriangle 
} from 'lucide-react';
import { OperationalCard, StatusBadge, EmptyState } from '../design-system';
import { ProjectOptimizationCandidateDTO, CurrencyUnit } from '../../types/recoveryOptimization';

interface CandidateProjectsGridProps {
  candidates: ProjectOptimizationCandidateDTO[];
  horizon: number;
  currency: CurrencyUnit;
  onChange: (candidates: ProjectOptimizationCandidateDTO[]) => void;
}

type SortField = 'project_id' | 'district_id' | 'estimated_cost' | 'duration_periods' | 'release_period' | 'raw_mcpi_score';
type SortOrder = 'asc' | 'desc';

/**
 * Exact monetary decimal string comparison without IEEE-754 floating-point conversion.
 * 
 * In accordance with Stage 2 monetary contract:
 * - Does not use parseFloat, parseInt, or Number on monetary values.
 * - Supports large integer portions without precision loss via BigInt.
 * - Compares fractional portions exactly by normalizing trailing zeros.
 * - Deterministic ordering policy for non-conforming values:
 *     - Valid non-negative decimals sort before invalid/malformed values.
 *     - If both values are invalid, deterministic fallback to localeCompare is applied.
 *     - Under no circumstance is underlying data modified or converted to float.
 */
export function compareMonetaryDecimalStrings(rawA: unknown, rawB: unknown): number {
  const strA = typeof rawA === 'string' ? rawA.trim() : (rawA !== null && rawA !== undefined ? String(rawA).trim() : '');
  const strB = typeof rawB === 'string' ? rawB.trim() : (rawB !== null && rawB !== undefined ? String(rawB).trim() : '');

  const REGEX = /^\d+(\.\d+)?$/;
  const validA = REGEX.test(strA);
  const validB = REGEX.test(strB);

  // Deterministic invalid policy: valid values before invalid; if both invalid, deterministic localeCompare
  if (!validA && !validB) return strA.localeCompare(strB);
  if (!validA) return 1;
  if (!validB) return -1;

  const [wholeAStr, fracAStr = ''] = strA.split('.');
  const [wholeBStr, fracBStr = ''] = strB.split('.');

  const bigWholeA = BigInt(wholeAStr || '0');
  const bigWholeB = BigInt(wholeBStr || '0');

  if (bigWholeA < bigWholeB) return -1;
  if (bigWholeA > bigWholeB) return 1;

  // Whole parts equal; normalize fractional digits with trailing zeros for exact comparison
  const maxFracLen = Math.max(fracAStr.length, fracBStr.length);
  const normFracA = fracAStr.padEnd(maxFracLen, '0');
  const normFracB = fracBStr.padEnd(maxFracLen, '0');

  if (normFracA < normFracB) return -1;
  if (normFracA > normFracB) return 1;

  return 0;
}

export const CandidateProjectsGrid: React.FC<CandidateProjectsGridProps> = ({
  candidates,
  horizon,
  currency,
  onChange,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('project_id');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Edit / Add candidate drawer or modal state
  const [editingCandidate, setEditingCandidate] = useState<ProjectOptimizationCandidateDTO | null>(null);
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [formErrors, setFormErrors] = useState<string[]>([]);

  // Search & Sorting
  const filteredCandidates = useMemo(() => {
    let result = [...candidates];
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      result = result.filter(
        (c) =>
          c.project_id.toLowerCase().includes(q) ||
          c.project_code.toLowerCase().includes(q) ||
          c.district_id.toLowerCase().includes(q)
      );
    }

    result.sort((a, b) => {
      let cmp = 0;
      if (sortField === 'estimated_cost') {
        cmp = compareMonetaryDecimalStrings(a.estimated_cost, b.estimated_cost);
      } else if (sortField === 'raw_mcpi_score') {
        cmp = (a.raw_mcpi_score ?? 0) - (b.raw_mcpi_score ?? 0);
      } else if (sortField === 'duration_periods') {
        cmp = a.duration_periods - b.duration_periods;
      } else if (sortField === 'release_period') {
        cmp = (a.release_period ?? 1) - (b.release_period ?? 1);
      } else {
        cmp = String(a[sortField]).localeCompare(String(b[sortField]));
      }
      return sortOrder === 'asc' ? cmp : -cmp;
    });

    return result;
  }, [candidates, searchTerm, sortField, sortOrder]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredCandidates.length / pageSize));
  const paginatedCandidates = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredCandidates.slice(start, start + pageSize);
  }, [filteredCandidates, page, pageSize]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const handleDelete = (projectId: string) => {
    onChange(candidates.filter((c) => c.project_id !== projectId));
  };

  const handleOpenAdd = () => {
    if (candidates.length >= 500) return;
    setEditingCandidate({
      project_id: `P-${String(candidates.length + 1).padStart(3, '0')}`,
      project_code: `PROJ-${String(candidates.length + 1).padStart(3, '0')}`,
      district_id: 'DIST-CENTRAL',
      estimated_cost: '5000000.00',
      duration_periods: 2,
      cost_currency: currency,
      release_period: 1,
      deadline_period: Math.min(horizon, 4),
      is_tier1_mandatory: false,
      raw_mcpi_score: 0.75,
    });
    setIsAddingNew(true);
    setFormErrors([]);
  };

  const handleOpenEdit = (cand: ProjectOptimizationCandidateDTO) => {
    setEditingCandidate({ ...cand });
    setIsAddingNew(false);
    setFormErrors([]);
  };

  const handleSaveForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCandidate) return;

    const errors: string[] = [];
    if (!editingCandidate.project_id.trim()) {
      errors.push('Project ID is required.');
    }
    if (!editingCandidate.project_code.trim()) {
      errors.push('Project Code is required.');
    }
    if (!editingCandidate.district_id.trim()) {
      errors.push('District ID is required.');
    }
    if (isAddingNew && candidates.some((c) => c.project_id === editingCandidate.project_id.trim())) {
      errors.push(`Project ID "${editingCandidate.project_id}" already exists. Project IDs must be unique.`);
    }
    if (editingCandidate.duration_periods < 1) {
      errors.push('Duration must be at least 1 period.');
    }
    const rel = editingCandidate.release_period ?? 1;
    if (rel < 1) {
      errors.push('Release period must be 1-based (≥ 1).');
    }
    if (editingCandidate.deadline_period !== null && editingCandidate.deadline_period !== undefined) {
      const minFeasibleDeadline = rel + editingCandidate.duration_periods - 1;
      if (editingCandidate.deadline_period < minFeasibleDeadline) {
        errors.push(`Deadline period (${editingCandidate.deadline_period}) must be ≥ release + duration - 1 (${minFeasibleDeadline}).`);
      }
    }
    const costStr = String(editingCandidate.estimated_cost ?? '').trim();
    if (!/^\d+(\.\d{1,2})?$/.test(costStr)) {
      errors.push('Estimated cost must be a non-negative decimal string with at most 2 decimal places (e.g. 5000000.00).');
    }
    const score = editingCandidate.raw_mcpi_score ?? 0;
    if (score < 0.0 || score > 1.0) {
      errors.push('MCPI score must be a float between 0.0 and 1.0.');
    }

    if (errors.length > 0) {
      setFormErrors(errors);
      return;
    }

    if (isAddingNew) {
      onChange([...candidates, editingCandidate]);
    } else {
      onChange(candidates.map((c) => (c.project_id === editingCandidate.project_id ? editingCandidate : c)));
    }

    setEditingCandidate(null);
    setIsAddingNew(false);
  };

  return (
    <OperationalCard
      title={
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-amber-ops" />
            <span>Candidate Recovery Projects Grid</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-400">Total Candidates:</span>
            <span
              className={`text-xs font-mono font-bold px-2 py-0.5 rounded border ${
                candidates.length >= 500
                  ? 'bg-red-950/80 text-red-300 border-red-800'
                  : 'bg-obsidian-950 text-slate-200 border-obsidian-750'
              }`}
            >
              {candidates.length} / 500 max
            </span>
          </div>
        </div>
      }
      subtitle="Configure recovery project characteristics, safety classifications, and discrete period execution windows"
      level={2}
      accent="amber"
    >
      <div className="space-y-4">
        {/* Controls Toolbar: Search, PageSize, Add Button */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-obsidian-900/60 rounded-lg border border-obsidian-750 text-xs font-mono">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder="Search by ID, code, or district..."
              className="w-full pl-9 pr-3 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-xs font-mono text-slate-100 focus:outline-none focus:border-amber-ops"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-slate-400">
              <span>Rows:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="bg-obsidian-950 border border-obsidian-700 rounded px-2 py-1 text-xs font-mono text-slate-200"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>

            <button
              type="button"
              onClick={handleOpenAdd}
              disabled={candidates.length >= 500}
              className="px-3 py-1.5 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-semibold rounded transition flex items-center gap-1.5 text-xs font-mono disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              Add Project
            </button>
          </div>
        </div>

        {/* Empty State */}
        {candidates.length === 0 ? (
          <EmptyState
            title="No Candidate Projects Configured"
            description="The recovery optimization portfolio requires at least one candidate project to evaluate."
            icon={Inbox}
            action={
              <button
                type="button"
                onClick={handleOpenAdd}
                className="px-3.5 py-1.5 bg-amber-ops text-obsidian-950 font-semibold rounded text-xs font-mono"
              >
                Create First Candidate
              </button>
            }
          />
        ) : (
          /* Table Container */
          <div className="overflow-x-auto rounded-lg border border-obsidian-750">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-obsidian-900 border-b border-obsidian-750 text-slate-400 text-[11px] uppercase tracking-wider select-none">
                <tr>
                  <th
                    className="p-3 cursor-pointer hover:text-slate-200"
                    onClick={() => handleSort('project_id')}
                  >
                    <div className="flex items-center gap-1">
                      <span>Project ID / Code</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th
                    className="p-3 cursor-pointer hover:text-slate-200"
                    onClick={() => handleSort('district_id')}
                  >
                    <div className="flex items-center gap-1">
                      <span>District</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th
                    className="p-3 text-right cursor-pointer hover:text-slate-200"
                    onClick={() => handleSort('estimated_cost')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      <span>Est. Cost ({currency})</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th
                    className="p-3 text-center cursor-pointer hover:text-slate-200"
                    onClick={() => handleSort('duration_periods')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <span>Duration (d<sub>j</sub>)</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th
                    className="p-3 text-center cursor-pointer hover:text-slate-200"
                    onClick={() => handleSort('release_period')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <span>Window [r<sub>j</sub>, d<sub>j</sub><sup>max</sup>]</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="p-3 text-center">Safety Status</th>
                  <th
                    className="p-3 text-right cursor-pointer hover:text-slate-200"
                    onClick={() => handleSort('raw_mcpi_score')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      <span>MCPI Score</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="p-3 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-obsidian-800 bg-obsidian-950/80">
                {paginatedCandidates.map((cand) => (
                  <tr key={cand.project_id} className="hover:bg-obsidian-900/60 transition">
                    <td className="p-3">
                      <div className="font-bold text-slate-200">{cand.project_id}</div>
                      <div className="text-[10px] text-slate-500">{cand.project_code}</div>
                    </td>
                    <td className="p-3 text-slate-300">{cand.district_id}</td>
                    <td className="p-3 text-right font-medium text-emerald-400">
                      {String(cand.estimated_cost)}
                    </td>
                    <td className="p-3 text-center text-slate-300">
                      {cand.duration_periods} periods
                    </td>
                    <td className="p-3 text-center text-slate-400">
                      [{cand.release_period ?? 1}, {cand.deadline_period ?? '∞'}]
                    </td>
                    <td className="p-3 text-center">
                      {cand.is_tier1_mandatory ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-950/80 text-red-300 border border-red-800">
                          <ShieldAlert className="w-3 h-3" />
                          TIER-1 SAFETY
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500">Standard</span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <span className="text-cyan-ops font-bold">
                          {(cand.raw_mcpi_score ?? 0.0).toFixed(3)}
                        </span>
                        <div className="w-12 h-1.5 bg-obsidian-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-cyan-ops"
                            style={{ width: `${Math.min(100, (cand.raw_mcpi_score ?? 0) * 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(cand)}
                          className="p-1 rounded bg-obsidian-800 hover:bg-obsidian-750 text-slate-300 hover:text-white transition"
                          title="Edit candidate"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(cand.project_id)}
                          className="p-1 rounded bg-obsidian-800 hover:bg-red-950/80 text-slate-400 hover:text-red-400 transition"
                          title="Delete candidate"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Toolbar */}
        {filteredCandidates.length > 0 && (
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 pt-1">
            <span>
              Showing {(page - 1) * pageSize + 1} to{' '}
              {Math.min(page * pageSize, filteredCandidates.length)} of {filteredCandidates.length} projects
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-300 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1 rounded bg-obsidian-900 border border-obsidian-750 text-slate-300 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* In-File Modal Dialog for Add / Edit Candidate */}
        {editingCandidate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-sm">
            <div className="w-full max-w-lg bg-obsidian-900 border border-obsidian-700 rounded-xl shadow-2xl p-6 space-y-4 font-mono">
              <div className="flex items-center justify-between border-b border-obsidian-750 pb-3">
                <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-amber-ops" />
                  {isAddingNew ? 'Add Candidate Project' : `Edit Project: ${editingCandidate.project_id}`}
                </h3>
                <button
                  type="button"
                  onClick={() => setEditingCandidate(null)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {formErrors.length > 0 && (
                <div className="p-3 bg-red-950/40 border border-red-800/80 rounded-lg space-y-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold text-red-400 uppercase">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Validation Failures
                  </div>
                  <ul className="text-[10px] text-red-300 list-disc list-inside space-y-0.5">
                    {formErrors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              <form onSubmit={handleSaveForm} className="space-y-3.5 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      Project ID <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      disabled={!isAddingNew}
                      value={editingCandidate.project_id}
                      onChange={(e) => setEditingCandidate({ ...editingCandidate, project_id: e.target.value })}
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops disabled:opacity-60"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      Project Code <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={editingCandidate.project_code}
                      onChange={(e) => setEditingCandidate({ ...editingCandidate, project_code: e.target.value })}
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      District ID <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={editingCandidate.district_id}
                      onChange={(e) => setEditingCandidate({ ...editingCandidate, district_id: e.target.value })}
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      Estimated Cost ({currency}) <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={String(editingCandidate.estimated_cost)}
                      onChange={(e) =>
                        setEditingCandidate({
                          ...editingCandidate,
                          estimated_cost: e.target.value.replace(/[^0-9.]/g, ''),
                        })
                      }
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops text-right"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      Duration (d<sub>j</sub>) <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      value={editingCandidate.duration_periods}
                      onChange={(e) =>
                        setEditingCandidate({
                          ...editingCandidate,
                          duration_periods: Math.max(1, parseInt(e.target.value, 10) || 1),
                        })
                      }
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      Release (r<sub>j</sub>) <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      value={editingCandidate.release_period ?? 1}
                      onChange={(e) =>
                        setEditingCandidate({
                          ...editingCandidate,
                          release_period: Math.max(1, parseInt(e.target.value, 10) || 1),
                        })
                      }
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      Deadline (d<sub>j</sub><sup>max</sup>)
                    </label>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      value={editingCandidate.deadline_period ?? ''}
                      onChange={(e) => {
                        const val = e.target.value === '' ? null : parseInt(e.target.value, 10);
                        setEditingCandidate({ ...editingCandidate, deadline_period: val });
                      }}
                      placeholder="Optional"
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block text-[10px] text-slate-400 uppercase mb-1">
                      MCPI Score [0.0, 1.0]
                    </label>
                    <input
                      type="number"
                      min={0.0}
                      max={1.0}
                      step={0.01}
                      value={editingCandidate.raw_mcpi_score ?? 0.0}
                      onChange={(e) =>
                        setEditingCandidate({
                          ...editingCandidate,
                          raw_mcpi_score: parseFloat(e.target.value) || 0.0,
                        })
                      }
                      className="w-full px-2.5 py-1.5 bg-obsidian-950 border border-obsidian-700 rounded text-slate-100 focus:outline-none focus:border-amber-ops"
                    />
                  </div>

                  <div className="flex items-center pt-4">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={editingCandidate.is_tier1_mandatory ?? false}
                        onChange={(e) =>
                          setEditingCandidate({
                            ...editingCandidate,
                            is_tier1_mandatory: e.target.checked,
                          })
                        }
                        className="w-4 h-4 rounded bg-obsidian-950 border-obsidian-700 text-red-600 focus:ring-0"
                      />
                      <span className="text-xs text-slate-200 font-bold flex items-center gap-1">
                        <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
                        Tier-1 Mandatory Safety
                      </span>
                    </label>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-obsidian-750">
                  <button
                    type="button"
                    onClick={() => setEditingCandidate(null)}
                    className="px-3.5 py-1.5 rounded border border-obsidian-700 text-slate-400 hover:text-slate-200 text-xs font-mono"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded text-xs font-mono"
                  >
                    Save Project
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </OperationalCard>
  );
};
