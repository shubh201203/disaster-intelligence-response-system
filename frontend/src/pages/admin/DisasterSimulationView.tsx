import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { 
  AlertTriangle, 
  Layers, 
  Play, 
  RefreshCw, 
  MapPin, 
  Truck, 
  Users, 
  Building2, 
  Activity, 
  ShieldAlert, 
  CheckCircle2, 
  ArrowRight,
  TrendingDown,
  TrendingUp,
  FileSpreadsheet,
  Compass,
  Cpu,
  Sliders,
  Filter,
  Search,
  RotateCcw
} from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { 
  OperationalCard, 
  KPIStat, 
  PageHeader, 
  StatusBadge, 
  SeverityBadge, 
  LoadingSkeleton 
} from '../../components/design-system';
import { RecoverySimulationWorkbench } from '../../components/recovery/RecoverySimulationWorkbench';

// Leaflet default icon fix
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

export const DisasterSimulationView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'map' | 'simulator' | 'compare' | 'recovery'>('map');
  const [selectedScenarioType, setSelectedScenarioType] = useState<string>('SCEN_DEMO_A_SURGE');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('SCEN_DEMO_A_SURGE');
  const [scenarioParams, setScenarioParams] = useState<Record<string, any>>({
    severity: 'CRITICAL',
    evacuees: 250,
    blocked_edges: 3,
    capacity_reduction_pct: 50,
    vehicles_disabled: 3,
    volunteer_drop_pct: 40,
  });

  const [activeLayers, setActiveLayers] = useState<Record<string, boolean>>({
    INCIDENTS: true,
    SHELTERS: true,
    DEPOTS: true,
    VEHICLES: true,
    VOLUNTEERS: true,
    ROAD_BLOCKAGES: true,
    RESPONSE_COVERAGE: false,
    EVACUATION_ZONES: true,
  });

  const [simulationResult, setSimulationResult] = useState<any>(null);
  const [comparisonResults, setComparisonResults] = useState<any>(null);
  const [spatialQueryResults, setSpatialQueryResults] = useState<any>(null);
  const [spatialTarget, setSpatialTarget] = useState<'shelter' | 'depot' | 'vehicle' | 'volunteer'>('shelter');

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const geojsonLayersRef = useRef<L.LayerGroup | null>(null);
  const spatialHighlightLayerRef = useRef<L.LayerGroup | null>(null);

  // Fetch available simulation scenarios from backend (DEF-04)
  const { data: scenarios = [] } = useQuery({
    queryKey: ['simulation-scenarios'],
    queryFn: async () => {
      const res = await apiClient.get('/simulation/scenarios');
      return res.data;
    }
  });

  useEffect(() => {
    if (scenarios.length > 0 && (!selectedScenarioId || selectedScenarioId === 'SCEN_DEMO_A_SURGE')) {
      const demoSurge = scenarios.find((s: any) => s.id === 'SCEN_DEMO_A_SURGE');
      setSelectedScenarioId(demoSurge ? demoSurge.id : scenarios[0].id);
      if (demoSurge) {
        setScenarioParams({
          severity: 'CRITICAL',
          evacuees: 240,
          blocked_edges: 0,
          capacity_reduction_pct: 0,
          vehicles_disabled: 0,
          volunteer_drop_pct: 0,
        });
      }
    }
  }, [scenarios]);

  // Fetch GIS Layers
  const { data: gisLayers, refetch: refetchLayers, isLoading: layersLoading } = useQuery({
    queryKey: ['gis-layers'],
    queryFn: async () => {
      const layerParams = Object.entries(activeLayers)
        .filter(([_, enabled]) => enabled)
        .map(([k]) => k)
        .join(',');
      const res = await apiClient.get(`/gis/layers?layers=${layerParams}`);
      return res.data;
    }
  });

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      zoomControl: false,
      attributionControl: false
    }).setView([13.0827, 80.2707], 12);

    L.control.zoom({ position: 'topright' }).addTo(map);

    // OpenStreetMap tiles with dark CSS filter (no API key required, zero watermark)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    geojsonLayersRef.current = L.layerGroup().addTo(map);
    spatialHighlightLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Spatial query feature map markers update (DEF-03)
  useEffect(() => {
    if (!mapInstanceRef.current || !spatialHighlightLayerRef.current) return;
    spatialHighlightLayerRef.current.clearLayers();

    if (!spatialQueryResults?.features || spatialQueryResults.features.length === 0) return;

    spatialQueryResults.features.forEach((f: any) => {
      if (f.geometry?.type === 'Point') {
        const [lng, lat] = f.geometry.coordinates;
        const marker = L.circleMarker([lat, lng], {
          radius: 12,
          fillColor: '#06b6d4',
          color: '#ffffff',
          weight: 2.5,
          opacity: 1,
          fillOpacity: 0.85
        });
        marker.bindPopup(`
          <div style="font-family: monospace; font-size: 11px; color: #f1f5f9; padding: 4px;">
            <strong style="color: #06b6d4">KNN MATCH: ${f.properties?.name || f.properties?.shelter_id || 'Matched Entity'}</strong><br/>
            Distance: ${f.properties?.distance_km !== undefined ? `${f.properties.distance_km.toFixed(2)} km` : 'Near'}<br/>
            Lat: ${lat.toFixed(4)} | Lng: ${lng.toFixed(4)}
          </div>
        `);
        spatialHighlightLayerRef.current?.addLayer(marker);
      }
    });

    const first = spatialQueryResults.features[0];
    if (first?.geometry?.coordinates) {
      mapInstanceRef.current.panTo([first.geometry.coordinates[1], first.geometry.coordinates[0]]);
    }
  }, [spatialQueryResults]);

  // Update GeoJSON Layers on Map
  useEffect(() => {
    if (!mapInstanceRef.current || !geojsonLayersRef.current || !gisLayers) return;

    geojsonLayersRef.current.clearLayers();

    for (const [layerType, fc] of Object.entries(gisLayers as Record<string, any>)) {
      if (!fc || !fc.features) continue;

      fc.features.forEach((feature: any) => {
        if (!feature.geometry) return;

        if (feature.geometry.type === 'Point') {
          const coords = feature.geometry.coordinates; // [lng, lat]
          const latLng: [number, number] = [coords[1], coords[0]];

          let markerColor = '#f59e0b';
          let radius = 6;
          let popupTitle = feature.properties?.name || feature.properties?.title || layerType;

          if (layerType === 'INCIDENTS') {
            markerColor = feature.properties?.severity === 'CRITICAL' ? '#ef4444' : '#f97316';
            radius = 8;
          } else if (layerType === 'SHELTERS') {
            markerColor = '#06b6d4';
          } else if (layerType === 'DEPOTS') {
            markerColor = '#a855f7';
          } else if (layerType === 'VEHICLES') {
            markerColor = '#10b981';
          } else if (layerType === 'ROAD_BLOCKAGES') {
            markerColor = '#ef4444';
          }

          const circleMarker = L.circleMarker(latLng, {
            radius,
            fillColor: markerColor,
            color: '#ffffff',
            weight: 1.5,
            opacity: 1,
            fillOpacity: 0.85
          });

          circleMarker.bindPopup(`
            <div style="font-family: monospace; font-size: 11px; color: #f1f5f9; padding: 4px;">
              <strong style="color: ${markerColor}">${popupTitle}</strong><br/>
              Layer: ${layerType}<br/>
              Lat: ${latLng[0].toFixed(4)} | Lng: ${latLng[1].toFixed(4)}
            </div>
          `);

          geojsonLayersRef.current?.addLayer(circleMarker);
        } else if (feature.geometry.type === 'Polygon') {
          const geoJsonLayer = L.geoJSON(feature, {
            style: {
              color: layerType === 'RESPONSE_COVERAGE' ? '#06b6d4' : '#f59e0b',
              weight: 1.5,
              opacity: 0.8,
              fillOpacity: 0.15,
              dashArray: layerType === 'RESPONSE_COVERAGE' ? '4, 4' : undefined
            }
          });
          geoJsonLayer.bindPopup(`
            <div style="font-family: monospace; font-size: 11px; color: #f1f5f9; padding: 4px;">
              <strong>${feature.properties?.title || layerType}</strong><br/>
              Note: ${feature.properties?.disclaimer || 'Simulation boundary'}
            </div>
          `);
          geojsonLayersRef.current?.addLayer(geoJsonLayer);
        }
      });
    }
  }, [gisLayers]);

  // Run Simulation Mutation (DEF-04)
  const runSimulationMutation = useMutation({
    mutationFn: async () => {
      const activeId = selectedScenarioId || 'SCEN_DEMO_A_SURGE';
      let payload: any = {
        base_workload: 'DIRS-GIS-10',
        seed: 42
      };

      const selectedScenario = scenarios.find((s: any) => s.id === activeId);

      // If user customized parameters or entered non-zero stress, pass inline_scenario
      if (scenarioParams.evacuees > 0 || scenarioParams.blocked_edges > 0 || scenarioParams.capacity_reduction_pct > 0 || (scenarioParams.vehicles_disabled || 0) > 0) {
        payload.inline_scenario = {
          name: selectedScenario?.name ? `${selectedScenario.name} [Calibrated]` : 'Custom Stress Simulation',
          description: `Custom stress: ${scenarioParams.evacuees} evacuees, ${scenarioParams.blocked_edges} blocked roads, ${scenarioParams.capacity_reduction_pct}% capacity reduction`,
          hazard_type: selectedScenario?.hazard_type || 'FLOOD',
          severity_multiplier: 1.0,
          affected_area_multiplier: 1.0,
          new_incidents: scenarioParams.evacuees > 0 ? [{
            id: 'SIM_INC_CUSTOM_01',
            title: 'Custom Stress Evacuee Surge',
            latitude: 13.045,
            longitude: 80.250,
            evacuees: scenarioParams.evacuees,
            vulnerable_count: Math.round(scenarioParams.evacuees * 0.2),
            injuries: Math.round(scenarioParams.evacuees * 0.1),
            severity: scenarioParams.severity || 'CRITICAL'
          }] : [],
          additional_blockages: scenarioParams.blocked_edges > 0 ? [
            { u: 'HUB_GUINDY', v: 'NODE_0012', status: 'IMPASSABLE', delay_factor: 0.0, blockage_id: 'CUSTOM_BLK_1' },
            { u: 'HUB_CENTRAL', v: 'NODE_0020', status: 'IMPASSABLE', delay_factor: 0.0, blockage_id: 'CUSTOM_BLK_2' },
            { u: 'NODE_0005', v: 'NODE_0015', status: 'IMPASSABLE', delay_factor: 0.0, blockage_id: 'CUSTOM_BLK_3' }
          ].slice(0, scenarioParams.blocked_edges) : [],
          shelter_capacity_changes: scenarioParams.capacity_reduction_pct > 0 ? {
            'SHELTER_DEMO_003': Math.max(0.05, 1.0 - (scenarioParams.capacity_reduction_pct / 100.0)),
            'SHELTER_INT_002': Math.max(0.05, 1.0 - (scenarioParams.capacity_reduction_pct / 100.0))
          } : {},
          depot_supply_changes: {},
          vehicle_availability_changes: (scenarioParams.vehicles_disabled || 0) > 0 ? ['DEMO-VEH-01', 'DEMO-VEH-05', 'VEH_INT_002'].slice(0, scenarioParams.vehicles_disabled) : [],
          volunteer_availability_changes: [],
          seed: 42
        };
      } else {
        payload.scenario_id = activeId;
      }

      const res = await apiClient.post('/simulation/run', payload);
      return res.data;
    },
    onSuccess: (data) => {
      setSimulationResult(data);
      refetchLayers();
    },
    onError: (err: any) => {
      alert(`Simulation execution failed: ${err.response?.data?.detail || err.message}`);
    }
  });

  // Run Multi-Scenario Compare Mutation (DEF-05)
  const runCompareMutation = useMutation({
    mutationFn: async () => {
      const demoScenarioIds = [
        'SCEN_DEMO_A_SURGE',
        'SCEN_DEMO_B_ROAD_CLOSURE',
        'SCEN_DEMO_C_SHELTER_LOSS',
        'SCEN_DEMO_E_VEHICLE_LOSS',
        'SCEN_DEMO_G_CASCADING_CRISIS'
      ];
      const availableIds = scenarios.map((s: any) => s.id);
      const targetIds = demoScenarioIds.filter(id => availableIds.includes(id));
      const scenario_ids = targetIds.length >= 2 ? targetIds : (availableIds.length > 0 ? availableIds.slice(0, 4) : demoScenarioIds);

      const payload = {
        scenario_ids,
        base_workload: 'DIRS-GIS-10',
        seed: 42
      };
      const res = await apiClient.post('/simulation/compare', payload);
      return res.data;
    },
    onSuccess: (data) => {
      setComparisonResults(data);
    },
    onError: (err: any) => {
      alert(`Multi-scenario comparison failed: ${err.response?.data?.detail || err.message}`);
    }
  });

  // Run Spatial Query Mutation (DEF-03)
  const runSpatialQueryMutation = useMutation({
    mutationFn: async () => {
      let qType = 'NEAREST_SHELTER';
      if (spatialTarget === 'depot') qType = 'NEAREST_DEPOT';
      else if (spatialTarget === 'vehicle') qType = 'NEAREST_VEHICLE';
      else if (spatialTarget === 'volunteer') qType = 'NEAREST_VOLUNTEER';

      const payload = {
        query_type: qType,
        latitude: 13.0827,
        longitude: 80.2707,
        radius_km: 15.0,
        target_layer: spatialTarget,
        k_nearest: 3
      };
      const res = await apiClient.post('/gis/spatial-query', payload);
      return res.data;
    },
    onSuccess: (data) => {
      setSpatialQueryResults(data);
    },
    onError: (err: any) => {
      alert(`Spatial query failed: ${err.response?.data?.detail || err.message}`);
    }
  });

  const toggleLayer = (layerName: string) => {
    setActiveLayers(prev => ({ ...prev, [layerName]: !prev[layerName] }));
    setTimeout(() => refetchLayers(), 100);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 font-sans">
      {/* Simulation Warning Banner - MANDATORY */}
      <div className="bg-amber-950/80 border-2 border-amber-ops rounded-xl p-4 flex items-center gap-4 text-amber-200 shadow-xl">
        <ShieldAlert className="w-8 h-8 text-amber-ops shrink-0 animate-pulse" />
        <div className="text-xs">
          <p className="font-mono font-bold text-sm text-amber-ops uppercase tracking-wider">
            ⚠ THIS IS A SIMULATION — NOT AN OPERATIONAL DISPATCH
          </p>
          <p className="mt-0.5 text-amber-200/90 font-mono text-[11px] leading-relaxed">
            All cascading scenarios, synthetic road blockages, and resource reallocations are evaluated in isolated sandboxes. 
            Base operational state is mathematically immutable (SHA-256 state isolation). Zero public alerts or real-world dispatches are generated.
          </p>
        </div>
      </div>

      {/* Header and Mode Navigation */}
      <PageHeader
        title="DISASTER SIMULATION — WHAT-IF RESPONSE ANALYSIS"
        subtitle="Predictive Sandboxed Optimization & Multi-Layer Spatial Intelligence Engine"
        icon={Compass}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-ops border border-cyan-800">
            PHASE 5G SANDBOX
          </span>
        }
        actions={
          <div className="flex items-center gap-1.5 bg-obsidian-850 p-1 rounded-lg border border-obsidian-750 text-xs font-mono">
            <button
              type="button"
              onClick={() => setActiveTab('map')}
              className={`px-3 py-1.5 rounded-md font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'map'
                  ? 'bg-amber-ops text-obsidian-950 font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              GIS Situation Map
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('simulator')}
              className={`px-3 py-1.5 rounded-md font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'simulator'
                  ? 'bg-amber-ops text-obsidian-950 font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              Scenario Laboratory
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('compare')}
              className={`px-3 py-1.5 rounded-md font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'compare'
                  ? 'bg-amber-ops text-obsidian-950 font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              Comparative Stress
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('recovery')}
              className={`px-3 py-1.5 rounded-md font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'recovery'
                  ? 'bg-amber-ops text-obsidian-950 font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              Community Recovery & What-If
            </button>
          </div>
        }
      />

      {/* TAB 1: GIS SITUATION MAP */}
      {activeTab === 'map' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Map Canvas */}
          <div className="lg:col-span-3">
            <OperationalCard
              title="PostGIS Dark Situation Map"
              subtitle="Center: 13.0827° N, 80.2707° E • PostGIS Spatial Index Query Enabled"
              bodyClassName="p-0 overflow-hidden relative"
            >
              <div className="h-[520px] w-full relative">
                <div ref={mapContainerRef} className="w-full h-full" />

                {/* Floating Map Layers Pill Drawer */}
                <div className="absolute top-3 left-3 z-[400] bg-obsidian-900/90 backdrop-blur border border-obsidian-700/80 rounded-xl p-3 text-xs font-mono shadow-2xl max-w-xs space-y-2 pointer-events-auto">
                  <div className="flex items-center justify-between border-b border-obsidian-750 pb-1.5">
                    <span className="font-bold text-[10px] text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-3 h-3 text-amber-ops" /> Operational Layers
                    </span>
                    <span className="text-[9px] text-cyan-ops">8 ACTIVE</span>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                    {Object.keys(activeLayers).map((layer) => (
                      <button
                        key={layer}
                        type="button"
                        onClick={() => toggleLayer(layer)}
                        className={`px-2 py-1 rounded text-left transition truncate border ${
                          activeLayers[layer]
                            ? 'bg-obsidian-800 text-amber-ops border-amber-900/80 font-bold'
                            : 'bg-obsidian-950 text-slate-500 border-obsidian-800'
                        }`}
                      >
                        {activeLayers[layer] ? '● ' : '○ '}
                        {layer.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Center Chennai Reset Button */}
                <button
                  type="button"
                  onClick={() => mapInstanceRef.current?.setView([13.0827, 80.2707], 12)}
                  className="absolute bottom-3 right-3 z-[400] px-3 py-1.5 bg-obsidian-900/90 backdrop-blur border border-obsidian-700 rounded-lg text-xs font-mono text-slate-200 hover:border-amber-ops transition shadow flex items-center gap-1.5"
                >
                  <Compass className="w-3.5 h-3.5 text-cyan-ops" />
                  Center Chennai
                </button>
              </div>
            </OperationalCard>
          </div>

          {/* Spatial K-Nearest Query Sidebar */}
          <div className="space-y-4">
            <OperationalCard
              title="PostGIS Spatial Query Tool"
              subtitle="ST_DWithin & KNN nearest search"
            >
              <div className="space-y-3 font-mono text-xs">
                <div>
                  <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                    Target Layer
                  </label>
                  <select
                    value={spatialTarget}
                    onChange={(e: any) => setSpatialTarget(e.target.value)}
                    className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-amber-ops"
                  >
                    <option value="shelter">Nearby Shelters</option>
                    <option value="depot">Supply Depots</option>
                    <option value="vehicle">Fleet Vehicles</option>
                    <option value="volunteer">Volunteers</option>
                  </select>
                </div>

                <button
                  type="button"
                  onClick={() => runSpatialQueryMutation.mutate()}
                  disabled={runSpatialQueryMutation.isPending}
                  className="w-full bg-cyan-ops hover:bg-cyan-ops-bright text-obsidian-950 font-bold py-2 rounded-lg text-xs transition flex items-center justify-center gap-1.5 shadow"
                >
                  <Search className="w-3.5 h-3.5" />
                  {runSpatialQueryMutation.isPending ? 'Executing Query...' : 'Run KNN Spatial Query'}
                </button>

                {spatialQueryResults && (
                  <div className="mt-3 p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-cyan-ops font-bold uppercase tracking-wider block">
                        Nearest Match Results:
                      </span>
                      <span className="text-[9px] text-slate-500">
                        {spatialQueryResults.results_count || spatialQueryResults.features?.length || 0} Found
                      </span>
                    </div>
                    <div className="space-y-1.5 text-[11px] max-h-48 overflow-y-auto">
                      {(!spatialQueryResults.features || spatialQueryResults.features.length === 0) ? (
                        <p className="text-slate-500 text-[10px] py-1">No spatial entities matched criteria.</p>
                      ) : (
                        spatialQueryResults.features.map((f: any, idx: number) => {
                          const p = f.properties || {};
                          const coords = f.geometry?.coordinates || [];
                          return (
                            <div key={idx} className="p-2 bg-obsidian-950 rounded border border-obsidian-800 space-y-0.5">
                              <p className="font-bold text-slate-200">{p.name || p.shelter_id || p.depot_id || p.title || p.vehicle_id || p.volunteer_id}</p>
                              <p className="text-cyan-ops text-[10px]">
                                Distance: {typeof p.distance_km === 'number' ? `${p.distance_km.toFixed(2)} km` : 'Direct Proximity'}
                                {coords.length === 2 && ` • [${coords[1].toFixed(3)}°N, ${coords[0].toFixed(3)}°E]`}
                              </p>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                )}
              </div>
            </OperationalCard>
          </div>
        </div>
      )}

      {/* TAB 2: SCENARIO LABORATORY */}
      {activeTab === 'simulator' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Controls Column (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <OperationalCard
              title="Scenario Archetype Selector"
              subtitle="Registered Scenarios from Database (Phase 5G)"
            >
              <div className="space-y-4 font-mono text-xs">
                <div>
                  <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                    Select Stress Scenario
                  </label>
                  <select
                    value={selectedScenarioId}
                    onChange={(e) => {
                      const id = e.target.value;
                      setSelectedScenarioId(id);
                      if (id === 'SCEN_DEMO_A_SURGE') {
                        setScenarioParams({ severity: 'CRITICAL', evacuees: 240, blocked_edges: 0, capacity_reduction_pct: 0, vehicles_disabled: 0, volunteer_drop_pct: 0 });
                      } else if (id === 'SCEN_DEMO_B_ROAD_CLOSURE') {
                        setScenarioParams({ severity: 'CRITICAL', evacuees: 0, blocked_edges: 1, capacity_reduction_pct: 0, vehicles_disabled: 0, volunteer_drop_pct: 0 });
                      } else if (id === 'SCEN_DEMO_C_SHELTER_LOSS') {
                        setScenarioParams({ severity: 'HIGH', evacuees: 0, blocked_edges: 0, capacity_reduction_pct: 50, vehicles_disabled: 0, volunteer_drop_pct: 0 });
                      } else if (id === 'SCEN_DEMO_E_VEHICLE_LOSS') {
                        setScenarioParams({ severity: 'HIGH', evacuees: 0, blocked_edges: 0, capacity_reduction_pct: 0, vehicles_disabled: 2, volunteer_drop_pct: 0 });
                      } else if (id === 'SCEN_DEMO_G_CASCADING_CRISIS') {
                        setScenarioParams({ severity: 'CRITICAL', evacuees: 180, blocked_edges: 1, capacity_reduction_pct: 50, vehicles_disabled: 2, volunteer_drop_pct: 30 });
                      }
                    }}
                    className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-ops"
                  >
                    {scenarios.map((s: any) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.hazard_type})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Grouped Parameters */}
                <div className="space-y-3 pt-2 border-t border-obsidian-750">
                  <span className="text-[10px] text-amber-ops font-bold uppercase tracking-wider block">
                    Scenario Customization Parameters:
                  </span>

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Evacuee Surge Count</label>
                    <input
                      type="number"
                      value={scenarioParams.evacuees}
                      onChange={(e) => setScenarioParams({ ...scenarioParams, evacuees: parseInt(e.target.value) || 0 })}
                      className="w-full bg-obsidian-900 border border-obsidian-700 text-xs rounded px-3 py-1.5 text-slate-100 font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Impassable Road Edges</label>
                    <input
                      type="number"
                      value={scenarioParams.blocked_edges}
                      onChange={(e) => setScenarioParams({ ...scenarioParams, blocked_edges: parseInt(e.target.value) || 0 })}
                      className="w-full bg-obsidian-900 border border-obsidian-700 text-xs rounded px-3 py-1.5 text-slate-100 font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-400 block mb-1">Shelter Capacity Reduction (%)</label>
                    <input
                      type="number"
                      value={scenarioParams.capacity_reduction_pct}
                      onChange={(e) => setScenarioParams({ ...scenarioParams, capacity_reduction_pct: parseInt(e.target.value) || 0 })}
                      className="w-full bg-obsidian-900 border border-obsidian-700 text-xs rounded px-3 py-1.5 text-slate-100 font-mono"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => runSimulationMutation.mutate()}
                  disabled={runSimulationMutation.isPending}
                  className="w-full bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold py-2.5 rounded-lg text-xs font-mono transition flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                >
                  {runSimulationMutation.isPending ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Optimizing Sandbox...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      <span>Execute What-If Simulation</span>
                    </>
                  )}
                </button>
              </div>
            </OperationalCard>
          </div>

          {/* Results Column (8 cols) */}
          <div className="lg:col-span-8 space-y-4">
            {runSimulationMutation.isPending && (
              <div className="p-6 bg-obsidian-850 border border-amber-ops/60 rounded-xl space-y-4 animate-pulse">
                <div className="flex items-center justify-between text-xs font-mono text-amber-ops">
                  <span>SANDBOX OPTIMIZATION IN PROGRESS...</span>
                  <span>SOLVING VRP-TW & LP</span>
                </div>
                {/* Visual Pipeline Progression */}
                <div className="grid grid-cols-5 gap-2 text-[10px] font-mono text-center">
                  <div className="p-2 rounded bg-obsidian-800 text-emerald-400 border border-emerald-800">
                    1. SNAPSHOT
                  </div>
                  <div className="p-2 rounded bg-obsidian-800 text-emerald-400 border border-emerald-800">
                    2. PROPAGATION
                  </div>
                  <div className="p-2 rounded bg-obsidian-800 text-amber-ops border border-amber-800 animate-pulse">
                    3. SOLVER LP
                  </div>
                  <div className="p-2 rounded bg-obsidian-900 text-slate-500 border border-obsidian-750">
                    4. ROUTING
                  </div>
                  <div className="p-2 rounded bg-obsidian-900 text-slate-500 border border-obsidian-750">
                    5. DELTA
                  </div>
                </div>
              </div>
            )}

            {!simulationResult && !runSimulationMutation.isPending ? (
              <div className="p-12 text-center bg-obsidian-850 border border-dashed border-obsidian-750 rounded-xl space-y-2">
                <Sliders className="w-8 h-8 mx-auto text-slate-600" />
                <p className="text-xs font-mono text-slate-300">No Scenario Run Executed Yet</p>
                <p className="text-[10px] text-slate-500 font-sans max-w-sm mx-auto">
                  Configure simulation parameters on the left and click "Execute What-If Simulation" to compute mathematical response deltas against the immutable base operational state.
                </p>
              </div>
            ) : simulationResult ? (
              <div className="space-y-4">
                {/* Result Header */}
                <OperationalCard
                  title={
                    <div className="flex items-center gap-2">
                      <span className="text-amber-ops font-mono font-bold">
                        {simulationResult.scenario_name || simulationResult.scenario_type}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-800 text-slate-400 border border-obsidian-700">
                        {simulationResult.scenario_type}
                      </span>
                    </div>
                  }
                  subtitle={simulationResult.description}
                  headerAction={
                    <span className="text-xs font-mono text-slate-400">
                      Compute Time: {simulationResult.computation_time_ms ? `${simulationResult.computation_time_ms.toFixed(1)} ms` : 'N/A'}
                    </span>
                  }
                >
                  {/* Delta KPI Grid (DEF-04) */}
                  {(() => {
                    const delta = simulationResult.delta || {};
                    const shelter = delta.shelter || {};
                    const resources = delta.resources || {};
                    const vehicles = delta.vehicles || {};
                    const network = delta.network || {};

                    const shelteredDelta = shelter.delta_sheltered ?? delta.delta_evacuees_sheltered ?? 0;
                    const unmetEvacDelta = shelter.delta_unmet ?? delta.delta_unmet_evacuation ?? 0;
                    const resAllocDelta = resources.delta_allocated ?? delta.delta_resource_allocated ?? 0;
                    const resShortfallDelta = resources.delta_unmet ?? delta.delta_unmet_resources ?? 0;
                    const unroutedDelta = vehicles.delta_unrouted ?? delta.delta_unrouted_shipments ?? 0;
                    const isolatedCount = (network.new_isolated_shelters || delta.new_isolated_shelters)?.length ?? 0;

                    const baseSheltered = shelter.base_sheltered ?? delta.base_evacuees_sheltered ?? 0;
                    const scenSheltered = shelter.scenario_sheltered ?? delta.scenario_evacuees_sheltered ?? (baseSheltered + shelteredDelta);
                    const baseUnmetEvac = shelter.base_unmet ?? delta.base_unmet_evacuation ?? 0;
                    const scenUnmetEvac = shelter.scenario_unmet ?? delta.scenario_unmet_evacuation ?? 0;
                    const baseResAlloc = resources.base_allocated ?? delta.base_resource_allocated ?? 0;
                    const scenResAlloc = resources.scenario_allocated ?? delta.scenario_resource_allocated ?? 0;
                    const baseVeh = vehicles.base_vehicles ?? delta.base_vehicle_count ?? 0;
                    const scenVeh = vehicles.scenario_vehicles ?? delta.scenario_vehicle_count ?? 0;
                    const unreachableCount = (network.new_unreachable_nodes || delta.new_unreachable_nodes)?.length ?? 0;

                    return (
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-1">
                        <KPIStat
                          label="Evacuees Sheltered"
                          value={shelteredDelta > 0 ? `+${shelteredDelta}` : `${shelteredDelta}`}
                          subtext={`Base: ${baseSheltered} → Scen: ${scenSheltered}`}
                          variant={shelteredDelta > 0 ? 'emerald' : 'neutral'}
                        />

                        <KPIStat
                          label="Evacuee Gap Delta"
                          value={unmetEvacDelta > 0 ? `+${unmetEvacDelta}` : `${unmetEvacDelta}`}
                          subtext={`Base: ${baseUnmetEvac} → Scen: ${scenUnmetEvac}`}
                          variant={unmetEvacDelta > 0 ? 'critical' : 'emerald'}
                        />

                        <KPIStat
                          label="Supplies Allocated"
                          value={resAllocDelta > 0 ? `+${resAllocDelta.toFixed(0)}` : `${resAllocDelta.toFixed(0)}`}
                          subtext={`Base: ${baseResAlloc.toFixed(0)} → Scen: ${scenResAlloc.toFixed(0)}`}
                          variant={resAllocDelta > 0 ? 'cyan' : 'neutral'}
                        />

                        <KPIStat
                          label="Resource Shortfall"
                          value={resShortfallDelta > 0 ? `+${resShortfallDelta.toFixed(0)}` : `${resShortfallDelta.toFixed(0)}`}
                          subtext="Unmet commodity units"
                          variant={resShortfallDelta > 0 ? 'high' : 'emerald'}
                        />

                        <KPIStat
                          label="Fleet Disruption"
                          value={unroutedDelta > 0 ? `+${unroutedDelta}` : `${unroutedDelta}`}
                          subtext={`Unrouted (Fleet: ${scenVeh}/${baseVeh})`}
                          variant={unroutedDelta > 0 ? 'amber' : 'emerald'}
                        />

                        <KPIStat
                          label="Shelters Isolated"
                          value={isolatedCount}
                          subtext={`Unreachable: ${unreachableCount} nodes`}
                          variant={isolatedCount > 0 ? 'critical' : 'neutral'}
                        />
                      </div>
                    );
                  })()}

                  {/* Factual Summary */}
                  <div className="mt-4 p-3 bg-obsidian-900 rounded-lg border border-obsidian-750 space-y-1">
                    <span className="text-[10px] font-mono text-cyan-ops uppercase font-bold tracking-wider">
                      Factual Intelligence Observations ({simulationResult.intelligence_observations?.length || 0}):
                    </span>
                    <div className="text-xs text-slate-300 font-mono leading-relaxed space-y-1">
                      {simulationResult.intelligence_observations && simulationResult.intelligence_observations.length > 0 ? (
                        simulationResult.intelligence_observations.map((obs: string, idx: number) => (
                          <p key={idx} className="flex items-start gap-1.5">
                            <span className="text-cyan-ops shrink-0">•</span>
                            <span>{obs}</span>
                          </p>
                        ))
                      ) : (
                        <p>{simulationResult.disclaimer || 'Scenario evaluated cleanly without violating mathematical invariants.'}</p>
                      )}
                    </div>
                  </div>
                </OperationalCard>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* TAB 3: COMPARATIVE STRESS ASSESSMENT (DEF-05) */}
      {activeTab === 'compare' && (
        <div className="space-y-4">
          <OperationalCard
            title="Multi-Scenario Comparative Stress Assessment"
            subtitle="Parallel Evaluation of Cascading Scenarios against Baseline Operational State"
            headerAction={
              <button
                type="button"
                onClick={() => runCompareMutation.mutate()}
                disabled={runCompareMutation.isPending}
                className="px-3.5 py-1.5 bg-amber-ops hover:bg-amber-ops-bright text-obsidian-950 font-bold rounded-lg text-xs font-mono transition flex items-center gap-1.5 shadow"
              >
                {runCompareMutation.isPending ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Evaluating...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    Run Multi-Scenario Comparison
                  </>
                )}
              </button>
            }
          >
            {comparisonResults ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono border-collapse">
                  <thead>
                    <tr className="border-b border-obsidian-750 text-slate-500 uppercase text-[10px]">
                      <th className="pb-2.5">Scenario Archetype</th>
                      <th className="pb-2.5">Evacuees Sheltered</th>
                      <th className="pb-2.5">Evacuee Gap</th>
                      <th className="pb-2.5">Supplies Allocated</th>
                      <th className="pb-2.5">Resource Shortfall</th>
                      <th className="pb-2.5">Fleet Unrouted</th>
                      <th className="pb-2.5">Medical Shortfall</th>
                      <th className="pb-2.5">Isolated Shelters</th>
                      <th className="pb-2.5">Alerts</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-800">
                    {/* Baseline Row */}
                    <tr className="bg-obsidian-800/40 font-bold">
                      <td className="py-3 text-cyan-ops">BASELINE ({comparisonResults.base_workload || 'Operational State'})</td>
                      <td className="py-3 tabular-nums text-slate-300">{comparisonResults.base_metrics?.evacuees_sheltered ?? comparisonResults.base_metrics?.total_evacuees_sheltered ?? 0}</td>
                      <td className="py-3 tabular-nums">{comparisonResults.base_metrics?.unmet_evacuation ?? 0}</td>
                      <td className="py-3 tabular-nums text-slate-300">{(comparisonResults.base_metrics?.resource_allocated ?? comparisonResults.base_metrics?.total_resources_allocated ?? 0).toFixed(0)}</td>
                      <td className="py-3 tabular-nums">{comparisonResults.base_metrics?.unmet_resources ?? 0}</td>
                      <td className="py-3 tabular-nums">{comparisonResults.base_metrics?.unrouted_shipments ?? 0}</td>
                      <td className="py-3 tabular-nums">{comparisonResults.base_metrics?.unmet_volunteer_tasks ?? 0}</td>
                      <td className="py-3 tabular-nums">0</td>
                      <td className="py-3">
                        <span className="text-emerald-400 font-bold text-[10px]">NORMAL</span>
                      </td>
                    </tr>

                    {/* Comparison Rows */}
                    {comparisonResults.comparisons?.map((c: any, idx: number) => (
                      <tr key={idx} className="hover:bg-obsidian-800/60 transition">
                        <td className="py-3 font-bold text-slate-100">{c.scenario_name || c.scenario_id}</td>
                        <td className="py-3 tabular-nums">
                          {c.delta_evacuees_sheltered > 0 ? (
                            <span className="text-emerald-400 font-bold">+{c.delta_evacuees_sheltered}</span>
                          ) : (
                            <span className="text-slate-400">{c.delta_evacuees_sheltered || 0}</span>
                          )}
                        </td>
                        <td className="py-3 tabular-nums">
                          {c.delta_unmet_evacuation > 0 ? (
                            <span className="text-red-400 font-bold">+{c.delta_unmet_evacuation}</span>
                          ) : (
                            <span className="text-emerald-400">0</span>
                          )}
                        </td>
                        <td className="py-3 tabular-nums">
                          {c.delta_resource_allocated > 0 ? (
                            <span className="text-cyan-400 font-bold">+{c.delta_resource_allocated.toFixed(0)}</span>
                          ) : (
                            <span className="text-slate-400">{(c.delta_resource_allocated || 0).toFixed(0)}</span>
                          )}
                        </td>
                        <td className="py-3 tabular-nums">
                          {c.delta_unmet_resources > 0 ? (
                            <span className="text-red-400 font-bold">+{c.delta_unmet_resources.toFixed(0)}</span>
                          ) : (
                            <span className="text-emerald-400">0</span>
                          )}
                        </td>
                        <td className="py-3 tabular-nums">
                          {c.delta_unrouted_shipments > 0 ? (
                            <span className="text-amber-ops font-bold">+{c.delta_unrouted_shipments}</span>
                          ) : (
                            <span className="text-emerald-400">0</span>
                          )}
                        </td>
                        <td className="py-3 tabular-nums">
                          {c.delta_medical_unmet_tasks > 0 ? (
                            <span className="text-red-400 font-bold">+{c.delta_medical_unmet_tasks}</span>
                          ) : (
                            <span className="text-emerald-400">0</span>
                          )}
                        </td>
                        <td className="py-3 tabular-nums">
                          {c.new_isolated_shelters_count > 0 ? (
                            <span className="text-red-400 font-bold">{c.new_isolated_shelters_count}</span>
                          ) : (
                            '0'
                          )}
                        </td>
                        <td className="py-3">
                          {c.critical_alerts_count > 0 ? (
                            <span className="px-2 py-0.5 bg-red-950 text-red-400 rounded text-[10px] font-bold border border-red-800">
                              {c.critical_alerts_count} ALERTS
                            </span>
                          ) : (
                            <span className="text-slate-500">None</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-xs font-mono text-slate-500">
                Click "Run Multi-Scenario Comparison" to assess the 4 standard disaster archetypes simultaneously.
              </div>
            )}
          </OperationalCard>
        </div>
      )}

      {/* TAB 4: COMMUNITY RECOVERY & WHAT-IF SIMULATION */}
      {activeTab === 'recovery' && (
        <RecoverySimulationWorkbench />
      )}
    </div>
  );
};

export default DisasterSimulationView;
