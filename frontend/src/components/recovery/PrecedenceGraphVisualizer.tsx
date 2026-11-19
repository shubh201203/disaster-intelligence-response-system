/**
 * DIRS Phase 6E Accelerated Programme: Work Package 1
 * Precedence Graph Visualizer (React 18 / TypeScript).
 *
 * Interactive SVG/Canvas DAG visualization for recovery project precedence networks:
 * - Topological layered DAG layout.
 * - Critical Path Method (CPM) node and edge highlighting.
 * - Interactive node inspection (ES, EF, LS, LF, Total Float, Free Float).
 * - Dry-run candidate dependency validation modal with cycle feedback.
 * - Zoom, pan, and filter controls.
 * - Zero external graph library dependencies (pure React + SVG + Tailwind).
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  GitCommit,
  ArrowRight,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
  Clock,
  DollarSign,
  ShieldAlert,
  Info,
  RefreshCw,
  PlusCircle,
  X,
} from 'lucide-react';
import {
  PrecedenceGraphResponse,
  PrecedenceGraphNode,
  PrecedenceGraphEdge,
  PrecedenceEdgeValidateResponse,
} from '../../types/precedence';
import { validateDependencyEdge, seedStandardPrecedenceScenario } from '../../api/precedence';

interface PrecedenceGraphVisualizerProps {
  /** Precedence graph data emitted by backend */
  data: PrecedenceGraphResponse;
  /** Loading indicator */
  isLoading?: boolean;
  /** Error message if query failed */
  error?: string | null;
  /** Callback to trigger refresh */
  onRefresh?: () => void;
  /** Active period days config */
  periodDays?: number;
  /** Callback when period days change */
  onPeriodDaysChange?: (days: number) => void;
}

interface LayoutNode extends PrecedenceGraphNode {
  x: number;
  y: number;
  width: number;
  height: number;
  level: number;
}

const NODE_WIDTH = 220;
const NODE_HEIGHT = 96;
const HORIZONTAL_GAP = 90;
const VERTICAL_GAP = 40;

