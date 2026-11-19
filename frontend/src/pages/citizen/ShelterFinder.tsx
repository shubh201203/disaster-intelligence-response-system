import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { 
  MapPin, 
  Check, 
  Cross, 
  Shield, 
  Users, 
  ArrowLeft,
  Home,
  Activity,
  Heart,
  Utensils,
  Droplets,
  Zap,
  Navigation
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { OperationalCard, PageHeader, LoadingSkeleton, NavigationModal } from '../../components/design-system';

export const ShelterFinder: React.FC = () => {
  const navigate = useNavigate();
  const [navShelter, setNavShelter] = useState<any | null>(null);

  const { data: shelters = [], isLoading } = useQuery({
    queryKey: ['shelters-nearby'],
    queryFn: async () => {
      const res = await apiClient.get('/shelters/nearby?lat=13.0827&lng=80.2707&radius_km=25');
      return res.data;
    }
  });

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 font-sans">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/citizen')}
          className="text-xs font-mono text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>
        <span className="text-[10px] font-mono text-cyan-ops bg-cyan-950/80 border border-cyan-800 px-3 py-1 rounded-full">
          PostGIS Multi-Criteria Suitability Active
        </span>
      </div>

      <PageHeader
        title="SMART EMERGENCY SHELTER LOCATOR"
        subtitle="Ranked dynamically by distance, remaining capacity, medical readiness, food/water stocks & safety elevation"
        icon={Home}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
            {shelters.length} SHELTERS ONLINE
          </span>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <LoadingSkeleton variant="card" />
          <LoadingSkeleton variant="card" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {shelters.map((s: any) => {
            const occRatio = Math.round((s.current_occupancy / Math.max(1, s.total_capacity)) * 100);
            const isNearCapacity = occRatio >= 85;

            return (
              <OperationalCard
                key={s.id}
                title={
                  <div className="flex items-center justify-between">
                    <span className="text-slate-100 font-bold">{s.name}</span>
                    <span className="text-xs font-mono text-amber-ops bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800">
                      {s.suitability_score !== undefined ? `${s.suitability_score} / 100 MATCH` : 'ACTIVE SHELTER'}
                    </span>
                  </div>
                }
                subtitle={
                  <span className="flex items-center gap-1 text-cyan-ops mt-0.5">
                    <MapPin className="w-3.5 h-3.5 shrink-0" />
                    {s.address} {s.distance_km !== undefined ? `(${s.distance_km.toFixed(1)} km away)` : ''}
                  </span>
                }
                accent={isNearCapacity ? 'red' : 'emerald'}
              >
                <div className="space-y-4 font-mono text-xs">
                  {/* Capacity Meter */}
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>Occupancy Capacity</span>
                      <span className={isNearCapacity ? 'text-red-400 font-bold' : 'text-slate-200'}>
                        {s.current_occupancy} / {s.total_capacity} ({occRatio}%)
                      </span>
                    </div>
                    <div className="w-full bg-obsidian-950 h-2.5 rounded-full overflow-hidden border border-obsidian-800">
                      <div
                        className={`h-full transition-all ${
                          isNearCapacity ? 'bg-red-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, occRatio)}%` }}
                      />
                    </div>
                  </div>

                  {/* Facilities Badges */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span
                      className={`px-2 py-1 rounded text-[10px] flex items-center gap-1.5 border ${
                        s.has_medical
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                          : 'bg-obsidian-950 text-slate-500 border-obsidian-800'
                      }`}
                    >
                      <Heart className="w-3 h-3 text-red-400" />
                      <span>Medical Care</span>
                    </span>

                    <span
                      className={`px-2 py-1 rounded text-[10px] flex items-center gap-1.5 border ${
                        s.has_food
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                          : 'bg-obsidian-950 text-slate-500 border-obsidian-800'
                      }`}
                    >
                      <Utensils className="w-3 h-3 text-amber-ops" />
                      <span>Hot Meals</span>
                    </span>

                    <span
                      className={`px-2 py-1 rounded text-[10px] flex items-center gap-1.5 border ${
                        s.has_water
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                          : 'bg-obsidian-950 text-slate-500 border-obsidian-800'
                      }`}
                    >
                      <Droplets className="w-3 h-3 text-cyan-ops" />
                      <span>Clean Water</span>
                    </span>

                    <span
                      className={`px-2 py-1 rounded text-[10px] flex items-center gap-1.5 border ${
                        s.has_power_backup
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                          : 'bg-obsidian-950 text-slate-500 border-obsidian-800'
                      }`}
                    >
                      <Zap className="w-3 h-3 text-amber-300" />
                      <span>Generator Power</span>
                    </span>
                  </div>

                  {/* Action */}
                  <div className="pt-2 border-t border-obsidian-800 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500">
                      STATUS: {isNearCapacity ? 'HIGH DEMAND' : 'ACCEPTING EVACUEES'}
                    </span>
                    <button
                      type="button"
                      onClick={() => setNavShelter(s)}
                      className="px-3 py-1 bg-obsidian-800 hover:bg-obsidian-750 text-slate-200 hover:text-white rounded border border-obsidian-700 text-xs flex items-center gap-1.5 transition"
                    >
                      <Navigation className="w-3 h-3 text-cyan-ops" />
                      Get Directions
                    </button>
                  </div>
                </div>
              </OperationalCard>
            );
          })}
        </div>
      )}

      {/* DEF-07: In-app Waypoint & External Navigation Modal */}
      <NavigationModal
        isOpen={Boolean(navShelter)}
        onClose={() => setNavShelter(null)}
        title={navShelter?.name || 'Emergency Relief Shelter'}
        subtitle="Evacuation Shelter Destination"
        address={navShelter?.address || 'Designated Safe Haven'}
        latitude={navShelter?.latitude || 13.0827}
        longitude={navShelter?.longitude || 80.2707}
        distanceKm={navShelter?.distance_km}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
            {navShelter?.suitability_score !== undefined ? `${navShelter.suitability_score} / 100 MATCH` : 'SHELTER'}
          </span>
        }
      />
    </div>
  );
};

export default ShelterFinder;
