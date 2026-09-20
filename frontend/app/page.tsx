import Link from "next/link";
import { ArrowRight, ArrowUpRight, Database, Network, RotateCw } from "lucide-react";
import { getDashboardData, getKnowledge, getRevisionQueue } from "@/lib/data";
import { getEvolutionStory, EVOLUTION_STORIES } from "@/lib/mock/snippets";
import { getMockProblems } from "@/lib/mock/problems";
import { isSolved, submissionCount } from "@/lib/mock/derive";
import { SiteNav } from "@/components/home/site-nav";
import { HeroPanel } from "@/components/home/hero-panel";
import { SolutionEvolution } from "@/components/app/solution-evolution";
import { ActivityHeatmap } from "@/components/charts/activity-heatmap";
import { Timeline } from "@/components/app/timeline";
import { BarChart } from "@/components/charts/bar-chart";
import { DistributionBars } from "@/components/charts/distribution";
import { KnowledgeGraphPanel } from "@/components/app/knowledge/knowledge-graph";
import { Reveal } from "@/components/system/reveal";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Button } from "@/components/ui/button";
import { DifficultyBadge } from "@/components/ui/badges";
import { formatNumber, formatPercent } from "@/lib/format";
import { problemIdFor } from "@/lib/mock/knowledge";

export default function HomePage() {
  const data = getDashboardData();
  const revision = getRevisionQueue();
  const knowledge = getKnowledge();
  const story = getEvolutionStory("3sum") ?? EVOLUTION_STORIES[0];
  const { overview } = data;

  const heroProblem = getMockProblems().find((problem) => problem.slug === "3sum");
  const heroStory = getEvolutionStory("3sum") ?? story;

  return (
    <div className="relative flex min-h-screen flex-col">
      <SiteNav />

      <main className="flex-1">
        {/* ---------------------------------------------------------------- hero */}
        <section
          id="product"
          aria-labelledby="hero-heading"
          className="relative overflow-hidden border-b border-border-soft"
        >
          <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" aria-hidden="true" />
          <div
            className="pointer-events-none absolute inset-x-0 top-0 h-px"
            style={{ background: "linear-gradient(90deg, transparent, rgba(255,161,22,0.35), transparent)" }}
            aria-hidden="true"
          />
          <div className="relative mx-auto grid w-full max-w-[1200px] grid-cols-1 items-center gap-10 px-5 py-16 md:px-8 md:py-24 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-12">
            <div className="flex flex-col">
              <span className="eyebrow flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />
                Your coding memory
              </span>

              <h1
                id="hero-heading"
                className="text-display-xl mt-5 text-text-primary"
              >
                Your coding history,{" "}
                <span className="relative whitespace-nowrap">
                  remembered
                  <span
                    aria-hidden="true"
                    className="absolute -bottom-0.5 left-0 h-[2px] w-full bg-accent/70"
                  />
                </span>
                .
              </h1>

              <p className="mt-6 max-w-[52ch] text-body-lg text-text-muted">
                CodeMemory turns every submission you have ever made into searchable
                knowledge, measurable progress, and a durable memory of{" "}
                <span className="text-text-secondary">how you actually solve problems</span>.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Button variant="primary" size="lg" asChild>
                  <Link href="/dashboard">
                    Open CodeMemory
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" asChild>
                  <Link href="#evolution">See how it works</Link>
                </Button>
              </div>

              <div className="mt-12 flex flex-wrap items-baseline gap-x-8 gap-y-3 border-t border-border-soft pt-6">
                <Stat value={formatNumber(overview.acceptedProblems)} label="problems solved" />
                <Stat value={formatNumber(overview.totalSubmissions)} label="submissions kept" />
                <Stat value={`${overview.longestStreakDays}d`} label="best streak" />
                <Stat value={formatPercent(overview.overallAcceptanceRatePct, 0)} label="acceptance" accent />
              </div>
            </div>

            <Reveal delay={80} className="relative">
              <HeroPanel story={heroStory} />
              <span
                aria-hidden="true"
                className="absolute -inset-x-6 -bottom-6 -z-10 h-24 bg-accent/5 blur-2xl"
              />
            </Reveal>
          </div>
        </section>

        {/* ------------------------------------------------------- memory trace */}
        <section
          id="memory"
          aria-labelledby="memory-heading"
          className="border-b border-border-soft"
        >
          <div className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-20">
            <SectionHeading
              eyebrow="Memory trace"
              title="Every attempt is preserved"
              description="Failed attempts are kept alongside the accepted one — a TLE on attempt one is part of the story of attempt three. Nothing is overwritten."
              id="memory-heading"
            />

            <div className="mt-10 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
              <Reveal>
                <Surface>
                  <SurfaceHeader
                    title="Activity"
                    description={`${formatNumber(data.activity.length)} days of submission history`}
                    action={<Database className="h-4 w-4 text-text-faint" aria-hidden="true" />}
                  />
                  <div className="px-5 py-4">
                    <ActivityHeatmap days={data.activity} />
                  </div>
                </Surface>
              </Reveal>

              <Reveal delay={60}>
                <Surface className="h-full">
                  <SurfaceHeader title="Recent memory" />
                  <div className="px-5 py-5">
                    <Timeline events={data.timeline.slice(0, 6)} />
                  </div>
                </Surface>
              </Reveal>
            </div>
          </div>
        </section>

        {/* --------------------------------------------------- solution evolution */}
        <section
          id="evolution"
          aria-labelledby="evolution-heading"
          className="border-b border-border-soft bg-surface/40"
        >
          <div className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-20">
            <SectionHeading
              eyebrow="Solution evolution"
              title="See how your thinking moved"
              description="CodeMemory keeps each attempt with its own approach, complexity and runtime, so a problem is a sequence — not just the final answer."
              id="evolution-heading"
            />

            <Reveal delay={60} className="mt-10">
              <Surface className="overflow-hidden">
                <SolutionEvolution story={story} />
              </Surface>
            </Reveal>

            {heroProblem ? (
              <Reveal delay={100}>
                <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 px-1 text-body-sm text-text-muted">
                  <span className="inline-flex items-center gap-2">
                    <DifficultyBadge difficulty={heroProblem.difficulty} />
                    {heroProblem.topics.join(" · ")}
                  </span>
                  <span className="font-technical-sm text-text-faint">
                    {submissionCount(heroProblem)} submissions · {isSolved(heroProblem) ? "solved" : "open"}
                  </span>
                </div>
              </Reveal>
            ) : null}
          </div>
        </section>

        {/* ------------------------------------------------------------- analytics */}
        <section id="analytics" aria-labelledby="analytics-heading" className="border-b border-border-soft">
          <div className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-20">
            <SectionHeading
              eyebrow="Analytics"
              title="Progress you can measure"
              description="Derived from your own submissions — consistency, difficulty progression, language usage. Charts that carry information rather than decorating space."
              id="analytics-heading"
            />

            <div className="mt-10 grid grid-cols-1 gap-5 lg:grid-cols-3">
              <Reveal className="lg:col-span-2">
                <Surface className="h-full">
                  <SurfaceHeader
                    title="Weekly submissions"
                    description="The last eight weeks of solving activity."
                  />
                  <div className="px-5 py-5">
                    <BarChart
                      data={data.progress.slice(-8).map((week) => ({
                        label: week.label,
                        value: week.totalSubmissions,
                        hint: `${week.problemsSolved} solved · ${week.acceptedSubmissions} accepted`,
                      }))}
                      height={160}
                    />
                  </div>
                </Surface>
              </Reveal>

              <Reveal delay={60}>
                <Surface className="h-full">
                  <SurfaceHeader title="Languages" />
                  <div className="px-5 py-5">
                    <DistributionBars
                      rows={data.languages.slice(0, 5).map((stat) => ({
                        label: stat.language,
                        value: stat.totalSubmissions,
                        share: stat.usageSharePct,
                      }))}
                      max={100}
                      formatValue={(value) => `${value.toFixed(0)}%`}
                    />
                  </div>
                </Surface>
              </Reveal>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-3">
              {data.difficulties.map((stat, index) => (
                <Reveal key={stat.difficulty} delay={index * 50}>
                  <Surface className="h-full p-5">
                    <DifficultyBadge difficulty={stat.difficulty} />
                    <div className="mt-4 flex items-baseline gap-2">
                      <span className="font-technical text-2xl text-text-primary tabular-nums">
                        {stat.solvedProblems}
                      </span>
                      <span className="font-technical-sm text-text-faint">
                        of {stat.totalProblems} solved
                      </span>
                    </div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-card">
                      <span
                        className="block h-full rounded-full"
                        style={{
                          width: `${stat.totalProblems ? (stat.solvedProblems / stat.totalProblems) * 100 : 0}%`,
                          backgroundColor:
                            stat.difficulty === "Easy"
                              ? "var(--color-easy)"
                              : stat.difficulty === "Medium"
                                ? "var(--color-medium)"
                                : "var(--color-hard)",
                        }}
                        aria-hidden="true"
                      />
                    </div>
                    <div className="mt-2 font-technical-sm text-text-faint">
                      {formatPercent(stat.acceptanceRatePct, 0)} acceptance
                    </div>
                  </Surface>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------ knowledge */}
        <section id="knowledge" aria-labelledby="knowledge-heading" className="border-b border-border-soft bg-surface/40">
          <div className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-20">
            <SectionHeading
              eyebrow="Knowledge"
              title="Your problems, connected"
              description="Every problem links to the topics it uses, the approaches you tried, the languages you reached for, and the mistakes you made. Select a node to follow the thread."
              id="knowledge-heading"
              icon={<Network className="h-4 w-4 text-accent-ink" aria-hidden="true" />}
            />

            <Reveal delay={60} className="mt-10">
              <Surface className="overflow-hidden">
                <KnowledgeGraphPanel
                  graph={knowledge.graph}
                  centerId={problemIdFor("3sum")}
                  height={440}
                />
              </Surface>
            </Reveal>
          </div>
        </section>

        {/* ------------------------------------------------------------ revision */}
        <section id="revision" aria-labelledby="revision-heading" className="border-b border-border-soft">
          <div className="mx-auto w-full max-w-[1200px] px-5 py-16 md:px-8 md:py-20">
            <SectionHeading
              eyebrow="Revision"
              title="It also tells you what to revisit"
              description="A deterministic priority score weighs difficulty, failure history, recency and topic weakness — so the queue is explainable, not magical."
              id="revision-heading"
              icon={<RotateCw className="h-4 w-4 text-accent-ink" aria-hidden="true" />}
            />

            <Reveal delay={60} className="mt-10">
              <Surface>
                <SurfaceHeader
                  title="Revision queue"
                  description={`${revision.length} items scored`}
                  action={
                    <Button variant="outline" size="sm" asChild>
                      <Link href="/revision">
                        Open queue
                        <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </Link>
                    </Button>
                  }
                />
                <div className="flex flex-col">
                  {revision.slice(0, 4).map((item) => (
                    <Link
                      key={item.problemId}
                      href={`/problems?slug=${item.slug}`}
                      className="press group flex items-center gap-4 border-b border-border-soft px-5 py-4 last:border-0 hover:bg-surface-hover"
                    >
                      <DifficultyBadge difficulty={item.difficulty} />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-body-sm font-medium text-text-primary">
                          {item.title}
                        </div>
                        <div className="mt-0.5 truncate text-body-sm text-text-muted">
                          {item.reason}
                        </div>
                      </div>
                      <span className="hidden shrink-0 items-center gap-2 sm:flex">
                        <span className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-card">
                          <span
                            className="block h-full bg-accent"
                            style={{ width: `${Math.min(100, (item.priorityScore / 9) * 100)}%` }}
                            aria-hidden="true"
                          />
                        </span>
                        <span className="w-8 text-right font-technical-sm text-accent-ink tabular-nums">
                          {item.priorityScore.toFixed(1)}
                        </span>
                      </span>
                    </Link>
                  ))}
                </div>
              </Surface>
            </Reveal>
          </div>
        </section>

        {/* ------------------------------------------------------------- final CTA */}
        <section aria-labelledby="cta-heading" className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-dots opacity-50" aria-hidden="true" />
          <div className="relative mx-auto flex w-full max-w-[1200px] flex-col items-start px-5 py-20 md:px-8 md:py-28">
            <h2 id="cta-heading" className="text-display-lg max-w-[20ch] text-text-primary">
              Your code has a history. Make it useful.
            </h2>
            <p className="mt-5 max-w-[52ch] text-body-lg text-text-muted">
              Import the submissions you already have. CodeMemory indexes them,
              connects them, and remembers the parts worth revisiting.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button variant="accent" size="lg" asChild>
                <Link href="/dashboard">
                  Open CodeMemory
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button variant="ghost" size="lg" asChild>
                <Link href="/problems">Browse problems</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

function Stat({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="flex items-baseline gap-2">
      <span
        className={cnStat(accent)}
      >
        {value}
      </span>
      <span className="font-technical-sm text-text-faint">{label}</span>
    </div>
  );
}

function cnStat(accent?: boolean): string {
  return [
    "font-technical",
    "text-lg",
    "tabular-nums",
    accent ? "text-accent-ink" : "text-text-primary",
  ].join(" ");
}

function SectionHeading({
  eyebrow,
  title,
  description,
  id,
  icon,
}: {
  eyebrow: string;
  title: string;
  description: string;
  id: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="max-w-[64ch]">
      <span className="eyebrow flex items-center gap-2">
        {icon}
        {eyebrow}
      </span>
      <h2 id={id} className="text-display-lg mt-3 text-text-primary">
        {title}
      </h2>
      <p className="mt-4 text-body-lg text-text-muted">{description}</p>
    </div>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-border-soft">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col items-start justify-between gap-4 px-5 py-8 sm:flex-row sm:items-center md:px-8">
        <span className="font-technical-sm text-text-faint">
          CodeMemory · local-first coding memory
        </span>
        <nav aria-label="Footer" className="flex items-center gap-5">
          <Link href="/dashboard" className="font-technical-sm text-text-faint hover:text-text-muted">
            Dashboard
          </Link>
          <Link href="/analytics" className="font-technical-sm text-text-faint hover:text-text-muted">
            Analytics
          </Link>
          <Link href="/knowledge" className="font-technical-sm text-text-faint hover:text-text-muted">
            Knowledge
          </Link>
          <Link href="/settings" className="font-technical-sm text-text-faint hover:text-text-muted">
            Settings
          </Link>
        </nav>
      </div>
    </footer>
  );
}
