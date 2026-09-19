import Link from "next/link";
import { ArrowUpRight, Flame, Target, Clock, TrendingUp } from "lucide-react";
import { getDashboardData } from "@/lib/data";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { StatStrip } from "@/components/app/stat-strip";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Timeline } from "@/components/app/timeline";
import { ActivityHeatmap } from "@/components/charts/activity-heatmap";
import { BarChart } from "@/components/charts/bar-chart";
import { DistributionBars } from "@/components/charts/distribution";
import { SolutionEvolution } from "@/components/app/solution-evolution";
import { DifficultyBadge } from "@/components/ui/badges";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/system/reveal";
import { getEvolutionStory } from "@/lib/mock/snippets";
import { formatPercent, formatNumber, formatRelative } from "@/lib/format";

export const metadata = { title: "Overview" };

export default function DashboardPage() {
  const data = getDashboardData();
  const story = getEvolutionStory("3sum");
  const { overview } = data;

  const recentWeeks = data.progress.slice(-8);

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Overview"
          title={greeting()}
          description="Your coding memory, as it stands today. Everything below is generated from your own submission history."
          actions={
            <>
              <Button variant="outline" size="sm" asChild>
                <Link href="/analytics">
                  Analytics
                  <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </Button>
              <Button variant="primary" size="sm" asChild>
                <Link href="/revision">Open revision queue</Link>
              </Button>
            </>
          }
        />

        <StatStrip
          stats={[
            { label: "Problems solved", value: overview.acceptedProblems, hint: `${overview.unsolvedProblems} still open` },
            { label: "Submissions", value: overview.totalSubmissions, hint: `${overview.totalAttempts} attempts` },
            { label: "Acceptance rate", value: formatPercent(overview.overallAcceptanceRatePct) },
            { label: "Current streak", value: `${overview.currentStreakDays}d`, hint: `Best ${overview.longestStreakDays}d`, accent: true },
            { label: "Active days / 30", value: `${overview.activeDaysLast30}`, hint: formatPercent((overview.activeDaysLast30 / 30) * 100, 0) },
          ]}
        />

        <Reveal>
          <Surface className="overflow-hidden">
            <SurfaceHeader
              eyebrow="Memory trace"
              title="Solving activity"
              description="Every submission, mapped to the day it happened."
              action={
                <span className="inline-flex items-center gap-1.5 font-technical-sm text-text-muted">
                  <Flame className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
                  {overview.currentStreakDays}-day streak
                </span>
              }
            />
            <div className="px-5 py-5">
              <ActivityHeatmap days={data.activity} />
              <Legend total={overview.totalSubmissions} shown={totalActivity(data.activity)} />
            </div>
          </Surface>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <Reveal className="lg:col-span-2">
            <Surface className="h-full">
              <SurfaceHeader
                eyebrow="Recent"
                title="Activity timeline"
                action={
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/submissions">All submissions</Link>
                  </Button>
                }
              />
              <div className="px-5 py-5">
                <Timeline events={data.timeline} limit={8} />
              </div>
            </Surface>
          </Reveal>

          <Reveal delay={60}>
            <Surface className="h-full">
              <SurfaceHeader eyebrow="Queue" title="Revision signals" />
              <div className="flex flex-col">
                {data.revisionQueue.map((item) => (
                  <Link
                    key={item.problemId}
                    href={`/problems?slug=${item.slug}`}
                    className="press group flex items-center gap-3 border-b border-border-soft px-5 py-3.5 last:border-0 hover:bg-surface-hover"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-body-sm font-medium text-text-primary">
                        {item.title}
                      </div>
                      <div className="mt-1 flex items-center gap-2">
                        <DifficultyBadge difficulty={item.difficulty} />
                        <span className="font-technical-sm text-text-faint">
                          {formatRelative(item.lastActivityAt)}
                        </span>
                      </div>
                    </div>
                    <PriorityScore value={item.priorityScore} />
                  </Link>
                ))}
                <div className="p-3">
                  <Button variant="subtle" size="sm" className="w-full" asChild>
                    <Link href="/revision">Review {formatNumber(data.revisionQueue.length)} more</Link>
                  </Button>
                </div>
              </div>
            </Surface>
          </Reveal>
        </div>

        <Reveal>
          {story ? (
            <Surface className="overflow-hidden">
              <SolutionEvolution story={story} />
            </Surface>
          ) : null}
        </Reveal>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <Reveal>
            <Surface className="h-full">
              <SurfaceHeader
                eyebrow="Weekly"
                title="Submissions per week"
                action={<TrendingUp className="h-4 w-4 text-text-faint" aria-hidden="true" />}
              />
              <div className="px-5 py-5">
                <BarChart
                  data={recentWeeks.map((week) => ({
                    label: week.label,
                    value: week.totalSubmissions,
                    hint: `${week.problemsSolved} solved · ${week.acceptedSubmissions} accepted`,
                  }))}
                  height={150}
                />
              </div>
            </Surface>
          </Reveal>

          <Reveal delay={60}>
            <Surface className="h-full">
              <SurfaceHeader eyebrow="Languages" title="Language usage" />
              <div className="px-5 py-5">
                <DistributionBars
                  rows={data.languages.slice(0, 6).map((stat) => ({
                    label: stat.language,
                    value: stat.totalSubmissions,
                    share: stat.usageSharePct,
                    hint: `${formatPercent(stat.acceptanceRatePct)} accepted`,
                  }))}
                  max={100}
                  formatValue={(value) => `${value.toFixed(0)}%`}
                />
              </div>
            </Surface>
          </Reveal>

          <Reveal delay={120}>
            <Surface className="h-full">
              <SurfaceHeader eyebrow="Difficulty" title="Solved by difficulty" />
              <div className="px-5 py-5">
                <DistributionBars
                  rows={data.difficulties.map((stat) => ({
                    label: stat.difficulty,
                    value: stat.solvedProblems,
                    share: stat.totalProblems,
                    color: difficultyColor(stat.difficulty),
                    hint: `${stat.solvedProblems} of ${stat.totalProblems} solved`,
                  }))}
                  formatValue={(value) => String(value)}
                />
                <div className="mt-4 flex items-center gap-4 border-t border-border-soft pt-4">
                  <span className="inline-flex items-center gap-1.5 text-caption text-text-muted">
                    <Target className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
                    First-try acceptance {formatPercent(overview.firstAttemptAcceptanceRatePct)}
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-caption text-text-muted">
                    <Clock className="h-3.5 w-3.5 text-text-faint" aria-hidden="true" />
                    Avg {overview.avgAttemptsPerSolvedProblem.toFixed(1)} attempts / solved
                  </span>
                </div>
              </div>
            </Surface>
          </Reveal>
        </div>

        <Reveal>
          <Surface>
            <SurfaceHeader
              eyebrow="Weak spots"
              title="Where you struggle"
              description="Problems with the most failed submissions. These feed the revision queue."
              action={
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/analytics">Full analytics</Link>
                </Button>
              }
            />
            <div className="flex flex-col">
              {data.struggles.map((struggle) => (
                <Link
                  key={struggle.problemId}
                  href={`/problems?slug=${struggle.slug}`}
                  className="press group flex items-center gap-4 border-b border-border-soft px-5 py-3.5 last:border-0 hover:bg-surface-hover"
                >
                  <DifficultyBadge difficulty={struggle.difficulty} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-body-sm font-medium text-text-primary">
                      {struggle.title}
                    </div>
                    <div className="mt-0.5 truncate font-technical-sm text-text-faint">
                      {struggle.topics.join(" · ")}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-4">
                    <span className="font-technical-sm text-text-muted">
                      {struggle.totalAttempts} attempts
                    </span>
                    <span className="font-technical-sm text-error">
                      {struggle.failedSubmissions} failed
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </Surface>
        </Reveal>
      </PageSection>
    </PageContainer>
  );
}

function Legend({ total, shown }: { total: number; shown: number }) {
  return (
    <div className="mt-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-1.5">
        <span className="font-technical-sm text-text-faint">Less</span>
        {[0.16, 0.32, 0.55, 0.85].map((opacity) => (
          <span
            key={opacity}
            className="h-2.5 w-2.5 rounded-[2px]"
            style={{ backgroundColor: `rgba(255,161,22,${opacity})` }}
            aria-hidden="true"
          />
        ))}
        <span className="font-technical-sm text-text-faint">More</span>
      </div>
      <span className="font-technical-sm text-text-faint">
        {formatNumber(shown)} of {formatNumber(total)} submissions shown
      </span>
    </div>
  );
}

function totalActivity(days: { submissions: number }[]): number {
  return days.reduce((sum, day) => sum + day.submissions, 0);
}

function PriorityScore({ value }: { value: number }) {
  const pct = Math.min(100, Math.round((value / 10) * 100));
  return (
    <div className="flex shrink-0 flex-col items-end gap-1">
      <span className="font-technical-sm font-medium text-accent">{value.toFixed(1)}</span>
      <span className="h-1 w-12 overflow-hidden rounded-full bg-surface-card">
        <span
          className="block h-full bg-accent"
          style={{ width: `${pct}%` }}
          aria-hidden="true"
        />
      </span>
    </div>
  );
}

function difficultyColor(difficulty: string): string {
  if (difficulty === "Easy") return "var(--color-easy)";
  if (difficulty === "Medium") return "var(--color-medium)";
  if (difficulty === "Hard") return "var(--color-hard)";
  return "var(--color-text-muted)";
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 5) return "Still up?";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}
