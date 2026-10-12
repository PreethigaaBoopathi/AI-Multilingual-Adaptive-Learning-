import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { 
  ZoomIn, ZoomOut, Maximize2, RotateCcw, 
  Layers, Filter, Search, BookOpen, 
  Presentation, Video, ArrowRight, Sparkles,
  HelpCircle, Eye, Move, CheckCircle2, Link2,
  MousePointer
} from 'lucide-react';

const TOPIC_PALETTES = [
  { bg: 'bg-indigo-500/20', border: 'border-indigo-400', text: 'text-indigo-300', fill: '#818cf8', glow: 'rgba(129, 140, 248, 0.5)' },
  { bg: 'bg-emerald-500/20', border: 'border-emerald-400', text: 'text-emerald-300', fill: '#34d399', glow: 'rgba(52, 211, 153, 0.5)' },
  { bg: 'bg-amber-500/20', border: 'border-amber-400', text: 'text-amber-300', fill: '#fbbf24', glow: 'rgba(251, 191, 36, 0.5)' },
  { bg: 'bg-cyan-500/20', border: 'border-cyan-400', text: 'text-cyan-300', fill: '#38bdf8', glow: 'rgba(56, 189, 248, 0.5)' },
  { bg: 'bg-rose-500/20', border: 'border-rose-400', text: 'text-rose-300', fill: '#fb7185', glow: 'rgba(251, 113, 133, 0.5)' },
  { bg: 'bg-purple-500/20', border: 'border-purple-400', text: 'text-purple-300', fill: '#c084fc', glow: 'rgba(192, 132, 252, 0.5)' },
];

