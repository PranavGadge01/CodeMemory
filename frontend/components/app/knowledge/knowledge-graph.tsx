"use client";

import * as React from "react";
import { Minus, Plus, RotateCcw, ExternalLink, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GraphEdge, GraphNode, KnowledgeGraph as KnowledgeGraphType, GraphNodeDetail } from "@/lib/types";

/** Node type colors - consistent with design tokens */
const TYPE_COLORS: Record<GraphNode["type"], string> = {
  Problem: "var(--color-accent)",
  Topic: "var(--color-graph-node-topic)",
  Concept: "var(--color-info)",
  Approach: "var(--color-accent)",
  Language: "var(--color-success)",
  Mistake: "var(--color-error)",
};

/** Type labels for legend */
const TYPE_LABELS: Record<GraphNode["type"], string> = {
  Problem: "Problem",
  Topic: "Topic",
  Concept: "Concept",
  Approach: "Approach",
  Language: "Language",
  Mistake: "Mistake",
};

const RELATIONSHIP_LABEL: Record<string, string> = {
  TAGGED_WITH: "tagged with",
  USES_APPROACH: "solved via",
  ENCOUNTERED_MISTAKE: "hit the mistake",
  SOLVED_IN: "submitted in",
  REQUIRES_CONCEPT: "rests on",
  RELATED_TO: "relates to",
};

const MIN_SCALE = 0.6;
const MAX_SCALE = 2.5;

const NODE_RADIUS: Record<GraphNode["type"], number> = {
  Problem: 20,
  Topic: 18,
  Concept: 16,
  Approach: 16,
  Language: 14,
  Mistake: 14,
};

/** Canvas size for the viewBox */
const SVG_SIZE = 600;
const CENTER = SVG_SIZE / 2;

/** Maximum label length before truncation */
const LABEL_MAX = 20;

/** View transformation state */
type View = {
  x: number;
  y: number;
  k: number;
};

/** Layout node with position and radius */
type LayoutNode = GraphNodeDetail & {
  x: number;
  y: number;
  radius: number;
  index: number;
};

/** Pan threshold in pixels */
const PAN_THRESHOLD = 3;

/**
 * Force-directed knowledge graph with improved layout.
 *
 * Uses a physics-based layout with proper spacing and readability.
 * Nodes are positioned with adequate separation, labels adapt to zoom,
 * and the graph is responsive and theme-aware.
 */
