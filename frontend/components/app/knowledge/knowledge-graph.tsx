"use client";

import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import type { GraphNode, KnowledgeGraph as KnowledgeGraphType } from "@/lib/types";

type LayoutNode = GraphNode & {
  x: number;
  y: number;
  radius: number;
  index: number;
};

const TYPE_ORDER: GraphNode["type"][] = [
  "Topic",
  "Concept",
  "Approach",
  "Language",
  "Mistake",
];

const TYPE_RADIUS: Record<GraphNode["type"], number> = {
  Topic: 88,
  Concept: 132,
  Approach: 132,
  Language: 178,
  Mistake: 178,
  Problem: 0,
};

const TYPE_FILL: Record<GraphNode["type"], string> = {
  Problem: "var(--color-accent)",
  Topic: "rgba(255,255,255,0.55)",
  Concept: "var(--color-info)",
  Approach: "var(--color-accent)",
  Language: "var(--color-success)",
  Mistake: "var(--color-error)",
};

const TYPE_LABEL: Record<GraphNode["type"], string> = {
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

const SVG_SIZE = 460;
const CENTER = SVG_SIZE / 2;
const LABEL_MAX = 22;

/**
 * Radial knowledge graph.
 *
 * One problem sits at the centre and everything it is connected to is placed
 * around it. Node types are separated by radius so neighbours never overlap,
 * and each type occupies its own wedge of the circle. The aim is a calm,
 * legible map of a single problem's memory — not a noisy neural-network
 * aesthetic.
 */
export function KnowledgeGraphPanel({
  graph,
  centerId,
  className,
  height = 460,
}: {
  graph: KnowledgeGraphType;
  centerId: string;
  className?: string;
  height?: number;
}) {
  const [selectedId, setSelectedId] = React.useState<string | null>(centerId);

  const { nodes, edges, byId } = React.useMemo(
    () => layout(graph, centerId),
    [graph, centerId],
  );

  const selected = selectedId ? (byId.get(selectedId) ?? null) : null;

  return (
    <div className={cn("grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_260px]", className)}>
      <div className="relative flex items-center justify-center overflow-hidden border-border-soft lg:border-r">
        <svg
          className="block h-auto w-full max-w-[460px]"
          viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
          role="img"
          aria-label="Knowledge graph. A problem at the centre connected to its topics, approaches, languages and recorded mistakes."
          style={{ maxHeight: height }}
        >
          {/* Edges */}
          {edges.map((edge) => {
            const source = byId.get(edge.sourceId);
            const target = byId.get(edge.targetId);
            if (!source || !target) return null;
            const highlight =
              selectedId === edge.sourceId || selectedId === edge.targetId;
            return (
              <line
                key={`${edge.sourceId}-${edge.targetId}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={highlight ? "rgba(255,161,22,0.5)" : "rgba(255,255,255,0.11)"}
                strokeWidth={highlight ? 1.25 : 1}
                vectorEffect="non-scaling-stroke"
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
            const isCenter = node.id === centerId;
            return (
              <g
                key={node.id}
                className="cursor-pointer"
                onClick={() => setSelectedId(node.id)}
                tabIndex={0}
                role="button"
                aria-pressed={isSelected}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setSelectedId(node.id);
                  }
                }}
              >
                {isSelected ? (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={node.radius + 5}
                    fill="none"
                    stroke={TYPE_FILL[node.type]}
                    strokeOpacity={0.4}
                    strokeWidth={1}
                  />
                ) : null}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isCenter ? 7 : node.radius}
                  fill={isCenter ? TYPE_FILL.Problem : TYPE_FILL[node.type]}
                  fillOpacity={isCenter ? 1 : 0.9}
                />
                <text
                  x={node.x}
                  y={node.y + (isCenter ? 20 : node.radius + 14)}
                  textAnchor="middle"
                  className={cn(
                    "font-mono",
                    isCenter ? "fill-text-primary" : "fill-text-muted",
                  )}
                  fontSize={isCenter ? 10.5 : 9}
                  fontWeight={isCenter ? 600 : 400}
                >
                  {truncate(node.label)}
                  {node.label.length > LABEL_MAX ? "…" : ""}
                </text>
              </g>
            );
          })}
        </svg>
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
      <div className="px-5 py-6">
        <div className="eyebrow mb-2">Selection</div>
        <p className="text-body-sm text-text-muted">
          Select any node to inspect what it connects to.
        </p>
      </div>
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

  const problemNode =
    node.type === "Problem" ? node : graph.nodes.find((candidate) => candidate.type === "Problem");

  return (
    <div className="flex flex-col px-5 py-6">
      <div className="eyebrow mb-2">{TYPE_LABEL[node.type]}</div>
      <div className="text-body-md font-medium text-text-primary">{node.label}</div>

      <div className="mt-1 flex items-center gap-2">
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: TYPE_FILL[node.type] }}
          aria-hidden="true"
        />
        <span className="font-technical-sm text-text-faint">
          {relations.length} connection{relations.length === 1 ? "" : "s"}
        </span>
      </div>

      {problemNode && problemNode.id !== node.id ? (
        <Link
          href={`/problems?slug=${slugFromId(problemNode.id)}`}
          className="press mt-4 inline-flex w-fit items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 font-technical-sm text-text-secondary hover:border-border-strong hover:text-text-primary"
        >
          {problemNode.label}
        </Link>
      ) : null}

      <div className="mt-5 h-px bg-border-soft" />

      <div className="eyebrow mt-5 mb-3">Relationships</div>
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
                style={{ backgroundColor: TYPE_FILL[other.type] }}
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

      {node.id !== centerId ? (
        <button
          type="button"
          onClick={onClear}
          className="press mt-5 self-start font-technical-sm text-text-faint hover:text-text-secondary"
        >
          Reset selection
        </button>
      ) : null}
    </div>
  );
}

/**
 * Deterministic radial layout.
 *
 * Each node type is given its own wedge of the circle, sized in proportion to
 * how many of that type there are, and its own radius. The result never
 * overlaps and always looks the same for the same data.
 */
function layout(graph: KnowledgeGraphType, centerId: string): {
  nodes: LayoutNode[];
  edges: KnowledgeGraphType["edges"];
  byId: Map<string, LayoutNode>;
} {
  const center = graph.nodes.find((node) => node.id === centerId);
  const byId = new Map<string, LayoutNode>();

  if (!center) {
    return { nodes: [], edges: [], byId };
  }

  const neighbors = graph.nodes.filter((node) => node.id !== centerId);
  const byType = new Map<GraphNode["type"], GraphNode[]>();
  for (const node of neighbors) {
    if (!byType.has(node.type)) byType.set(node.type, []);
    byType.get(node.type)!.push(node);
  }

  const typesPresent = TYPE_ORDER.filter((type) => byType.has(type));
  const totalNeighbors = neighbors.length;

  // Wedge for each type, proportional to its share of the neighbours, with a
  // small gap so neighbouring sectors stay visually distinct.
  const totalGap = typesPresent.length * 0.09;
  const sweep = (Math.PI * 2 - totalGap) / Math.max(1, totalNeighbors);

  let angle = -Math.PI / 2;

  const placed: LayoutNode[] = [
    { ...center, x: CENTER, y: CENTER, radius: 7, index: 0 },
  ];

  for (const type of typesPresent) {
    const group = byType.get(type) as GraphNode[];
    const gap = 0.09;
    for (const node of group) {
      const x = CENTER + Math.cos(angle) * TYPE_RADIUS[type];
      const y = CENTER + Math.sin(angle) * TYPE_RADIUS[type];
      placed.push({ ...node, x, y, radius: 4, index: placed.length });
      angle += sweep;
    }
    angle += gap;
  }

  for (const node of placed) {
    byId.set(node.id, node);
  }

  // Only keep edges that involve the centre or one of its direct neighbours.
  const visibleEdges = graph.edges.filter((edge) => {
    const nearCenter = edge.sourceId === centerId || edge.targetId === centerId;
    if (nearCenter) return true;
    return byId.has(edge.sourceId) && byId.has(edge.targetId);
  });

  return { nodes: placed, edges: visibleEdges, byId };
}

function truncate(label: string): string {
  if (label.length <= LABEL_MAX) return label;
  return label.slice(0, LABEL_MAX).trimEnd();
}

function slugFromId(id: string): string {
  return id.replace(/^prob_/, "");
}