export const ConceptGraphViewer = ({ 
  graph, 
  selectedConceptId, 
  onSelectConcept, 
  isDark = true 
}) => {
  const containerRef = useRef(null);
  const [zoom, setZoom] = useState(0.85);
  const [pan, setPan] = useState({ x: 40, y: 30 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [filterType, setFilterType] = useState('all'); // 'all', 'prereq', 'related'
  const [selectedTopic, setSelectedTopic] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Topic Color Mapping
  const topicColorMap = useMemo(() => {
    const map = {};
    if (graph?.topics) {
      graph.topics.forEach((t, idx) => {
        map[t.name] = TOPIC_PALETTES[idx % TOPIC_PALETTES.length];
      });
    }
    return map;
  }, [graph?.topics]);

  // Generously Spaced 2D Hierarchy Layout Engine
  const { positions: nodePositions, boundingBox, stages } = useMemo(() => {
    if (!graph?.nodes || graph.nodes.length === 0) {
      return { positions: {}, boundingBox: { minX: 0, maxX: 900, minY: 0, maxY: 600, width: 900, height: 600 }, stages: [] };
    }
    
    const nodes = graph.nodes;
    const edges = graph.edges || [];
    const positions = {};

    // 1. Calculate prerequisite in-degrees & topological depth
    const inDegree = {};
    const outDegree = {};
    nodes.forEach(n => {
      inDegree[n.id] = 0;
      outDegree[n.id] = 0;
    });

    edges.forEach(e => {
      const src = e.source || e.source_concept_id;
      const tgt = e.target || e.target_concept_id;
      if (e.relationship_type === 'prerequisite') {
        if (inDegree[tgt] !== undefined) inDegree[tgt] += 1;
        if (outDegree[src] !== undefined) outDegree[src] += 1;
      }
    });

    const depth = {};
    nodes.forEach(n => {
      depth[n.id] = 0;
    });

    for (let pass = 0; pass < 6; pass++) {
      edges.forEach(e => {
        const src = e.source || e.source_concept_id;
        const tgt = e.target || e.target_concept_id;
        if (e.relationship_type === 'prerequisite') {
          if (depth[tgt] <= depth[src]) {
            depth[tgt] = depth[src] + 1;
          }
        }
      });
    }

    // 2. Group nodes into structured stages / tiers
    const stageGroups = {};
    nodes.forEach(n => {
      const d = Math.min(depth[n.id] || 0, 3);
      if (!stageGroups[d]) stageGroups[d] = [];
      stageGroups[d].push(n);
    });

    const stageKeys = Object.keys(stageGroups).map(Number).sort((a, b) => a - b);

    // Spacing Configuration: Generous clear gutters for effortless readability
    const CARD_WIDTH = 230;
    const CARD_HEIGHT = 82;
    const COL_SPACING = 350;     // Clear horizontal gutter between cards
    const ROW_SPACING = 175;     // Clear vertical space between rows for curves & arrows
    const STAGE_GAP_Y = 95;      // Clear vertical gap between stages
    const MAX_NODES_PER_ROW = 3; // Maximum 3 cards per row

    let currentY = 50;
    let maxOverallX = 900;
    const computedStages = [];

    stageKeys.forEach((stageKey) => {
      const stageNodes = stageGroups[stageKey];
      const stageName = stageKey === 0 
        ? "Stage 1: Foundational Concepts" 
        : stageKey === 1 
          ? "Stage 2: Core Mechanisms" 
          : `Stage ${stageKey + 1}: Advanced & Applied Concepts`;

      const numRows = Math.ceil(stageNodes.length / MAX_NODES_PER_ROW);

      // Top edge of the stage container
      const stageBoxTop = currentY;

      // Header is placed at stageBoxTop + 16, height 30 (spans y = stageBoxTop + 16 to stageBoxTop + 46)
      const headerY = stageBoxTop + 16;
      const HEADER_HEIGHT = 30;
      const GAP_AFTER_HEADER = 32; // Generous clear gap between bottom of header pill and top of node cards

      // First row of node cards:
      // Node center posY is CARD_HEIGHT / 2 (41px) below the top edge of the card
      const firstRowCenterY = headerY + HEADER_HEIGHT + GAP_AFTER_HEADER + CARD_HEIGHT / 2;

      let rowCenterY = firstRowCenterY;

      for (let r = 0; r < numRows; r++) {
        const rowNodes = stageNodes.slice(r * MAX_NODES_PER_ROW, (r + 1) * MAX_NODES_PER_ROW);
        const rowWidth = (rowNodes.length - 1) * COL_SPACING;
        // Center the row nicely relative to canvas midpoint
        const startX = Math.max(180, 520 - rowWidth / 2);

        rowNodes.forEach((node, colIdx) => {
          const posX = startX + colIdx * COL_SPACING;
          const posY = rowCenterY;

          positions[node.id] = {
            x: posX,
            y: posY,
            stage: stageKey,
            depth: depth[node.id] || 0,
            inDegree: inDegree[node.id] || 0,
            outDegree: outDegree[node.id] || 0
          };

          if (posX + CARD_WIDTH / 2 > maxOverallX) {
            maxOverallX = posX + CARD_WIDTH / 2;
          }
        });

        rowCenterY += ROW_SPACING;
      }

      const lastRowCenterY = rowCenterY - ROW_SPACING;
      const stageBoxBottom = lastRowCenterY + CARD_HEIGHT / 2 + 32;

      computedStages.push({
        stage: stageKey,
        name: stageName,
        startY: stageBoxTop,
        endY: stageBoxBottom,
        headerY: headerY,
        count: stageNodes.length
      });

      // Extra clearance between distinct stages
      currentY = stageBoxBottom + STAGE_GAP_Y;
    });

    // Compute exact bounding box
    const allX = Object.values(positions).map(p => p.x);
    const allY = Object.values(positions).map(p => p.y);
    const minStageY = computedStages.length > 0 ? computedStages[0].startY : 30;
    const maxStageY = computedStages.length > 0 ? computedStages[computedStages.length - 1].endY : 600;

    const minX = Math.min(...allX, 100) - CARD_WIDTH / 2 - 50;
    const maxX = Math.max(...allX, 900) + CARD_WIDTH / 2 + 50;
    const minY = Math.min(minStageY, ...allY) - 30;
    const maxY = Math.max(maxStageY, ...allY) + 30;

    return {
      positions,
      boundingBox: {
        minX,
        maxX,
        minY,
        maxY,
        width: maxX - minX,
        height: maxY - minY
      },
      stages: computedStages
    };
  }, [graph]);

  // Fit view automatically to center all nodes, maintaining comfortable minimum zoom
  const fitToScreen = useCallback(() => {
    if (!containerRef.current || !boundingBox || boundingBox.width === 0) return;
    const containerWidth = containerRef.current.clientWidth || 900;
    const containerHeight = containerRef.current.clientHeight || 640;

    const scaleX = (containerWidth - 60) / boundingBox.width;
    const scaleY = (containerHeight - 60) / boundingBox.height;
    // Keep comfortable zoom so text is always sharp and large (at least 76%)
    const optimalZoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.76), 1.0);

    const centerX = (boundingBox.minX + boundingBox.maxX) / 2;
    const centerY = (boundingBox.minY + boundingBox.maxY) / 2;

    setZoom(optimalZoom);
    setPan({
      x: containerWidth / 2 - centerX * optimalZoom,
      y: containerHeight / 2 - centerY * optimalZoom
    });
  }, [boundingBox]);

  // Initial fit on graph load
  useEffect(() => {
    if (graph?.nodes && graph.nodes.length > 0) {
      const timer = setTimeout(fitToScreen, 100);
      return () => clearTimeout(timer);
    }
  }, [graph, fitToScreen]);

  // Filtered Edges
  const visibleEdges = useMemo(() => {
    if (!graph?.edges) return [];
    return graph.edges.filter(e => {
      if (filterType === 'prereq' && e.relationship_type !== 'prerequisite') return false;
      if (filterType === 'related' && e.relationship_type === 'prerequisite') return false;
      if (selectedTopic !== 'all') {
        const srcNode = graph.nodes.find(n => n.id === (e.source || e.source_concept_id));
        const tgtNode = graph.nodes.find(n => n.id === (e.target || e.target_concept_id));
        if (srcNode?.topic !== selectedTopic && tgtNode?.topic !== selectedTopic) return false;
      }
      return true;
    });
  }, [graph, filterType, selectedTopic]);

  // Filtered Nodes
  const visibleNodes = useMemo(() => {
    if (!graph?.nodes) return [];
    return graph.nodes.filter(n => {
      if (selectedTopic !== 'all' && n.topic !== selectedTopic) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesName = n.name.toLowerCase().includes(q);
        const matchesTopic = n.topic.toLowerCase().includes(q);
        if (!matchesName && !matchesTopic) return false;
      }
      return true;
    });
  }, [graph, selectedTopic, searchQuery]);

  // Native Non-Passive Wheel Event Listener
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleWheelNative = (e) => {
      e.preventDefault();
      e.stopPropagation();

      if (e.ctrlKey || e.metaKey) {
        // Zoom with Ctrl + Wheel or Trackpad Pinch
        const zoomFactor = e.deltaY > 0 ? 0.92 : 1.08;
        setZoom(prev => Math.min(Math.max(prev * zoomFactor, 0.40), 2.2));
      } else if (e.shiftKey) {
        // Horizontal Pan with Shift + Wheel
        setPan(p => ({ ...p, x: p.x - e.deltaY * 0.9 }));
      } else {
        // Natural Vertical Pan with regular Mouse Wheel
        setPan(p => ({ ...p, y: p.y - e.deltaY * 0.9 }));
      }
    };

    el.addEventListener('wheel', handleWheelNative, { passive: false });
    return () => {
      el.removeEventListener('wheel', handleWheelNative);
    };
  }, []);

  const handleMouseDown = (e) => {
    if (e.target.tagName === 'svg' || e.target.id === 'graph-canvas' || (e.target.tagName === 'rect' && e.target.getAttribute('fill')?.includes('url'))) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Center view on search match
  useEffect(() => {
    if (searchQuery && visibleNodes.length > 0) {
      const firstMatch = visibleNodes[0];
      const pos = nodePositions[firstMatch.id];
      if (pos && containerRef.current) {
        const w = containerRef.current.clientWidth || 900;
        const h = containerRef.current.clientHeight || 640;
        setPan({
          x: w / 2 - pos.x * zoom,
          y: h / 2 - pos.y * zoom
        });
      }
    }
  }, [searchQuery, visibleNodes, nodePositions, zoom]);

  // Helper to test if edge is highlighted
  const isEdgeHighlighted = (edge) => {
    const srcId = edge.source || edge.source_concept_id;
    const tgtId = edge.target || edge.target_concept_id;
    const activeId = selectedConceptId || hoveredNode?.id;
    if (hoveredEdge && (hoveredEdge.id === edge.id)) return true;
    if (!activeId) return false;
    return srcId === activeId || tgtId === activeId;
  };

  // Check if any concept is currently selected/hovered to dim background
  const hasActiveSelection = Boolean(selectedConceptId || hoveredNode);

  // Helper to generate elegant curved Bézier paths
  const getEdgePath = (srcPos, tgtPos, edgeIndex = 0) => {
    const dx = tgtPos.x - srcPos.x;
    const dy = tgtPos.y - srcPos.y;

    if (Math.abs(dy) < 40) {
      // Same Row connection: smooth arch below the cards
      const curveHeight = Math.min(55 + Math.abs(dx) * 0.12 + (edgeIndex % 2) * 14, 95);
      const startX = srcPos.x;
      const startY = srcPos.y + 41; // bottom center of card
      const endX = tgtPos.x;
      const endY = tgtPos.y + 41;   // bottom center of card
      const ctrlY = startY + curveHeight;

      return `M ${startX} ${startY} C ${startX} ${ctrlY}, ${endX} ${ctrlY}, ${endX} ${endY}`;
    } else if (dy > 0) {
      // Downward Flow (Prerequisite / Hierarchy)
      const startX = srcPos.x;
      const startY = srcPos.y + 41; // exit from bottom of source card
      const endX = tgtPos.x;
      const endY = tgtPos.y - 41;   // enter top of target card
      const midY = (startY + endY) / 2;
      return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
    } else {
      // Upward Flow
      const startX = srcPos.x;
      const startY = srcPos.y - 41; // exit top
      const endX = tgtPos.x;
      const endY = tgtPos.y + 41;   // enter bottom
      const midY = (startY + endY) / 2;
      return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
    }
  };

  // Split title into 2 clean lines if long
  const formatTitleLines = (name) => {
    if (!name) return ["Concept"];
    if (name.length <= 22) return [name];
    
    const words = name.split(' ');
    let line1 = '';
    let line2 = '';

    for (let w of words) {
      if ((line1 + ' ' + w).trim().length <= 22) {
        line1 = (line1 + ' ' + w).trim();
      } else {
        line2 = (line2 + ' ' + w).trim();
      }
    }

    if (line2.length > 24) {
      line2 = line2.substring(0, 22) + '...';
    }

    return line2 ? [line1, line2] : [line1];
  };

  return (
    <div className="relative w-full rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 flex flex-col select-none shadow-2xl">
      
      {/* Top Controls Header Bar */}
      <div className="w-full flex flex-wrap items-center justify-between gap-3 p-3.5 bg-slate-900 border-b border-slate-800 z-20 shadow-md">
        
        {/* Left: Filters & Search */}
        <div className="flex flex-wrap items-center gap-2.5">
          
          {/* Relationship Filter */}
          <div className="flex items-center space-x-1 bg-slate-800 p-1 rounded-xl border border-slate-700 text-xs">
            <button
              onClick={() => setFilterType('all')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                filterType === 'all' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
              }`}
            >
              All Links ({graph?.stats?.total_relationships || 0})
            </button>
            <button
              onClick={() => setFilterType('prereq')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all flex items-center space-x-1.5 ${
                filterType === 'prereq' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
              }`}
            >
              <ArrowRight className="w-3.5 h-3.5" />
              <span>Prerequisites ({graph?.stats?.total_prerequisites || 0})</span>
            </button>
            <button
              onClick={() => setFilterType('related')}
              className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                filterType === 'related' ? 'bg-cyan-600 text-white shadow-sm' : 'text-slate-300 hover:text-white'
              }`}
            >
              Related Only
            </button>
          </div>

          {/* Topic Filter */}
          {graph?.topics && graph.topics.length > 0 && (
            <select
              value={selectedTopic}
              onChange={(e) => setSelectedTopic(e.target.value)}
              className="bg-slate-800 text-white border border-slate-700 text-xs font-semibold rounded-xl px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 shadow-2xs"
            >
              <option value="all">All Topics ({graph.topics.length})</option>
              {graph.topics.map(t => (
                <option key={t.name} value={t.name}>{t.name} ({t.count})</option>
              ))}
            </select>
          )}

          {/* Search Concept */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search concepts..."
              className="pl-9 pr-3 py-1.5 text-xs bg-slate-800 border border-slate-700 text-white placeholder:text-slate-400 rounded-xl focus:outline-none focus:border-indigo-500 w-48 font-medium"
            />
          </div>

        </div>

        {/* Right: Zoom & Navigation Tools */}
        <div className="flex items-center space-x-2">
          
          <button
            onClick={fitToScreen}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold border border-indigo-400/50 flex items-center space-x-1.5 shadow-sm transition"
            title="Auto-Fit and Center All Concepts"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Fit Graph</span>
          </button>

          <div className="text-xs text-slate-200 font-mono font-bold hidden sm:block bg-slate-800 px-2.5 py-1.5 rounded-xl border border-slate-700">
            {Math.round(zoom * 100)}%
          </div>

          <button
            onClick={() => setZoom(z => Math.min(z + 0.15, 2.2))}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl border border-slate-700 transition shadow-2xs"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(z => Math.max(z - 0.15, 0.40))}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl border border-slate-700 transition shadow-2xs"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={fitToScreen}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl border border-slate-700 transition shadow-2xs"
            title="Center View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

      </div>

      {/* Main Interactive SVG Canvas Area */}
      <div 
        ref={containerRef}
        id="graph-canvas"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        className="w-full h-[640px] cursor-grab active:cursor-grabbing relative overflow-hidden bg-[#0a0f1d] select-none"
        style={{ overscrollBehavior: 'contain', touchAction: 'none' }}
      >
        <svg 
          className="w-full h-full"
          style={{ width: '100%', height: '100%' }}
        >
          <defs>
            {/* Prerequisite Direction Arrow Marker */}
            <marker
              id="prereq-arrow"
              viewBox="0 0 10 10"
              refX="10"
              refY="5"
              markerWidth="8"
              markerHeight="8"
              orient="auto"
            >
              <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#10b981" />
            </marker>

            {/* Related Concept Arrow Marker */}
            <marker
              id="related-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M 0 2 L 9 5 L 0 8 z" fill="#94a3b8" />
            </marker>

            {/* Highlighted Arrow Marker */}
            <marker
              id="highlight-arrow"
              viewBox="0 0 10 10"
              refX="10"
              refY="5"
              markerWidth="9"
              markerHeight="9"
              orient="auto"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#34d399" />
            </marker>

            {/* Card Drop Shadow Filter */}
            <filter id="node-card-shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#000000" floodOpacity="0.5" />
            </filter>

            {/* Background Grid Pattern */}
            <pattern id="graph-dot-grid" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1.3" fill="#475569" opacity="0.45" />
            </pattern>
          </defs>

          {/* Dot Grid Background */}
          <rect width="100%" height="100%" fill="url(#graph-dot-grid)" />

          {/* Transformed Graph Layer */}
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            
            {/* Stage / Tier Backdrop Containers */}
            {stages.map((stg) => {
              const labelWidth = Math.max(stg.name.length * 8.5 + 130, 260);
              return (
                <g key={stg.stage}>
                  <rect
                    x={boundingBox.minX - 10}
                    y={stg.startY}
                    width={boundingBox.width + 20}
                    height={stg.endY - stg.startY}
                    rx="18"
                    fill="#111827"
                    fillOpacity="0.75"
                    stroke="#334155"
                    strokeWidth="1.5"
                    strokeDasharray="6 4"
                  />
                  {/* Clean Prominent Stage Header Badge - Clearly positioned above all node cards */}
                  <rect
                    x={boundingBox.minX + 16}
                    y={stg.headerY}
                    width={labelWidth}
                    height="30"
                    rx="15"
                    fill="#1e293b"
                    stroke="#475569"
                    strokeWidth="1.2"
                  />
                  <text
                    x={boundingBox.minX + 32}
                    y={stg.headerY + 19}
                    fill="#e2e8f0"
                    fontSize="12"
                    fontWeight="800"
                    letterSpacing="0.8"
                    className="font-mono uppercase"
                  >
                    {stg.name} &bull; {stg.count} {stg.count === 1 ? 'Concept' : 'Concepts'}
                  </text>
                </g>
              );
            })}

            {/* 1. EDGES LAYER */}
            {visibleEdges.map((edge, edgeIdx) => {
              const srcId = edge.source || edge.source_concept_id;
              const tgtId = edge.target || edge.target_concept_id;
              const srcPos = nodePositions[srcId];
              const tgtPos = nodePositions[tgtId];
              if (!srcPos || !tgtPos) return null;

              const isHighlighted = isEdgeHighlighted(edge);
              const isPrereq = edge.relationship_type === 'prerequisite';
              const pathD = getEdgePath(srcPos, tgtPos, edgeIdx);

              // Midpoint for badge on hover
              const midX = (srcPos.x + tgtPos.x) / 2;
              const isSameRow = Math.abs(tgtPos.y - srcPos.y) < 40;
              const midY = isSameRow ? srcPos.y + 65 : (srcPos.y + tgtPos.y) / 2;

              // Opacity logic: if something is hovered/selected, dim unrelated lines
              const edgeOpacity = isHighlighted 
                ? 1.0 
                : (hasActiveSelection ? 0.15 : (isPrereq ? 0.90 : 0.45));

              const isEdgeHovered = hoveredEdge?.id === edge.id;

              return (
                <g 
                  key={edge.id || `${srcId}-${tgtId}-${edgeIdx}`}
                  className="transition-all duration-200 cursor-pointer"
                  onMouseEnter={() => setHoveredEdge(edge)}
                  onMouseLeave={() => setHoveredEdge(null)}
                >
                  {/* Invisible wide hitbox for easy mouse hover */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke="transparent"
                    strokeWidth="24"
                  />

                  {/* Outer glow line on highlight */}
                  {isHighlighted && (
                    <path
                      d={pathD}
                      fill="none"
                      stroke={isPrereq ? '#10b981' : '#38bdf8'}
                      strokeWidth="7"
                      strokeOpacity="0.45"
                      className="animate-pulse"
                    />
                  )}

                  {/* Main visible connection line */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke={
                      isHighlighted 
                        ? (isPrereq ? '#34d399' : '#38bdf8') 
                        : (isPrereq ? '#10b981' : '#64748b')
                    }
                    strokeWidth={isHighlighted ? 3.6 : (isPrereq ? 2.5 : 1.6)}
                    strokeDasharray={isPrereq ? 'none' : '5 4'}
                    markerEnd={isHighlighted ? 'url(#highlight-arrow)' : (isPrereq ? 'url(#prereq-arrow)' : 'url(#related-arrow)')}
                    opacity={edgeOpacity}
                  />

                  {/* Relationship Badge only when THIS SPECIFIC EDGE is hovered */}
                  {isEdgeHovered && (
                    <foreignObject
                      x={midX - 75}
                      y={midY - 14}
                      width="150"
                      height="30"
                      className="overflow-visible pointer-events-none z-50"
                    >
                      <div className="flex items-center justify-center">
                        <span className={`text-xs font-black px-3 py-1 rounded-full uppercase tracking-wider shadow-2xl border-2 ${
                          isPrereq 
                            ? 'bg-emerald-600 text-white border-emerald-300' 
                            : 'bg-cyan-600 text-white border-cyan-300'
                        }`}>
                          {isPrereq ? '→ Prerequisite' : edge.relationship_type}
                        </span>
                      </div>
                    </foreignObject>
                  )}
                </g>
              );
            })}

            {/* 2. NODES LAYER */}
            {visibleNodes.map((node) => {
              const pos = nodePositions[node.id] || { x: 400, y: 300, inDegree: 0 };
              const isSelected = selectedConceptId === node.id;
              const isHovered = hoveredNode?.id === node.id;
              const palette = topicColorMap[node.topic] || TOPIC_PALETTES[0];

              // Check source modalities
              const hasPDF = node.sources?.some(s => s.source_type === 'pdf') || node.source_types?.includes('pdf');
              const hasPPT = node.sources?.some(s => s.source_type === 'presentation') || node.source_types?.includes('presentation');
              const hasVideo = node.sources?.some(s => s.source_type === 'video') || node.source_types?.includes('video');

              const isRoot = pos.inDegree === 0;
              const titleLines = formatTitleLines(node.name);

              // Dim non-connected nodes when something is actively hovered/selected
              const isConnectedToActive = isSelected || isHovered || (
                hasActiveSelection && visibleEdges.some(e => 
                  ((e.source === node.id || e.source_concept_id === node.id) && (e.target === (selectedConceptId || hoveredNode?.id) || e.target_concept_id === (selectedConceptId || hoveredNode?.id))) ||
                  ((e.target === node.id || e.target_concept_id === node.id) && (e.source === (selectedConceptId || hoveredNode?.id) || e.source_concept_id === (selectedConceptId || hoveredNode?.id)))
                )
              );

              const nodeOpacity = hasActiveSelection && !isConnectedToActive ? 0.35 : 1.0;

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectConcept(node);
                  }}
                  onMouseEnter={() => setHoveredNode(node)}
                  onMouseLeave={() => setHoveredNode(null)}
                  className="cursor-pointer group select-none transition-opacity duration-200"
                  opacity={nodeOpacity}
                >
                  {/* Glowing selection / hover ring */}
                  {(isSelected || isHovered) && (
                    <rect
                      x="-120"
                      y="-46"
                      width="240"
                      height="92"
                      rx="18"
                      fill="none"
                      stroke={palette.fill}
                      strokeWidth={isSelected ? "3.5" : "2"}
                      strokeOpacity={isSelected ? "1" : "0.6"}
                      style={{ filter: `drop-shadow(0 0 16px ${palette.glow})` }}
                    />
                  )}

                  {/* Main Node Card Body - Elevated & High Contrast */}
                  <rect
                    x="-115"
                    y="-41"
                    width="230"
                    height="82"
                    rx="15"
                    fill="#1e293b"
                    stroke={isSelected ? palette.fill : (isHovered ? '#cbd5e1' : '#475569')}
                    strokeWidth={isSelected ? '2.5' : '1.8'}
                    filter="url(#node-card-shadow)"
                    className="transition-colors duration-200"
                  />

                  {/* Topic color indicator strip on left */}
                  <rect
                    x="-115"
                    y="-41"
                    width="6.5"
                    height="82"
                    rx="3"
                    fill={palette.fill}
                  />

                  {/* Top Topic Tag Badge */}
                  <rect
                    x="-100"
                    y="-33"
                    width={Math.min(node.topic.length * 6.5 + 16, 160)}
                    height="17"
                    rx="8.5"
                    fill={palette.fill}
                    fillOpacity="0.25"
                    stroke={palette.fill}
                    strokeWidth="0.8"
                  />
                  <text
                    x="-92"
                    y="-21"
                    fill={palette.fill}
                    fontSize="9.5"
                    fontWeight="800"
                    className="font-mono uppercase tracking-wider"
                  >
                    {node.topic.length > 20 ? node.topic.substring(0, 18) + '...' : node.topic}
                  </text>

                  {/* Concept Name Text (Pure White, Bold 800, High Contrast) */}
                  {titleLines.length === 1 ? (
                    <text
                      x="-100"
                      y="3"
                      fill="#ffffff"
                      fontSize="13"
                      fontWeight="800"
                      className="font-sans"
                    >
                      {titleLines[0]}
                    </text>
                  ) : (
                    <>
                      <text
                        x="-100"
                        y="-2"
                        fill="#ffffff"
                        fontSize="12"
                        fontWeight="800"
                        className="font-sans"
                      >
                        {titleLines[0]}
                      </text>
                      <text
                        x="-100"
                        y="13"
                        fill="#ffffff"
                        fontSize="12"
                        fontWeight="800"
                        className="font-sans"
                      >
                        {titleLines[1]}
                      </text>
                    </>
                  )}

                  {/* Bottom Strip: Modalities + Hierarchy Status */}
                  <g transform="translate(-100, 24)">
                    
                    {/* Status Pill on Bottom Left */}
                    {isRoot ? (
                      <g>
                        <rect x="0" y="-3" width="76" height="16" rx="8" fill="#065f46" stroke="#10b981" strokeWidth="1" />
                        <text x="38" y="8" fill="#ecfdf5" fontSize="8.5" fontWeight="800" textAnchor="middle">
                          ✓ FOUNDATION
                        </text>
                      </g>
                    ) : (
                      <g>
                        <rect x="0" y="-3" width="76" height="16" rx="8" fill="#312e81" stroke="#818cf8" strokeWidth="1" />
                        <text x="38" y="8" fill="#e0e7ff" fontSize="8.5" fontWeight="800" textAnchor="middle">
                          🔗 {pos.inDegree} {pos.inDegree === 1 ? 'PREREQ' : 'PREREQS'}
                        </text>
                      </g>
                    )}

                    {/* Modality Badges on Bottom Right */}
                    <g transform="translate(132, 5)">
                      {hasPDF && (
                        <circle cx="8" cy="0" r="6" fill="#ef4444" stroke="#fca5a5" strokeWidth="0.8">
                          <title>PDF Textbook</title>
                        </circle>
                      )}
                      {hasPPT && (
                        <circle cx="23" cy="0" r="6" fill="#f59e0b" stroke="#fde68a" strokeWidth="0.8">
                          <title>PPT Slides</title>
                        </circle>
                      )}
                      {hasVideo && (
                        <circle cx="38" cy="0" r="6" fill="#8b5cf6" stroke="#ddd6fe" strokeWidth="0.8">
                          <title>Video Lecture</title>
                        </circle>
                      )}
                      {node.cross_modal_count > 1 && (
                        <g transform="translate(-32, -8)">
                          <rect x="0" y="0" width="28" height="15" rx="7.5" fill="#1e293b" stroke="#38bdf8" strokeWidth="1" />
                          <text x="14" y="11" fill="#38bdf8" fontSize="8" fontWeight="800" textAnchor="middle">
                            {node.cross_modal_count}M
                          </text>
                        </g>
                      )}
                    </g>

                  </g>
                </g>
              );
            })}

          </g>
        </svg>

        {/* Floating Navigation Hint Bar */}
        <div className="absolute bottom-3 left-4 pointer-events-none text-2xs font-mono text-slate-300 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700 shadow-md">
          <span>💡 Scroll to Pan &bull; Ctrl+Scroll to Zoom &bull; Drag to Move</span>
        </div>

      </div>

      {/* Bottom Informational Legend Strip */}
      <div className="w-full flex flex-wrap items-center justify-between gap-3 text-2xs text-slate-300 bg-slate-900/95 px-4 py-3 border-t border-slate-800">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <span className="w-4 h-1.5 bg-emerald-500 rounded-full inline-block"></span>
            <span className="text-emerald-400 font-bold">Solid Arrow (→): Prerequisite (Learn A before B)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-4 h-0.5 border-t-2 border-dashed border-slate-400 inline-block"></span>
            <span className="text-slate-300 font-semibold">Dashed Line: Related Concept</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded bg-emerald-900/80 text-emerald-300 text-3xs font-extrabold border border-emerald-600">✓ FOUNDATION</span>
            <span className="text-slate-400">No prerequisites</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <span className="font-semibold text-slate-400">Sources:</span>
          <span className="inline-flex items-center space-x-1.5 text-red-400 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 border border-red-300"></span>
            <span>📕 PDF</span>
          </span>
          <span className="inline-flex items-center space-x-1.5 text-amber-400 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-amber-300"></span>
            <span>📊 Slides</span>
          </span>
          <span className="inline-flex items-center space-x-1.5 text-purple-400 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 border border-purple-300"></span>
            <span>🎥 Video</span>
          </span>
        </div>
      </div>

    </div>
  );
};