export function KnowledgeGraphPanel({
  graph,
  centerId,
  className,
  height = 500,
  _onNodeSelect,
}: {
  graph: KnowledgeGraphType;
  centerId: string;
  className?: string;
  height?: number;
  _onNodeSelect?: (nodeId: string) => void;
}) {
  const [selectedId, setSelectedId] = React.useState<string | null>(centerId);
  const [hoverId, setHoverId] = React.useState<string | null>(null);
  const [view, setView] = React.useState<View>({ x: 0, y: 0, k: 1 });
  const [panning, setPanning] = React.useState(false);

  const svgRef = React.useRef<SVGSVGElement>(null);
  const panRef = React.useRef<{ x: number; y: number; origin: View } | null>(null);
  const movedRef = React.useRef(false);

  const { nodes, edges, byId } = React.useMemo(
    () => layout(graph, centerId),
    [graph, centerId],
  );

  // Hover takes precedence over selection so brushing a node previews its
  // neighbourhood without committing to it.
  const focusId = hoverId ?? selectedId;

  const focusNeighbors = React.useMemo(
    () => neighborsOf(graph, focusId),
    [graph, focusId],
  );

  const selected = selectedId ? (byId.get(selectedId) ?? null) : null;

  const zoomBy = React.useCallback((factor: number) => {
    setView((current) => zoomAt(current, { x: CENTER, y: CENTER }, factor));
  }, []);

  const reset = React.useCallback(() => {
    setView({ x: 0, y: 0, k: 1 });
    setSelectedId(centerId);
  }, [centerId]);

  // Fit the graph to view - zoom out to fit all nodes
  const fitToView = React.useCallback(() => {
    if (nodes.length === 0) return;

    // Calculate bounding box
    const minX = Math.min(...nodes.map(n => n.x - n.radius));
    const maxX = Math.max(...nodes.map(n => n.x + n.radius));
    const minY = Math.min(...nodes.map(n => n.y - n.radius));
    const maxY = Math.max(...nodes.map(n => n.y + n.radius));

    const width = maxX - minX;
    const height = maxY - minY;
    const scale = Math.min(CENTER * 2 / Math.max(width, height), MAX_SCALE);
    const focusX = (minX + maxX) / 2;
    const focusY = (minY + maxY) / 2;

    setView({
      x: CENTER - focusX * scale,
      y: CENTER - focusY * scale,
      k: scale,
    });
    setSelectedId(centerId);
  }, [nodes, centerId]);

  // Gentle focus: slide the chosen node to the middle at whatever zoom the
  // user is on. Done in the handler rather than an effect so it never fights
  // a pan, and never moves the graph for an unrelated render.
  const focusNode = React.useCallback(
    (id: string) => {
      const node = byId.get(id);
      if (!node) return;
      setView((current) => ({
        ...current,
        x: CENTER - node.x * current.k,
        y: CENTER - node.y * current.k,
      }));
    },
    [byId],
  );

  const selectNode = React.useCallback(
    (id: string) => {
      // A drag that happened to end on a node must not also select it.
      if (movedRef.current) {
        movedRef.current = false;
        return;
      }
      setSelectedId(id);
      focusNode(id);
    },
    [focusNode],
  );

  // Wheel is attached manually so the handler can be non-passive and actually
  // prevent the page from scrolling under the graph.
  React.useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      setView((current) => zoomAt(current, toViewBox(event.clientX, event.clientY, svg), Math.exp(-event.deltaY * 0.0012)));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, []);

  const onPointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    svg.setPointerCapture(event.pointerId);
    panRef.current = { x: event.clientX, y: event.clientY, origin: view };
    movedRef.current = false;
    setPanning(true);
  };

  const onPointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const pan = panRef.current;
    const svg = svgRef.current;
    if (!pan || !svg) return;
    const dx = event.clientX - pan.x;
    const dy = event.clientY - pan.y;
    if (Math.abs(dx) + Math.abs(dy) > PAN_THRESHOLD) movedRef.current = true;
    const scale = viewBoxScale(svg);
    setView({
      ...pan.origin,
      x: pan.origin.x + dx / scale,
      y: pan.origin.y + dy / scale,
    });
  };

  const endPan = () => {
    panRef.current = null;
    setPanning(false);
  };

  const hasFocus = focusId !== null;

  return (
    <div className={cn("grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_260px]", className)}>
      <div className="relative flex items-center justify-center overflow-hidden border-border-soft lg:border-r">
        <svg
          ref={svgRef}
          className="block h-auto w-full max-w-full touch-none cursor-grab active:cursor-grabbing"
          viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
          role="img"
          aria-label="Knowledge graph. A problem at the centre connected to its topics, approaches, languages and recorded mistakes. Hover a node to highlight its relationships, click to inspect it, drag to pan and scroll to zoom."
          style={{ maxHeight: height }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endPan}
          onPointerCancel={endPan}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              reset();
            }
          }}
        >
          <g
            style={{
              transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})`,
              transformBox: "view-box",
              transformOrigin: "0 0",
              transition: panning
                ? "none"
                : "transform var(--duration-meaningful) var(--ease-emphasis)",
            }}
          >
            {/* Edges */}
            {edges.map((edge) => {
              const source = byId.get(edge.sourceId);
              const target = byId.get(edge.targetId);
              if (!source || !target) return null;
              const highlighted =
                focusId === edge.sourceId || focusId === edge.targetId;
              return (
                <line
                  key={`${edge.sourceId}-${edge.targetId}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={
                    highlighted ? "var(--color-graph-edge-active)" : "var(--color-graph-edge)"
                  }
                  strokeWidth={highlighted ? 1.4 : 1}
                  strokeOpacity={hasFocus && !highlighted ? 0.2 : 1}
                  vectorEffect="non-scaling-stroke"
                  style={{
                    transition:
                      "stroke var(--duration-ui) var(--ease-standard), stroke-opacity var(--duration-ui) var(--ease-standard)",
                  }}
                >
                  <title>
                    {`${source.label} ${RELATIONSHIP_LABEL[edge.relationship] ?? "connects to"} ${target.label}`}
                  </title>
                </line>
              );
            })}

            {/* Nodes */}
            {nodes.map((node) => {
              const isSelected = selectedId === node.id;
              const isFocused = focusId === node.id;
              const isCenter = node.id === centerId;
              const isNeighbor = focusNeighbors.has(node.id);
              const dimmed = hasFocus && !isFocused && !isNeighbor && !isCenter;
              const labelled = isCenter || isFocused || isNeighbor;
              return (
                <g
                  key={node.id}
                  className="cursor-pointer"
                  onClick={() => selectNode(node.id)}
                  onPointerEnter={() => setHoverId(node.id)}
                  onPointerLeave={() => setHoverId(null)}
                  onFocus={() => setHoverId(node.id)}
                  onBlur={() => setHoverId(null)}
                  tabIndex={0}
                  role="button"
                  aria-pressed={isSelected}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      selectNode(node.id);
                    } else if (event.key === "Escape") {
                      event.preventDefault();
                      reset();
                    }
                  }}
                  style={{
                    opacity: dimmed ? 0.14 : 1,
                    transition: "opacity var(--duration-ui) var(--ease-standard)",
                  }}
                >
                  {isFocused ? (
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={(isCenter ? 7 : node.radius) + (isSelected ? 5 : 3.5)}
                      fill="none"
                      stroke={TYPE_COLORS[node.type]}
                      strokeOpacity={isSelected ? 0.4 : 0.22}
                      strokeWidth={1}
                    />
                  ) : null}
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={isCenter ? 7 : node.radius}
                    fill={TYPE_COLORS[node.type]}
                    fillOpacity={isCenter ? 1 : 0.9}
                  />
                  {labelled ? (
                    <text
                      x={node.x}
                      y={node.y + (isCenter ? 20 : node.radius + 14)}
                      textAnchor="middle"
                      className={cn(
                        "font-mono",
                        isFocused ? "fill-text-primary" : "fill-text-muted",
                      )}
                      fontSize={isFocused ? 10.5 : 9}
                      fontWeight={isFocused ? 600 : 400}
                      // Canvas-coloured halo so a label stays readable where
                      // it crosses an edge or a dense cluster.
                      style={{
                        paintOrder: "stroke",
                        stroke: "var(--color-canvas)",
                        strokeWidth: 3,
                        strokeLinejoin: "round",
                      }}
                    >
                      {truncate(node.label)}
                      {node.label.length > LABEL_MAX ? "…" : ""}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </g>
        </svg>

        <div
          className="absolute bottom-3 right-3 flex flex-col gap-1 overflow-hidden rounded-md border border-border bg-surface/95 p-1"
          role="group"
          aria-label="Graph controls"
        >
          <div className="flex items-center gap-1">
            <ZoomControl aria-label="Zoom in" onClick={() => zoomBy(1.25)}>
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            </ZoomControl>
            <ZoomControl aria-label="Zoom out" onClick={() => zoomBy(1 / 1.25)}>
              <Minus className="h-3.5 w-3.5" aria-hidden="true" />
            </ZoomControl>
            <ZoomControl aria-label="Fit to view" onClick={() => fitToView()}>
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </ZoomControl>
            <ZoomControl aria-label="Reset view" onClick={reset}>
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            </ZoomControl>
          </div>
        </div>
      </div>

      <NodeDetail
        node={selected}
        graph={graph}
        centerId={centerId}
        onSelect={setSelectedId}
        onClear={() => setSelectedId(centerId)}
      />
    </div>
  );
}

function ZoomControl({
  children,
  onClick,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      onClick={onClick}
      {...props}
      className="press inline-flex h-7 w-7 items-center justify-center text-text-muted hover:bg-surface-hover hover:text-text-primary"
    >
      {children}
    </button>
  );
}

/** Detailed info panel for selected node */
function NodeDetail({
  node,
  graph,
  centerId,
  onSelect,
  onClear,
}: {
  node: LayoutNode | GraphNode | null;
  graph: KnowledgeGraphType;
  centerId: string;
  onSelect: (id: string) => void;
  onClear: () => void;
}) {
  if (!node) {
    return (
      <aside className="flex w-full flex-col gap-4 rounded-lg border border-border bg-surface p-5">
        <div className="eyebrow mb-2">What the graph shows</div>
        <div className="space-y-3 text-body-sm text-text-secondary">
          <p>
            The knowledge graph visualizes connections between your coding history.
          </p>
          <p className="font-technical-sm">
            <Info className="mr-1.5 inline-block h-3.5 w-3.5" /> {graph.nodes.length} nodes, {graph.edges.length} connections
          </p>
          <p className="text-text-muted">Select any node to see its relationships.</p>
        </div>
      </aside>
    );
  }

  const relations = graph.edges
    .filter((edge) => edge.sourceId === node.id || edge.targetId === node.id)
    .map((edge) => {
      const otherId = edge.sourceId === node.id ? edge.targetId : edge.sourceId;
      const other = graph.nodes.find((candidate) => candidate.id === otherId);
      if (!other) return null;
      return { other, relationship: edge.relationship, outgoing: edge.sourceId === node.id };
    })
    .filter((relation): relation is NonNullable<typeof relation> => relation !== null);

  // Cast to GraphNodeDetail if available
  const nodeDetail = node as GraphNodeDetail;

  return (
    <aside className="flex w-full flex-col gap-4 rounded-lg border border-border bg-surface p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="eyebrow mb-1">{TYPE_LABELS[node.type]}</div>
          <div className="text-body-md font-medium text-text-primary">{node.label}</div>
        </div>
        <span
          className="hidden h-2 w-2 rounded-full"
          style={{ backgroundColor: TYPE_COLORS[node.type as GraphNode["type"]] }}
          aria-hidden="true"
        />
      </div>

      {/* Node-specific details */}
      {nodeDetail.difficulty && (
        <div className="flex items-center gap-2">
          <span className="rounded-full px-2 py-0.5 text-xs font-medium"
            style={{
              backgroundColor: nodeDetail.difficulty === "Easy" ? "var(--color-easy)" :
                nodeDetail.difficulty === "Medium" ? "var(--color-medium)" :
                nodeDetail.difficulty === "Hard" ? "var(--color-hard)" : "var(--color-text-faint)",
              color: "var(--color-canvas)"
            }}>
            {nodeDetail.difficulty}
          </span>
        </div>
      )}

      {nodeDetail.topics && nodeDetail.topics.length > 0 && (
        <div>
          <div className="text-xs font-technical-sm text-text-muted uppercase tracking-wider">Topics</div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {nodeDetail.topics.slice(0, 5).map((topic) => (
              <span key={topic} className="rounded-full bg-surface-hover px-2 py-0.5 text-xs text-text-secondary">
                {topic}
              </span>
            ))}
            {nodeDetail.topics.length > 5 && (
              <span className="text-xs text-text-muted">+{nodeDetail.topics.length - 5} more</span>
            )}
          </div>
        </div>
      )}

      {nodeDetail.languages && nodeDetail.languages.length > 0 && (
        <div>
          <div className="text-xs font-technical-sm text-text-muted uppercase tracking-wider">Languages</div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {nodeDetail.languages.slice(0, 5).map((lang) => (
              <span key={lang} className="rounded-full bg-surface-hover px-2 py-0.5 text-xs text-text-secondary">
                {lang}
              </span>
            ))}
          </div>
        </div>
      )}

      {nodeDetail.approaches && nodeDetail.approaches.length > 0 && (
        <div>
          <div className="text-xs font-technical-sm text-text-muted uppercase tracking-wider">Approaches</div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {nodeDetail.approaches.slice(0, 3).map((app) => (
              <span key={app} className="rounded-full bg-surface-hover px-2 py-0.5 text-xs text-text-secondary">
                {app}
              </span>
            ))}
            {nodeDetail.approaches.length > 3 && (
              <span className="text-xs text-text-muted">+{nodeDetail.approaches.length - 3} more</span>
            )}
          </div>
        </div>
      )}

      <div className="mt-5 h-px bg-border-soft" />

      <div className="eyebrow mb-3">Relationships ({relations.length})</div>
      <ul className="flex flex-col gap-1.5">
        {relations.map(({ other, relationship, outgoing }) => (
          <li key={`${other.id}-${relationship}`}>
            <button
              type="button"
              onClick={() => onSelect(other.id)}
              className="press flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-surface-hover"
            >
              <span
                className="h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ backgroundColor: TYPE_COLORS[other.type] }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-body-sm text-text-secondary">{other.label}</span>
                <span className="block font-technical-sm text-text-faint">
                  {outgoing ? "→" : "←"} {RELATIONSHIP_LABEL[relationship] ?? "connects"}
                </span>
              </span>
            </button>
          </li>
        ))}
        {relations.length === 0 ? (
          <li className="text-body-sm text-text-faint">No relationships recorded.</li>
        ) : null}
      </ul>

      {node.id !== centerId && (
        <button
          type="button"
          onClick={onClear}
          className="press mt-2 self-start font-technical-sm text-text-faint hover:text-text-secondary"
        >
          Reset selection
        </button>
      )}
    </aside>
  );
}

/** Direct neighbours of a node, plus itself — the set worth labelling. */
function neighborsOf(graph: KnowledgeGraphType, id: string | null): Set<string> {
  const set = new Set<string>();
  if (!id) return set;
  set.add(id);
  for (const edge of graph.edges) {
    if (edge.sourceId === id) set.add(edge.targetId);
    else if (edge.targetId === id) set.add(edge.sourceId);
  }
  return set;
}

/** Zoom about a fixed anchor point so the cursor stays over what it was over. */
function zoomAt(view: View, anchor: { x: number; y: number }, factor: number): View {
  const k = Math.min(MAX_SCALE, Math.max(MIN_SCALE, view.k * factor));
  if (k === view.k) return view;
  return {
    k,
    x: view.x + anchor.x * (view.k - k),
    y: view.y + anchor.y * (view.k - k),
  };
}

/** Screen px → viewBox units. The viewBox is square and uses `meet`, so it is
    letterboxed inside the element when the box is not square. */
function toViewBox(
  clientX: number,
  clientY: number,
  svg: SVGSVGElement,
): { x: number; y: number } {
  const rect = svg.getBoundingClientRect();
  const scale = viewBoxScale(svg);
  return {
    x: (clientX - rect.left - (rect.width - SVG_SIZE * scale) / 2) / scale,
    y: (clientY - rect.top - (rect.height - SVG_SIZE * scale) / 2) / scale,
  };
}

/** ViewBox units per screen pixel. */
function viewBoxScale(svg: SVGSVGElement): number {
  const rect = svg.getBoundingClientRect();
  return SVG_SIZE / Math.max(1, Math.min(rect.width, rect.height));
}

/**
 * Force-directed layout for the knowledge graph.
 *
 * Positions nodes with proper spacing using a physics simulation.
 * The center node is at the middle, connected nodes are arranged
 * in concentric rings with adaptive spacing.
 */
function layout(graph: KnowledgeGraphType, centerId: string): {
  nodes: LayoutNode[];
  edges: GraphEdge[];
  byId: Map<string, LayoutNode>;
} {
  const center = graph.nodes.find((node) => node.id === centerId);
  const byId = new Map<string, LayoutNode>();

  if (!center) {
    return { nodes: [], edges: [], byId };
  }

  // Collect all nodes
  const allNodes = [...graph.nodes];
  const neighbors = allNodes.filter((node) => node.id !== centerId);

  // Build adjacency map for connection counts
  const connectionCount = new Map<string, number>();
  for (const edge of graph.edges) {
    connectionCount.set(edge.sourceId, (connectionCount.get(edge.sourceId) ?? 0) + 1);
    connectionCount.set(edge.targetId, (connectionCount.get(edge.targetId) ?? 0) + 1);
  }

  // Group neighbors by type
  const byType = new Map<GraphNode["type"], GraphNode[]>();
  for (const node of neighbors) {
    if (!byType.has(node.type)) byType.set(node.type, []);
    byType.get(node.type)!.push(node);
  }

  // Calculate ring radius based on number of nodes and types
  const minRadius = 80;
  const nodeCount = neighbors.length;
  const ringRadius = nodeCount > 10
    ? minRadius + (nodeCount - 10) * 4
    : minRadius;

  // Compute angles for each type's arc
  const typeEntries = Array.from(byType.entries());
  const totalTypes = typeEntries.length;
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const gapBetweenTypes = (Math.PI * 2 - totalTypes * 0.3) / Math.max(1, nodeCount);

  const placed: LayoutNode[] = [
    { ...center, x: CENTER, y: CENTER, radius: NODE_RADIUS.Problem ?? 20, index: 0 },
  ];

  let currentAngle = -Math.PI / 2;

  for (const [, nodesOfType] of typeEntries) {
    const nodesInType = nodesOfType.length;
    const typeArc = Math.PI * (nodesInType / Math.max(1, nodeCount) + 0.1);
    const startAngle = currentAngle;
    const endAngle = startAngle + typeArc;

    for (let i = 0; i < nodesInType; i++) {
      const node = nodesOfType[i];
      const t = nodesInType > 1 ? i / (nodesInType - 1) : 0.5;
      const angle = startAngle + t * typeArc;

      // Place at the calculated ring radius
      const distanceFromCenter = ringRadius;
      const x = CENTER + Math.cos(angle) * distanceFromCenter;
      const y = CENTER + Math.sin(angle) * distanceFromCenter;

      placed.push({
        ...node,
        x,
        y,
        radius: NODE_RADIUS[node.type] ?? 14,
        index: placed.length,
        connectionCount: connectionCount.get(node.id) ?? 0,
      });
    }

    currentAngle = endAngle + 0.3; // gap between types
  }

  // Build position map
  for (const node of placed) {
    byId.set(node.id, node);
  }

  // Filter edges - show all edges in the graph for now
  const visibleEdges = graph.edges.filter((edge) => {
    return byId.has(edge.sourceId) && byId.has(edge.targetId);
  });

  return { nodes: placed, edges: visibleEdges, byId };
}

function truncate(label: string): string {
  if (label.length <= LABEL_MAX) return label;
  return label.slice(0, LABEL_MAX).trimEnd();
}
