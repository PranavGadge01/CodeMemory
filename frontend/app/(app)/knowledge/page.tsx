import Link from "next/link";
import { ArrowUpRight, Network } from "lucide-react";
import { getKnowledge, getProblem, listProblems, toAsyncState } from "@/lib/api";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { KnowledgeGraphPanel } from "@/components/app/knowledge/knowledge-graph";
import { Reveal } from "@/components/system/reveal";
import { Button } from "@/components/ui/button";
import { EmptyDataState, ErrorState, PageSkeleton } from "@/components/app/data-states";
import { isSolved, submissionCount } from "@/lib/mock/derive";

export const metadata = { title: "Knowledge" };

const TYPE_LEGEND = [
  { label: "Problem", color: "var(--color-accent)" },
  { label: "Topic", color: "rgba(255,255,255,0.55)" },
  { label: "Concept", color: "var(--color-info)" },
  { label: "Approach", color: "var(--color-medium)" },
  { label: "Language", color: "var(--color-success)" },
  { label: "Mistake", color: "var(--color-error)" },
];

export default async function KnowledgePage() {
  // The graph is keyed by node ids the backend assigns (`prob_<id>`), so the
  // centre is chosen from the graph itself rather than derived from a slug.
  const state = await toAsyncState(
    (async () => {
      const knowledge = await getKnowledge();
      const problems = await listProblems({ page: 1, pageSize: 100 }).then((list) =>
        Promise.all(list.items.map((item) => getProblem(item.slug))),
      );
      return { knowledge, problems };
    })(),
  );

  if (state.status !== "success") {
    return <KnowledgePending state={state} />;
  }

  const { graph, clusters } = state.data.knowledge;
  const { problems } = state.data;

  const center = graph.nodes.find((node) => node.type === "Problem") ?? graph.nodes[0];
  const centerTitle = center?.label ?? "Knowledge graph";

  const topicNodes = graph.nodes.filter((node) => node.type === "Topic").length;
  const approachNodes = graph.nodes.filter((node) => node.type === "Approach").length;
  const mistakeNodes = graph.nodes.filter((node) => node.type === "Mistake").length;
  const languageNodes = graph.nodes.filter((node) => node.type === "Language").length;
  const problemNodes = graph.nodes.filter((node) => node.type === "Problem").length;

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Knowledge"
          title="Connected memory"
          description="Problems link to the topics they use, the approaches you tried, the languages you reached for, and the mistakes you made along the way. Follow any thread."
          actions={
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard">
                Back to overview
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          }
        />

        <div className="grid grid-cols-2 divide-x divide-border-soft rounded-lg border border-border bg-surface sm:grid-cols-4">
          <Metric label="Problems" value={problemNodes} />
          <Metric label="Topics" value={topicNodes} />
          <Metric label="Approaches" value={approachNodes} accent />
          <Metric label="Mistakes recorded" value={mistakeNodes} />
        </div>

        <Reveal>
          <Surface className="overflow-hidden">
            <SurfaceHeader
              eyebrow="Graph"
              title={centerTitle}
              description="Select any node to inspect its relationships. The graph is rendered from your own submission history."
              action={
                <span className="hidden items-center gap-1.5 font-technical-sm text-text-muted sm:flex">
                  <Network className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
                  {languageNodes} languages
                </span>
              }
            />
            {center ? (
              <KnowledgeGraphPanel graph={graph} centerId={center.id} height={480} />
            ) : (
              <EmptyDataState
                className="py-16"
                title="The graph is empty"
                description="Nodes appear once problems with topics and submissions are indexed."
              />
            )}
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border-soft px-5 py-3">
              <span className="eyebrow">Legend</span>
              {TYPE_LEGEND.map((entry) => (
                <span
                  key={entry.label}
                  className="inline-flex items-center gap-1.5 font-technical-sm text-text-muted"
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: entry.color }}
                    aria-hidden="true"
                  />
                  {entry.label}
                </span>
              ))}
            </div>
          </Surface>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
          <Reveal delay={60}>
            <Surface>
              <SurfaceHeader
                eyebrow="Clusters"
                title="Topic clusters"
                description="Where your practice actually concentrates, and where it thins out."
              />
              {clusters.length > 0 ? (
                <div className="flex flex-col">
                  {clusters.slice(0, 10).map((cluster) => (
                    <div
                      key={cluster.id}
                      className="flex items-center gap-4 border-b border-border-soft px-5 py-4 last:border-0"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-body-sm font-medium text-text-primary">
                          {cluster.title}
                        </div>
                        <div className="mt-0.5 font-technical-sm text-text-faint">
                          {cluster.description}
                        </div>
                        <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-surface-card">
                          <span
                            className="block h-full rounded-full bg-accent/80"
                            style={{ width: `${cluster.masteryPct}%` }}
                            aria-hidden="true"
                          />
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className="font-technical text-text-primary tabular-nums">
                          {cluster.masteryPct}%
                        </div>
                        <div className="font-technical-sm text-text-faint">mastery</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyDataState
                  className="py-12"
                  title="No topic clusters"
                  description="Clusters are computed from solved-problem concentration per topic. They appear once enough topics have solved problems behind them."
                />
              )}
            </Surface>
          </Reveal>

          <Reveal delay={120}>
            <Surface className="h-full">
              <SurfaceHeader eyebrow="Weakest" title="Thinnest coverage" />
              {clusters.length > 0 ? (
                <div className="flex flex-col">
                  {[...clusters]
                    .sort((a, b) => a.masteryPct - b.masteryPct)
                    .slice(0, 6)
                    .map((cluster) => (
                      <Link
                        key={`weak-${cluster.id}`}
                        href={`/problems`}
                        className="press group flex items-center justify-between gap-3 border-b border-border-soft px-5 py-3.5 last:border-0 hover:bg-surface-hover"
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-body-sm text-text-secondary group-hover:text-text-primary">
                            {cluster.title}
                          </span>
                          <span className="font-technical-sm text-text-faint">
                            {cluster.problemIds.length} problems
                          </span>
                        </span>
                        <span className="shrink-0 font-technical-sm text-warning tabular-nums">
                          {cluster.masteryPct}%
                        </span>
                      </Link>
                    ))}
                </div>
              ) : (
                <EmptyDataState
                  className="py-12"
                  title="No coverage signal"
                  description="Thinnest coverage ranks topic clusters by mastery once they exist."
                />
              )}
            </Surface>
          </Reveal>
        </div>

        <Reveal>
          <Surface>
            <SurfaceHeader
              eyebrow="Problems"
              title="Most connected problems"
              description="The problems that touch the most topics and approaches — the ones worth keeping as reference."
            />
            {graph.nodes.length > 0 ? (
              <div className="flex flex-col">
                {problems
                  .map((problem) => ({
                    problem,
                    degree: graph.edges.filter(
                      (edge) => edge.sourceId === problem.id || edge.targetId === problem.id,
                    ).length,
                  }))
                  .sort((a, b) => b.degree - a.degree)
                  .slice(0, 8)
                  .map(({ problem, degree }) => (
                    <Link
                      key={problem.id}
                      href={`/problems?slug=${problem.slug}`}
                      className="press group flex items-center gap-4 border-b border-border-soft px-5 py-3.5 last:border-0 hover:bg-surface-hover"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-body-sm font-medium text-text-primary">
                          {problem.title}
                        </div>
                        <div className="mt-0.5 truncate font-technical-sm text-text-faint">
                          {problem.topics.join(" · ")}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-4">
                        <span className="font-technical-sm text-text-muted">
                          {submissionCount(problem)} submissions
                        </span>
                        <span className="font-technical-sm text-accent tabular-nums">
                          {degree} links
                        </span>
                        <span
                          className={isSolved(problem) ? "text-success" : "text-warning"}
                          title={isSolved(problem) ? "Solved" : "Unsolved"}
                        >
                          {isSolved(problem) ? "●" : "○"}
                          <span className="sr-only">{isSolved(problem) ? "Solved" : "Unsolved"}</span>
                        </span>
                      </div>
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
          title="Connected memory"
          description="Problems link to the topics they use, the approaches you tried, the languages you reached for, and the mistakes you made along the way. Follow any thread."
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

function Metric({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="px-4 py-3.5 sm:px-5">
      <div className="eyebrow">{label}</div>
      <div className={cnMetric(accent)}>{value}</div>
    </div>
  );
}

function cnMetric(accent?: boolean): string {
  return [
    "mt-1.5",
    "font-technical",
    "text-text-primary",
    "tabular-nums",
    accent ? "text-accent" : "",
  ]
    .filter(Boolean)
    .join(" ");
}
