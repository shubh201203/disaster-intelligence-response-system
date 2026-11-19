import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { 
  Package, 
  Plus, 
  Truck, 
  CheckCircle2, 
  RefreshCw, 
  Layers, 
  Send,
  Droplets,
  Heart,
  Utensils,
  Home,
  Wrench,
  Search,
  Filter,
  Building,
  ShieldCheck,
  AlertCircle,
  Clock,
  ExternalLink,
  Users
} from 'lucide-react';
import { 
  OperationalCard, 
  PageHeader, 
  KPIStat, 
  StatusBadge, 
  SeverityBadge,
  ConfirmDialog,
  LoadingSkeleton 
} from '../../components/design-system';

export const NGODashboard: React.FC = () => {
  const { user } = useAuth();
  const [category, setCategory] = useState('FOOD');
  const [resourceName, setResourceName] = useState('');
  const [quantity, setQuantity] = useState(500);
  const [unit, setUnit] = useState('packets');
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [scopeFilter, setScopeFilter] = useState<'ALL' | 'MY_ORG'>('ALL');

  // Dispatch Dialog State
  const [dispatchModal, setDispatchModal] = useState<{
    isOpen: boolean;
    resourceId: string;
    resourceName: string;
    available: number;
    unit: string;
  }>({
    isOpen: false,
    resourceId: '',
    resourceName: '',
    available: 0,
    unit: ''
  });
  const [dispatchQty, setDispatchQty] = useState(50);
  const [dispatchLoading, setDispatchLoading] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);

  // Fetch verified user & organization profile
  const { data: userProfile } = useQuery({
    queryKey: ['ngo-user-profile', user?.id],
    queryFn: async () => {
      const res = await apiClient.get('/auth/me');
      return res.data;
    }
  });

  const ngoProfile = (userProfile as any)?.ngo_profile || (user as any)?.ngo_profile;

  // Fetch relief inventory stock
  const { data: resources = [], refetch, isLoading } = useQuery({
    queryKey: ['resources-ngo', user?.id],
    queryFn: async () => {
      const res = await apiClient.get('/resources');
      return res.data;
    }
  });

  // Fetch incident resource requests from disaster zones
  const { data: resourceRequests = [], refetch: refetchRequests } = useQuery({
    queryKey: ['resources-requests-ngo', user?.id],
    queryFn: async () => {
      try {
        const res = await apiClient.get('/resources/requests');
        return res.data;
      } catch (e) {
        return [];
      }
    }
  });

  const handleAddResource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resourceName.trim()) return;
    try {
      await apiClient.post('/resources', {
        owner_type: 'NGO',
        category,
        resource_name: resourceName,
        total_quantity: Number(quantity),
        unit,
        location_lat: 13.0850,
        location_lng: 80.2750
      });
      setResourceName('');
      refetch();
    } catch (e) {
      alert('Error adding inventory to DIRS network');
    }
  };

  const handleDispatchConfirm = async () => {
    setDispatchError(null);
    if (dispatchQty <= 0 || dispatchQty > dispatchModal.available) {
      setDispatchError(`Invalid quantity. Must be between 1 and ${dispatchModal.available}.`);
      return;
    }
    setDispatchLoading(true);
    try {
      await apiClient.post(`/resources/${dispatchModal.resourceId}/dispatch?quantity=${dispatchQty}`);
      setDispatchModal(prev => ({ ...prev, isOpen: false }));
      setDispatchError(null);
      refetch();
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      let errorMsg = 'Failed to dispatch stock.';
      if (Array.isArray(detail)) {
        errorMsg = detail.map((d: any) => d.msg || `${d.loc?.join('.')}: ${d.type}`).join(', ');
      } else if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (e.message) {
        errorMsg = e.message;
      }
      setDispatchError(errorMsg);
    } finally {
      setDispatchLoading(false);
    }
  };

  const filteredResources = resources.filter((r: any) => {
    if (scopeFilter === 'MY_ORG' && user?.id) {
      if (r.owner_id !== user.id) return false;
    }
    if (filterCategory === 'ALL') return true;
    return r.category === filterCategory;
  });

  const totalItemsCount = filteredResources.reduce((acc: number, r: any) => acc + (r.available_quantity || 0), 0);
  const myOrgResourcesCount = resources.filter((r: any) => r.owner_id === user?.id).length;

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'FOOD': return Utensils;
      case 'WATER': return Droplets;
      case 'MEDICAL': return Heart;
      case 'SHELTER': return Home;
      default: return Wrench;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12 font-sans">
      {/* Page Header */}
      <PageHeader
        title="NGO RELIEF SUPPLY & DISPATCH HUB"
        subtitle="Humanitarian Supply Logistics, Commodity Inventory & Fleet Convoys"
        icon={Package}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800">
            RELIEF LOGISTICS ACTIVE
          </span>
        }
        actions={
          <button
            type="button"
            onClick={() => {
              refetch();
              refetchRequests();
            }}
            className="px-3 py-1.5 rounded-lg bg-obsidian-850 hover:bg-obsidian-800 border border-obsidian-750 text-slate-300 text-xs font-mono flex items-center gap-1.5 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        }
      />

      {/* NGO Organization Credentials Card */}
      <div className="bg-obsidian-850 border border-obsidian-700 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0">
            <Building className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-mono font-bold text-slate-100">
                {ngoProfile?.org_name || 'Registered Humanitarian Partner'}
              </h2>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                ngoProfile?.verified
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                  : 'bg-purple-950 text-purple-300 border-purple-800'
              }`}>
                {ngoProfile?.verified ? '✓ VERIFIED NGO' : 'REGISTERED PARTNER'}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Registration No: <span className="font-mono text-slate-300">{ngoProfile?.registration_no || 'NGO-STATE-2026-904'}</span> • Authorized Rep: <span className="text-slate-300">{user?.full_name || 'Relief Officer'}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="p-2.5 bg-obsidian-900 rounded-lg border border-obsidian-750 text-center">
            <span className="text-[10px] text-slate-500 block uppercase">Managed SKUs</span>
            <span className="text-xs font-bold text-purple-300">{myOrgResourcesCount} Lines</span>
          </div>
          <div className="p-2.5 bg-obsidian-900 rounded-lg border border-obsidian-750 text-center">
            <span className="text-[10px] text-slate-500 block uppercase">Cluster Role</span>
            <span className="text-xs font-bold text-cyan-ops">RELIEF_SUPPLIER</span>
          </div>
        </div>
      </div>

      {/* Top 4 KPI Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KPIStat
          label="Available Units"
          value={totalItemsCount.toLocaleString()}
          subtext="In active depots"
          icon={Package}
          variant="amber"
        />
        <KPIStat
          label="Active SKUs"
          value={filteredResources.length}
          subtext="Relief commodity lines"
          icon={Layers}
          variant="cyan"
        />
        <KPIStat
          label="Open Needs Requests"
          value={resourceRequests.filter((r: any) => r.status === 'PENDING').length}
          subtext="Field demands awaiting relief"
          icon={AlertCircle}
          variant="emerald"
        />
        <KPIStat
          label="Depot Logistics"
          value="ONLINE"
          subtext="Central supply hub active"
          icon={CheckCircle2}
          variant="neutral"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main: Active Relief Stock List (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          <OperationalCard
            title="Active Relief Inventory Stock"
            subtitle="Inventory In Stock Across Active Depots"
            headerAction={
              <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
                {/* Organization Scope Filter */}
                <div className="flex items-center gap-1 bg-obsidian-900 p-0.5 rounded border border-obsidian-750">
                  <button
                    type="button"
                    onClick={() => setScopeFilter('ALL')}
                    className={`px-2 py-0.5 rounded text-[10px] transition ${
                      scopeFilter === 'ALL'
                        ? 'bg-purple-900 text-purple-200 font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    All Hubs
                  </button>
                  <button
                    type="button"
                    onClick={() => setScopeFilter('MY_ORG')}
                    className={`px-2 py-0.5 rounded text-[10px] transition ${
                      scopeFilter === 'MY_ORG'
                        ? 'bg-purple-900 text-purple-200 font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    My Org Only
                  </button>
                </div>

                {/* Category Filter */}
                <div className="flex items-center gap-1">
                  {['ALL', 'FOOD', 'WATER', 'MEDICAL', 'SHELTER'].map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setFilterCategory(cat)}
                      className={`px-2 py-0.5 rounded text-[10px] transition ${
                        filterCategory === cat
                          ? 'bg-amber-ops text-obsidian-950 font-bold'
                          : 'bg-obsidian-900 text-slate-400 hover:text-white border border-obsidian-750'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            }
          >
            {filteredResources.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-slate-500">
                No relief inventory items match the selected filter.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1 font-mono text-xs">
                {filteredResources.map((res: any) => {
                  const CatIcon = getCategoryIcon(res.category);
                  const isMine = res.owner_id === user?.id;

                  return (
                    <div
                      key={res.id}
                      className="p-3.5 bg-obsidian-900 rounded-xl border border-obsidian-750 flex items-center justify-between gap-4 hover:border-obsidian-600 transition"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-obsidian-800 border border-obsidian-700 flex items-center justify-center text-amber-ops shrink-0">
                          <CatIcon className="w-5 h-5" />
                        </div>
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-200">{res.resource_name}</span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-obsidian-800 text-slate-400 border border-obsidian-700">
                              {res.category}
                            </span>
                            {isMine && (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800 font-bold">
                                MY STOCK
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400">
                            Depot Stock: <span className="text-slate-200 font-bold">{res.available_quantity}</span> / {res.total_quantity} {res.unit}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <button
                          type="button"
                          disabled={res.available_quantity <= 0}
                          onClick={() => {
                            setDispatchModal({
                              isOpen: true,
                              resourceId: res.id,
                              resourceName: res.resource_name,
                              available: res.available_quantity,
                              unit: res.unit
                            });
                            setDispatchQty(Math.min(50, res.available_quantity));
                          }}
                          className="px-3 py-1.5 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold text-xs rounded-lg transition disabled:opacity-40 flex items-center gap-1 shadow"
                        >
                          <Truck className="w-3.5 h-3.5" />
                          <span>Dispatch</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </OperationalCard>

          {/* Incoming Incident Demands / Needs Section */}
          <OperationalCard
            title="Field Relief Demands from Disaster Incidents"
            subtitle="Incident Command resource requirements awaiting fulfillment"
            headerAction={
              <span className="text-xs font-mono text-slate-400">
                {resourceRequests.length} Requests
              </span>
            }
          >
            {resourceRequests.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-slate-500">
                No active incident resource requests logged in the disaster zone.
              </div>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1 font-mono text-xs">
                {resourceRequests.map((req: any) => (
                  <div
                    key={req.id}
                    className="p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 flex items-center justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-amber-ops">{req.incident_code || 'INC'}</span>
                        <span className="font-bold text-slate-200">{req.incident_title || 'Emergency Site'}</span>
                        <SeverityBadge severity={req.priority} />
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">
                        Required: <span className="font-bold text-cyan-ops">{req.quantity_requested}</span> units of <span className="text-slate-200 font-bold">{req.category}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <StatusBadge status={req.status} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </OperationalCard>
        </div>

        {/* Right Column: Add Inventory & Governance Box (4 cols) */}
        <div className="lg:col-span-4 space-y-4 font-mono text-xs">
          <OperationalCard
            title="Add Relief Inventory Stock"
            subtitle="Register new relief commodities into your organization's depot"
          >
            <form onSubmit={handleAddResource} className="space-y-3">
              <div>
                <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-slate-100 font-bold"
                >
                  <option value="FOOD">FOOD (Dry Rations / Meals)</option>
                  <option value="WATER">WATER (Packaged / Potable)</option>
                  <option value="MEDICAL">MEDICAL (First Aid / Trauma)</option>
                  <option value="SHELTER">SHELTER (Tarpaulins / Tents)</option>
                  <option value="CLOTHING">CLOTHING (Blankets / Hygiene)</option>
                  <option value="GENERATOR">GENERATOR / POWER</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                  Commodity Name
                </label>
                <input
                  type="text"
                  required
                  value={resourceName}
                  onChange={(e) => setResourceName(e.target.value)}
                  placeholder="e.g. 20L Water Cans, Family Dry Rations"
                  className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-slate-100 placeholder:text-slate-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                    Quantity
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={quantity}
                    onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                    className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-slate-100 font-bold"
                  />
                </div>

                <div>
                  <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                    Unit of Measure
                  </label>
                  <input
                    type="text"
                    required
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    placeholder="packets / kits"
                    className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-slate-100"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold py-2.5 rounded-lg text-xs font-mono transition flex items-center justify-center gap-1.5 shadow mt-2"
              >
                <Plus className="w-4 h-4" />
                <span>Add Stock to Depot</span>
              </button>
            </form>
          </OperationalCard>

          {/* Institutional Governance Box (Schema Boundary Compliance) */}
          <div className="p-4 bg-obsidian-900 rounded-xl border border-obsidian-750 space-y-2 text-slate-400">
            <div className="flex items-center gap-2 text-amber-ops font-bold text-xs">
              <ShieldCheck className="w-4 h-4" />
              <span>Institutional Governance Policy</span>
            </div>
            <p className="text-[11px] font-sans leading-relaxed text-slate-300">
              Capital infrastructure restoration projects are administered by Government Command under statutory financial sanctions. Multi-agency capital pledges require formal bilateral framework agreements. Unverified string substitution in contractor/supplier records is strictly prohibited by DIRS data-integrity controls.
            </p>
          </div>
        </div>
      </div>

      {/* Dispatch Modal Dialog */}
      {dispatchModal.isOpen && (typeof document !== 'undefined' ? createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-sm bg-obsidian-850 border border-obsidian-700 rounded-xl p-5 space-y-4 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between border-b border-obsidian-750 pb-2">
              <span className="font-bold text-amber-ops text-sm">
                Dispatch Relief Stock
              </span>
              <button
                type="button"
                onClick={() => setDispatchModal(prev => ({ ...prev, isOpen: false }))}
                className="text-slate-500 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-1">
              <p className="text-slate-200 font-bold">{dispatchModal.resourceName}</p>
              <p className="text-[10px] text-slate-500">
                Available in Depot: {dispatchModal.available} {dispatchModal.unit}
              </p>
            </div>

            {dispatchError && (
              <div className="p-2.5 bg-red-950/80 border border-red-800 text-red-300 text-xs rounded-lg font-mono">
                {dispatchError}
              </div>
            )}

            <div>
              <label className="text-[10px] text-slate-400 uppercase block mb-1">
                Quantity to Dispatch
              </label>
              <input
                type="number"
                min="1"
                max={dispatchModal.available}
                value={dispatchQty}
                onChange={(e) => setDispatchQty(parseInt(e.target.value) || 1)}
                className="w-full bg-obsidian-900 border border-obsidian-750 rounded p-2 text-slate-100 font-bold text-sm"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-obsidian-750">
              <button
                type="button"
                onClick={() => setDispatchModal(prev => ({ ...prev, isOpen: false }))}
                className="px-3 py-1.5 text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDispatchConfirm}
                disabled={dispatchLoading}
                className="px-4 py-1.5 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded flex items-center gap-1"
              >
                {dispatchLoading ? 'Dispatching...' : 'Confirm Dispatch'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      ) : null)}
    </div>
  );
};

export default NGODashboard;
