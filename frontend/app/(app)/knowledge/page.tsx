"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Network, BookOpen } from "lucide-react";
import { getKnowledge, ApiError } from "@/lib/api";
import type { KnowledgeData, GraphNodeDetail, GraphNode } from "@/lib/types";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { KnowledgeGraphPanel } from "@/components/app/knowledge/knowledge-graph";
import { Reveal } from "@/components/system/reveal";
import { Button } from "@/components/ui/button";
import { EmptyDataState, ErrorState, PageSkeleton } from "@/components/app/data-states";

export default function KnowledgePage() {
  const [state, setState] = React.useState<
    | { status: "loading" }
    | { status: "success"; data: KnowledgeData }
    | { status: "error"; error: ApiError }
  >({ status: "loading" });

  React.useEffect(() => {
    let cancelled = false;
    getKnowledge()
      .then((data) => { if (!cancelled) setState({ status: "success", data }); })
      .catch((error: unknown) => { if (!cancelled) setState({ status: "error", error: error instanceof ApiError ? error : new ApiError("Could not load knowledge data.", "ERROR", 0) }); });
    return () => { cancelled = true; };
  }, []);

  if (state.status !== "success") {
    return <KnowledgePending state={state} />;
  }

  const { graph, entityCounts } = state.data;

  // Find a center node (prefer a Problem)
  const centerNode = graph.nodes.find((n: GraphNode) => n.type === "Problem") as GraphNodeDetail | undefined;
  const centerId = centerNode?.id ?? graph.nodes[0]?.id;
  const centerTitle = centerNode?.label ?? "Your coding knowledge";

  // Get connection statistics for the snapshot
  const problemNodes = graph.nodes.filter((n: GraphNode) => n.type === "Problem") as GraphNodeDetail[];
  const topicNodes = graph.nodes.filter((n: GraphNode) => n.type === "Topic");
  const approachNodes = graph.nodes.filter((n: GraphNode) => n.type === "Approach");
  const languageNodes = graph.nodes.filter((n: GraphNode) => n.type === "Language");
  const mistakeNodes = graph.nodes.filter((n: GraphNode) => n.type === "Mistake");
  const conceptNodes = graph.nodes.filter((n: GraphNode) => n.type === "Concept");

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Knowledge"
          title="Your coding memory"
          description="Explore the problems, concepts, topics, approaches and techniques you've encountered — and how they connect."
          actions={
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard">
                Back to overview
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          }
        />

        {/* Knowledge snapshot */}
        <div className="grid grid-cols-2 divide-x divide-border-soft rounded-lg border border-border bg-surface sm:grid-cols-6">
          <Metric label="Problems" value={entityCounts.Problem ?? problemNodes.length} />
          <Metric label="Topics" value={entityCounts.Topic ?? topicNodes.length} />
          <Metric label="Approaches" value={entityCounts.Approach ?? approachNodes.length} accent />
          <Metric label="Concepts" value={entityCounts.Concept ?? conceptNodes.length} />
          <Metric label="Languages" value={entityCounts.Language ?? languageNodes.length} />
          <Metric label="Mistakes" value={entityCounts.Mistake ?? mistakeNodes.length} />
        </div>

        {/* Graph */}
        <Reveal>
          <Surface className="overflow-hidden">
            <SurfaceHeader
              eyebrow="Knowledge graph"
              title={centerTitle}
              description="Select any node to inspect its relationships. The graph shows how your coding history connects."
              action={
                <span className="hidden items-center gap-1.5 font-technical-sm text-text-muted sm:flex">
                  <Network className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
                  {languageNodes.length} languages
                </span>
              }
            />
            {centerId ? (
              <KnowledgeGraphPanel graph={graph} centerId={centerId} height={400} />
            ) : (
              <EmptyDataState
                className="py-16"
                title="The knowledge graph is empty"
                description="Nodes appear once problems with topics and submissions are indexed."
              />
            )}
          </Surface>
        </Reveal>

        {/* Related knowledge section */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
          <Reveal delay={60}>
            <Surface>
              <SurfaceHeader
                eyebrow="Connected methods"
                title="Topics and approaches"
                description="The concepts your problems connect to."
              />
              {topicNodes.length > 0 ? (
                <div className="flex flex-wrap gap-2 p-5">
                  {topicNodes.slice(0, 8).map((topic: GraphNode) => (
                    <Link
                      key={topic.id}
                      href={`/problems`}
                      className="press inline-flex items-center gap-2 rounded-full bg-surface-hover px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-hover"
                    >
                      <BookOpen className="h-3.5 w-3.5 text-accent" />
                      {topic.label}
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyDataState
                  className="py-12"
                  title="No topics recorded"
                  description="Topics appear once problems are tagged with them."
                />
              )}
            </Surface>
          </Reveal>

          <Reveal delay={120}>
            <Surface>
              <SurfaceHeader
                eyebrow="Most connected problems"
                title="Linked problems"
                description="Problems with many connections in your knowledge graph."
              />
              {problemNodes.length > 0 ? (
                <div className="flex flex-col">
                  {problemNodes
                    .sort((a, b) => (b.connectionCount ?? 0) - (a.connectionCount ?? 0))
                    .slice(0, 6)
                    .map((problem) => (
                      <Link
                        key={problem.id}
                        href={`/problems?slug=${problem.id.replace(/^prob_/, "")}`}
                        className="press group flex items-center gap-3 border-b border-border-soft px-5 py-3 last:border-0 hover:bg-surface-hover"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-body-sm font-medium text-text-primary">
                            {problem.label}
                          </div>
                          <div className="mt-0.5 font-technical-sm text-text-faint">
                            {problem.topics?.join(" · ") ?? "No topics"}
                          </div>
                        </div>
                        <span className="flex shrink-0 items-center gap-2 font-technical-sm text-text-muted">
                          <span className="tabular-nums">{problem.connectionCount ?? 0}</span>
                          <span className="font-technical-sm text-text-faint">links</span>
                        </span>
                      </Link>
                    ))}
                </div>
              ) : (
                <EmptyDataState
                  className="py-12"
                  title="No connected problems"
                  description="The most connected problems appear once the graph has edges to count."
                />
              )}
            </Surface>
          </Reveal>
        </div>
      </PageSection>
    </PageContainer>
  );
}

function KnowledgePending({
  state,
}: {
  state: { status: "loading" } | { status: "error"; error: import("@/lib/api").ApiError };
}) {
  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Knowledge"
          title="Your coding memory"
          description="Explore the problems, concepts, topics, approaches and techniques you've encountered — and how they connect."
        />
        {state.status === "error" ? (
          <Surface>
            <ErrorState error={state.error} />
          </Surface>
        ) : (
          <PageSkeleton />
        )}
      </PageSection>
    </PageContainer>
  );
}

function Metric({ label, value, accent }: { label: string; value: number | string; accent?: boolean }) {
  return (
    <div className="px-4 py-3.5 sm:px-5">
      <div className="eyebrow text-xs uppercase tracking-wider">{label}</div>
      <div className={cnMetric(accent)}>{value}</div>
    </div>
  );
}

function cnMetric(accent?: boolean): string {
  return [
    "mt-1.5",
    "font-mono",
    "text-text-primary",
    "tabular-nums",
    "text-heading-sm",
    accent ? "text-accent" : "",
  ]
    .filter(Boolean)
    .join(" ");
}