export const PrecedenceGraphVisualizer: React.FC<PrecedenceGraphVisualizerProps> = ({
  data,
  isLoading = false,
  error = null,
  onRefresh,
  periodDays = 30,
  onPeriodDaysChange,
}) => {
  // Viewport / Zoom State
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 40, y: 40 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Selection & Inspector State
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [highlightCriticalOnly, setHighlightCriticalOnly] = useState<boolean>(false);

  // Candidate Validation Drawer / Modal State
  const [isValidateModalOpen, setIsValidateModalOpen] = useState<boolean>(false);
  const [candidatePredId, setCandidatePredId] = useState<string>('');
  const [candidateSuccId, setCandidateSuccId] = useState<string>('');
  const [candidateLag, setCandidateLag] = useState<number>(0);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<PrecedenceEdgeValidateResponse | null>(null);
  const [isSeeding, setIsSeeding] = useState<boolean>(false);

  // SVG ref for bounds
  const svgRef = useRef<SVGSVGElement | null>(null);

  const handleSeedScenario = async () => {
    setIsSeeding(true);
    try {
      await seedStandardPrecedenceScenario();
      if (onRefresh) onRefresh();
    } catch (err: any) {
      alert('Failed to seed standard scenario: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsSeeding(false);
    }
  };

  // Set default candidate IDs when modal opens
  useEffect(() => {
    if (isValidateModalOpen && data.nodes.length >= 2) {
      if (!candidatePredId) setCandidatePredId(data.nodes[0].id);
      if (!candidateSuccId) setCandidateSuccId(data.nodes[1].id);
    }
  }, [isValidateModalOpen, data.nodes, candidatePredId, candidateSuccId]);

  // Compute Topological Layered Layout
  const { layoutNodes, layoutEdges, svgWidth, svgHeight } = useMemo(() => {
    if (!data.nodes.length) {
      return { layoutNodes: [], layoutEdges: [], svgWidth: 800, svgHeight: 500 };
    }

    // Build incoming/outgoing adjacency
    const inEdges: Record<string, string[]> = {};
    const outEdges: Record<string, string[]> = {};
    data.nodes.forEach((n) => {
      inEdges[n.id] = [];
      outEdges[n.id] = [];
    });

    data.edges.forEach((e) => {
      if (outEdges[e.predecessor_project_id]) outEdges[e.predecessor_project_id].push(e.successor_project_id);
      if (inEdges[e.successor_project_id]) inEdges[e.successor_project_id].push(e.predecessor_project_id);
    });

    // Compute levels (longest path from roots or early_start)
    const levels: Record<string, number> = {};
    const nodeMap: Record<string, PrecedenceGraphNode> = {};
    data.nodes.forEach((n) => {
      nodeMap[n.id] = n;
      levels[n.id] = 0;
    });

    // If topological order exists, assign levels based on predecessor max level + 1
    const order = data.topological_order.length
      ? data.topological_order
      : data.nodes.map((n) => n.id);

    order.forEach((nid) => {
      const preds = inEdges[nid] || [];
      if (preds.length > 0) {
        let maxPredLevel = -1;
        preds.forEach((p) => {
          maxPredLevel = Math.max(maxPredLevel, levels[p] ?? 0);
        });
        levels[nid] = maxPredLevel + 1;
      } else {
        levels[nid] = 0;
      }
    });

    // Group nodes by level
    const levelBuckets: Record<number, PrecedenceGraphNode[]> = {};
    let maxLevel = 0;
    Object.entries(levels).forEach(([nid, lvl]) => {
      maxLevel = Math.max(maxLevel, lvl);
      if (!levelBuckets[lvl]) levelBuckets[lvl] = [];
      if (nodeMap[nid]) levelBuckets[lvl].push(nodeMap[nid]);
    });

    // Position nodes
    const positioned: LayoutNode[] = [];
    const positions: Record<string, { x: number; y: number }> = {};
    let maxCalculatedHeight = 0;

    for (let lvl = 0; lvl <= maxLevel; lvl++) {
      const bucket = levelBuckets[lvl] || [];
      const colX = lvl * (NODE_WIDTH + HORIZONTAL_GAP) + 40;
      const bucketHeight = bucket.length * (NODE_HEIGHT + VERTICAL_GAP);
      maxCalculatedHeight = Math.max(maxCalculatedHeight, bucketHeight);

      bucket.forEach((node, idx) => {
        const rowY = idx * (NODE_HEIGHT + VERTICAL_GAP) + 60;
        positions[node.id] = { x: colX, y: rowY };
        positioned.push({
          ...node,
          x: colX,
          y: rowY,
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
          level: lvl,
        });
      });
    }

    const calculatedWidth = (maxLevel + 1) * (NODE_WIDTH + HORIZONTAL_GAP) + 200;
    const calculatedHeight = maxCalculatedHeight + 160;

    return {
      layoutNodes: positioned,
      layoutEdges: data.edges,
      svgWidth: Math.max(calculatedWidth, 1000),
      svgHeight: Math.max(calculatedHeight, 600),
    };
  }, [data]);

  // Selected Node Object
  const selectedNode = useMemo(() => {
    return layoutNodes.find((n) => n.id === selectedNodeId) || null;
  }, [layoutNodes, selectedNodeId]);

  // Handle Drag / Pan
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === 'svg' || (e.target as HTMLElement).id === 'graph-canvas') {
      setIsDragging(true);
      dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStartRef.current.x,
        y: e.clientY - dragStartRef.current.y,
      });
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  // Zoom Controls
  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.15, 2.0));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.15, 0.4));
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 40, y: 40 });
    setSelectedNodeId(null);
  };

  // Dry-run validation submit
  const handleValidateCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidatePredId || !candidateSuccId) return;

    setIsValidating(true);
    setValidationResult(null);

    try {
      const res = await validateDependencyEdge({
        predecessor_project_id: candidatePredId,
        successor_project_id: candidateSuccId,
        lag_days: Number(candidateLag) || 0,
        dependency_type: 'FINISH_TO_START',
      });
      setValidationResult(res);
    } catch (err: any) {
      setValidationResult({
        is_valid: false,
        reason: 'API_ERROR',
        message: err?.response?.data?.detail?.message || err?.message || 'Validation request failed',
        cycle_path: null,
      });
    } finally {
      setIsValidating(false);
    }
  };

  // Node position lookup map
  const nodePositionMap = useMemo(() => {
    const map: Record<string, LayoutNode> = {};
    layoutNodes.forEach((n) => {
      map[n.id] = n;
    });
    return map;
  }, [layoutNodes]);

  // Loading State
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 bg-slate-900 border border-slate-800 rounded-xl text-slate-300">
        <RefreshCw className="w-10 h-10 animate-spin text-emerald-500 mb-4" />
        <h3 className="text-lg font-semibold text-slate-100">Compiling Precedence Network...</h3>
        <p className="text-sm text-slate-400 mt-1">Executing Kahn's topological sort and CPM-PL analysis</p>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="p-6 bg-red-950/40 border border-red-800 rounded-xl text-red-200">
        <div className="flex items-center gap-3 mb-2">
          <AlertTriangle className="w-6 h-6 text-red-400" />
          <h3 className="text-lg font-bold">Failed to Load Precedence Graph</h3>
        </div>
        <p className="text-sm">{error}</p>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="mt-4 px-4 py-2 bg-red-800 hover:bg-red-700 text-white rounded-lg text-sm font-medium flex items-center gap-2 transition"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      {/* 1. Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-950 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-950/60 border border-emerald-700/50 rounded-lg text-emerald-400">
            <GitCommit className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-100">Infrastructure Precedence Network</h2>
              {data.is_acyclic ? (
                <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300 rounded-full flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" /> Acyclic DAG
                </span>
              ) : (
                <span className="px-2 py-0.5 text-xs font-semibold bg-red-950 border border-red-800 text-red-300 rounded-full flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Cyclic Dependency Detected
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Kahn Topological Sort &amp; Critical Path Method with Positive Lag (CPM-PL)
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Seed Standard 5-Project Benchmark Scenario */}
          <button
            onClick={handleSeedScenario}
            disabled={isSeeding}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-900/80 hover:bg-indigo-850 border border-indigo-700 text-indigo-200 transition flex items-center gap-1.5 shadow disabled:opacity-50"
            title="Seed standard 5-project precedence benchmark (Makespan = 12d, Critical Path: A -> B -> E)"
          >
            <GitCommit className="w-3.5 h-3.5 text-indigo-400" />
            {isSeeding ? 'Seeding...' : 'Load Standard Scenario'}
          </button>

          {/* Highlight Critical Toggle */}
          <button
            onClick={() => setHighlightCriticalOnly((prev) => !prev)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition flex items-center gap-1.5 ${
              highlightCriticalOnly
                ? 'bg-red-950 border-red-700 text-red-200'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
            }`}
            title="Toggle critical path visibility emphasis"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
            Critical Path Only
          </button>

          {/* Dry Run Validate Button */}
          <button
            onClick={() => setIsValidateModalOpen(true)}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-800 hover:bg-emerald-700 text-white transition flex items-center gap-1.5 shadow"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Test Link (Dry-Run)
          </button>

          {/* Zoom controls */}
          <div className="flex items-center bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
            <button
              onClick={handleZoomIn}
              className="p-1.5 hover:bg-slate-700 text-slate-300 transition"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <span className="px-2 text-xs font-mono text-slate-400 border-x border-slate-700">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomOut}
              className="p-1.5 hover:bg-slate-700 text-slate-300 transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleReset}
              className="p-1.5 hover:bg-slate-700 text-slate-300 transition border-l border-slate-700"
              title="Reset View"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-1.5 bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg transition"
              title="Refresh Graph"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 2. KPI Summary Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 px-4 py-2.5 bg-slate-950/70 border-b border-slate-800 text-xs">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-sky-400" />
          <span className="text-slate-400">Total Projects:</span>
          <span className="font-semibold text-slate-200">{data.total_projects}</span>
        </div>
        <div className="flex items-center gap-2">
          <ArrowRight className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-400">Dependencies:</span>
          <span className="font-semibold text-slate-200">{data.total_dependencies}</span>
        </div>
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-400" />
          <span className="text-slate-400">Critical Projects:</span>
          <span className="font-semibold text-red-300">{data.critical_path_project_ids.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" />
          <span className="text-slate-400">Makespan:</span>
          <span className="font-semibold text-amber-300">
            {data.project_makespan_periods} Periods ({data.project_makespan_periods * periodDays}d)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-indigo-400" />
          <span className="text-slate-400">Period Duration:</span>
          {onPeriodDaysChange ? (
            <select
              value={periodDays}
              onChange={(e) => onPeriodDaysChange(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded px-1.5 py-0.5"
            >
              <option value={15}>15 days</option>
              <option value={30}>30 days</option>
              <option value={60}>60 days</option>
            </select>
          ) : (
            <span className="font-semibold text-slate-200">{periodDays} days</span>
          )}
        </div>
      </div>

      {/* Cyclic Warning Alert if graph has cycles */}
      {!data.is_acyclic && data.cycle_path && (
        <div className="p-3 bg-red-950/70 border-b border-red-800 text-red-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>
              <strong>Graph Cycle Invalidation:</strong> Circular dependency path: {' '}
              <code className="bg-red-900/60 px-2 py-0.5 rounded font-mono text-white">
                {data.cycle_path.join(' → ')}
              </code>
            </span>
          </div>
        </div>
      )}

      {/* 3. Main Graph Canvas Area */}
      <div className="relative flex-1 min-h-[560px] bg-slate-950 overflow-hidden select-none">
        {data.nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[500px] text-slate-400 p-8 space-y-4">
            <GitCommit className="w-12 h-12 text-indigo-400 animate-pulse" />
            <div className="text-center">
              <h4 className="text-base font-semibold text-slate-200">No Projects in Precedence Network</h4>
              <p className="text-xs text-slate-500 mt-1 max-w-md text-center">
                Recovery capital projects and precedence dependencies have not been configured yet.
                Load the standard 5-project benchmark network to visualize CPM-PL scheduling and run dry-run cycle tests.
              </p>
            </div>
            <button
              type="button"
              onClick={handleSeedScenario}
              disabled={isSeeding}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs shadow-lg transition flex items-center gap-2 disabled:opacity-50"
            >
              <PlusCircle className="w-4 h-4" />
              {isSeeding ? 'Seeding Scenario...' : 'Load Standard 5-Project Scenario'}
            </button>
          </div>
        ) : (
          <svg
            id="graph-canvas"
            ref={svgRef}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            style={{ minHeight: '560px' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            <defs>
              {/* Directed Arrow Markers */}
              <marker
                id="arrow-default"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
              </marker>

              <marker
                id="arrow-critical"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
              </marker>

              {/* Node Drop Shadows */}
              <filter id="node-glow-critical" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#ef4444" floodOpacity="0.4" />
              </filter>
              <filter id="node-glow-default" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0f172a" floodOpacity="0.8" />
              </filter>
            </defs>

            {/* Transform Group for Pan & Zoom */}
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              {/* Layer 1: Edges */}
              {layoutEdges.map((edge) => {
                const pred = nodePositionMap[edge.predecessor_project_id];
                const succ = nodePositionMap[edge.successor_project_id];
                if (!pred || !succ) return null;

                const startX = pred.x + pred.width;
                const startY = pred.y + pred.height / 2;
                const endX = succ.x;
                const endY = succ.y + succ.height / 2;

                // Bezier control points
                const dx = Math.max(Math.abs(endX - startX) * 0.5, 40);
                const pathD = `M ${startX} ${startY} C ${startX + dx} ${startY}, ${endX - dx} ${endY}, ${endX} ${endY}`;

                const isCritEdge = edge.is_critical_path;
                const isDimmed = highlightCriticalOnly && !isCritEdge;

                return (
                  <g key={edge.id} className="transition-opacity duration-200" opacity={isDimmed ? 0.15 : 1}>
                    <path
                      d={pathD}
                      fill="none"
                      stroke={isCritEdge ? '#ef4444' : '#475569'}
                      strokeWidth={isCritEdge ? 3 : 1.75}
                      strokeDasharray={isCritEdge ? undefined : edge.lag_days > 0 ? '4 3' : undefined}
                      markerEnd={isCritEdge ? 'url(#arrow-critical)' : 'url(#arrow-default)'}
                    />

                    {/* Lag badge if present */}
                    {edge.lag_days > 0 && (
                      <g transform={`translate(${(startX + endX) / 2}, ${(startY + endY) / 2 - 8})`}>
                        <rect
                          x="-24"
                          y="-8"
                          width="48"
                          height="16"
                          rx="4"
                          fill="#1e293b"
                          stroke={isCritEdge ? '#ef4444' : '#64748b'}
                          strokeWidth="1"
                        />
                        <text
                          x="0"
                          y="4"
                          textAnchor="middle"
                          fontSize="9"
                          fill={isCritEdge ? '#fca5a5' : '#94a3b8'}
                          fontFamily="monospace"
                        >
                          +{edge.lag_days}d
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* Layer 2: Nodes */}
              {layoutNodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                const isCritical = node.cpm?.is_critical ?? false;
                const isDimmed = highlightCriticalOnly && !isCritical;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={() => setSelectedNodeId(node.id)}
                    className="cursor-pointer"
                    opacity={isDimmed ? 0.2 : 1}
                  >
                    {/* Background Rect */}
                    <rect
                      width={node.width}
                      height={node.height}
                      rx="8"
                      fill={isCritical ? '#1c1917' : '#0f172a'}
                      stroke={
                        isSelected
                          ? '#38bdf8'
                          : isCritical
                          ? '#ef4444'
                          : '#334155'
                      }
                      strokeWidth={isSelected ? 2.5 : isCritical ? 2 : 1.5}
                      filter={isCritical ? 'url(#node-glow-critical)' : 'url(#node-glow-default)'}
                      className="transition-colors duration-150"
                    />

                    {/* Header Strip with Sector & Priority */}
                    <rect
                      x="0"
                      y="0"
                      width={node.width}
                      height="24"
                      rx="8"
                      fill={isCritical ? '#450a0a' : '#1e293b'}
                    />
                    {/* Fix rounded bottom for header strip */}
                    <rect
                      x="0"
                      y="16"
                      width={node.width}
                      height="8"
                      fill={isCritical ? '#450a0a' : '#1e293b'}
                    />

                    {/* Project Code */}
                    <text
                      x="10"
                      y="16"
                      fontSize="11"
                      fontWeight="bold"
                      fill={isCritical ? '#fca5a5' : '#e2e8f0'}
                      fontFamily="monospace"
                    >
                      {node.project_code}
                    </text>

                    {/* Sector Badge */}
                    <text
                      x={node.width - 10}
                      y="16"
                      textAnchor="end"
                      fontSize="9"
                      fontWeight="bold"
                      fill={isCritical ? '#f87171' : '#94a3b8'}
                    >
                      {node.sector}
                    </text>

                    {/* Title */}
                    <text
                      x="10"
                      y="42"
                      fontSize="11"
                      fontWeight="600"
                      fill="#f8fafc"
                      width={node.width - 20}
                    >
                      {node.title.length > 24 ? `${node.title.substring(0, 22)}...` : node.title}
                    </text>

                    {/* CPM Bounds: ES, EF, Duration */}
                    {node.cpm && (
                      <g transform="translate(10, 60)">
                        <text x="0" y="0" fontSize="9.5" fill="#94a3b8">
                          ES: <tspan fill="#e2e8f0" fontWeight="bold">P{node.cpm.early_start}</tspan> | EF:{' '}
                          <tspan fill="#e2e8f0" fontWeight="bold">P{node.cpm.early_finish}</tspan>
                        </text>
                        <text x="0" y="16" fontSize="9.5" fill="#94a3b8">
                          Duration:{' '}
                          <tspan fill="#e2e8f0" fontWeight="bold">
                            {node.cpm.duration_periods}P ({node.estimated_duration_days}d)
                          </tspan>
                        </text>

                        {/* Float Badge */}
                        <g transform={`translate(${node.width - 80}, -2)`}>
                          <rect
                            x="0"
                            y="0"
                            width="62"
                            height="18"
                            rx="4"
                            fill={node.cpm.is_critical ? '#7f1d1d' : '#1e293b'}
                            stroke={node.cpm.is_critical ? '#ef4444' : '#475569'}
                            strokeWidth="1"
                          />
                          <text
                            x="31"
                            y="12"
                            textAnchor="middle"
                            fontSize="8.5"
                            fontWeight="bold"
                            fill={node.cpm.is_critical ? '#fef2f2' : '#cbd5e1'}
                          >
                            {node.cpm.is_critical ? 'CRITICAL' : `Float: ${node.cpm.total_float}P`}
                          </text>
                        </g>
                      </g>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
        )}

        {/* 4. Selected Node Inspector Drawer (Right Side) */}
        {selectedNode && (
          <div className="absolute top-4 right-4 w-80 bg-slate-900/95 border border-slate-700/80 rounded-xl p-4 shadow-2xl backdrop-blur-md text-xs z-10 animate-in fade-in slide-in-from-right-4 duration-150">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-sm text-slate-100">{selectedNode.project_code}</span>
                {selectedNode.cpm?.is_critical && (
                  <span className="px-1.5 py-0.5 text-[10px] font-bold bg-red-950 border border-red-700 text-red-300 rounded">
                    CRITICAL
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedNodeId(null)}
                className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <h4 className="text-sm font-semibold text-slate-200 mb-2">{selectedNode.title}</h4>

            <div className="space-y-2 mb-3">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Sector:</span>
                <span className="font-medium text-slate-200">{selectedNode.sector}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Priority Tier:</span>
                <span className="font-medium text-slate-200">{selectedNode.priority_tier}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Status:</span>
                <span className="font-medium text-slate-200">{selectedNode.status}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Duration:</span>
                <span className="font-medium text-slate-200">{selectedNode.estimated_duration_days} days</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Estimated Cost:</span>
                <span className="font-medium text-emerald-400">
                  ₹{selectedNode.estimated_cost.toLocaleString()}
                </span>
              </div>
            </div>

            {selectedNode.cpm && (
              <div className="mt-3 p-3 bg-slate-950/80 border border-slate-800 rounded-lg">
                <h5 className="font-bold text-slate-300 mb-2 flex items-center gap-1.5 text-[11px]">
                  <Clock className="w-3.5 h-3.5 text-amber-400" /> CPM-PL Schedule Bounds
                </h5>
                <div className="grid grid-cols-2 gap-2 text-[10.5px]">
                  <div>
                    <span className="text-slate-400">Early Start:</span>{' '}
                    <strong className="text-slate-200">Period {selectedNode.cpm.early_start}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Early Finish:</span>{' '}
                    <strong className="text-slate-200">Period {selectedNode.cpm.early_finish}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Late Start:</span>{' '}
                    <strong className="text-slate-200">Period {selectedNode.cpm.late_start}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Late Finish:</span>{' '}
                    <strong className="text-slate-200">Period {selectedNode.cpm.late_finish}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Total Float:</span>{' '}
                    <strong className={selectedNode.cpm.total_float === 0 ? 'text-red-400' : 'text-emerald-400'}>
                      {selectedNode.cpm.total_float} periods
                    </strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Free Float:</span>{' '}
                    <strong className="text-slate-200">{selectedNode.cpm.free_float} periods</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 5. Dry-Run Dependency Edge Validation Modal */}
      {isValidateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between p-4 bg-slate-950 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-emerald-950 border border-emerald-700/60 rounded-lg text-emerald-400">
                  <GitCommit className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Dry-Run Dependency Link Validator</h3>
                  <p className="text-xs text-slate-400">Test candidate edges for cycle creation without database writes</p>
                </div>
              </div>
              <button
                onClick={() => setIsValidateModalOpen(false)}
                className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {data.nodes.length < 2 ? (
              <div className="p-6 text-center space-y-4">
                <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto animate-bounce" />
                <div>
                  <h4 className="text-sm font-bold text-slate-200">Insufficient Precedence Nodes</h4>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                    At least 2 recovery projects are required to dry-run candidate dependency links and test Kahn cycle detection.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    await handleSeedScenario();
                  }}
                  disabled={isSeeding}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs transition flex items-center justify-center gap-2 mx-auto disabled:opacity-50"
                >
                  <PlusCircle className="w-4 h-4" />
                  {isSeeding ? 'Seeding 5 Projects...' : 'Load Standard 5-Project Scenario'}
                </button>
              </div>
            ) : (
            <form onSubmit={handleValidateCandidate} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Predecessor Project (Must complete first):</label>
                <select
                  value={candidatePredId}
                  onChange={(e) => setCandidatePredId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  {data.nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.project_code} — {n.title} ({n.sector})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Successor Project (Depends on predecessor):</label>
                <select
                  value={candidateSuccId}
                  onChange={(e) => setCandidateSuccId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  {data.nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.project_code} — {n.title} ({n.sector})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Lag (Calendar Days):</label>
                <input
                  type="number"
                  min="0"
                  max="365"
                  value={candidateLag}
                  onChange={(e) => setCandidateLag(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Positive calendar lag before successor can begin after predecessor finish.
                </p>
              </div>

              {/* Validation Result Box */}
              {validationResult && (
                <div
                  className={`p-3 rounded-lg border text-xs ${
                    validationResult.is_valid
                      ? 'bg-emerald-950/50 border-emerald-800 text-emerald-200'
                      : 'bg-red-950/60 border-red-800 text-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2 font-bold mb-1">
                    {validationResult.is_valid ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-emerald-400" /> Candidate Link is Valid
                      </>
                    ) : (
                      <>
                        <XCircle className="w-4 h-4 text-red-400" /> Dependency Rejected:{' '}
                        {validationResult.reason || 'Invalid'}
                      </>
                    )}
                  </div>
                  <p>{validationResult.message}</p>

                  {validationResult.cycle_path && (
                    <div className="mt-2 pt-2 border-t border-red-800/60">
                      <span className="font-semibold text-red-300">Detected Cycle Path:</span>
                      <div className="mt-1 font-mono text-[11px] bg-red-900/40 p-1.5 rounded border border-red-800 text-red-100 break-all">
                        {validationResult.cycle_path.join(' → ')}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsValidateModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={isValidating || candidatePredId === candidateSuccId}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg font-semibold flex items-center gap-2 transition"
                >
                  {isValidating && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Run Dry-Run Cycle Check
                </button>
              </div>
            </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
