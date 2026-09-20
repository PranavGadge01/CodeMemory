import { getAnalytics } from "@/lib/data";
import type { ProgressOverTime } from "@/lib/types";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { StatStrip } from "@/components/app/stat-strip";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { BarChart } from "@/components/charts/bar-chart";
import { LineChart } from "@/components/charts/line-chart";
import { DistributionBars } from "@/components/charts/distribution";
import { CHART_COLORS } from "@/components/charts/lib";
import { Reveal } from "@/components/system/reveal";
import { DifficultyDistribution } from "@/components/app/analytics/difficulty-distribution";
import { TopicTable } from "@/components/app/analytics/topic-table";
import { StruggleList } from "@/components/app/analytics/struggle-list";
import { formatNumber, formatPercent } from "@/lib/format";

export const metadata = { title: "Coding analytics" };

/** Weekly buckets shown across the time-series sections. ~18 weeks exist in a full history; 12 keeps the labels readable. */
const WEEKS_SHOWN = 12;

export default function AnalyticsPage() {
  const { overview, difficulties, topics, languages, progress, struggles } = getAnalytics();
  const weeks = progress.slice(-WEEKS_SHOWN);

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Analytics"
          title="Coding analytics"
          description="Derived from your own submissions — every number below is computed from problems you have actually attempted, nothing inferred or assumed."
        />

        <StatStrip
          className="lg:grid-cols-6"
          stats={[
            { label: "Problems", value: overview.totalProblems, hint: `${overview.acceptedProblems} solved` },
            { label: "Submissions", value: overview.totalSubmissions, hint: `${overview.totalAttempts} attempts` },
            { label: "Acceptance rate", value: formatPercent(overview.overallAcceptanceRatePct) },
            {
              label: "Avg attempts / solved",
              value: overview.avgAttemptsPerSolvedProblem.toFixed(1),
            },
            {
              label: "First-try acceptance",
              value: formatPercent(overview.firstAttemptAcceptanceRatePct),
              hint: "Accepted on attempt 1",
            },
            {
              label: "Current streak",
              value: `${overview.currentStreakDays}d`,
              hint: `Best ${overview.longestStreakDays}d`,
              accent: true,
            },
          ]}
        />

        <Reveal>
          <Surface>
            <SurfaceHeader
              eyebrow="Activity over time"
              title="Submissions per week"
              description={`Weekly submission volume across the last ${weeks.length} weeks.`}
            />
            <div className="flex flex-col gap-6 px-5 py-5 sm:flex-row sm:items-center sm:gap-10">
              <div className="min-w-0 flex-1 sm:max-w-[640px]">
                <BarChart
                  data={weeks.map((week) => ({
                    label: week.label,
                    value: week.totalSubmissions,
                    hint: `${week.totalSubmissions} submissions · ${week.problemsSolved} solved · ${week.acceptedSubmissions} accepted`,
                  }))}
                  height={190}
                />
              </div>
              <WeeklySummary weeks={weeks} />
            </div>
          </Surface>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
          <Reveal className="lg:col-span-3">
            <Surface className="h-full">
              <SurfaceHeader
                eyebrow="Progress"
                title="Solved vs attempted"
                description="Problems solved against total submissions, per week."
              />
              <div className="px-5 py-5">
                <LineChart
                  labels={weeks.map((week) => week.label)}
                  series={[
                    {
                      label: "Problems solved",
                      values: weeks.map((week) => week.problemsSolved),
                      color: CHART_COLORS.accent,
                      area: true,
                    },
                    {
                      label: "Total submissions",
                      values: weeks.map((week) => week.totalSubmissions),
                      color: CHART_COLORS.muted,
                    },
                  ]}
                  height={150}
                />
              </div>
            </Surface>
          </Reveal>

          <Reveal delay={60} className="lg:col-span-2">
            <Surface className="h-full">
              <SurfaceHeader
                eyebrow="Difficulty"
                title="Difficulty distribution"
                description="Solved against attempted, per difficulty."
              />
              <div className="px-5 py-5">
                <DifficultyDistribution stats={difficulties} />
              </div>
            </Surface>
          </Reveal>
        </div>

        <Reveal>
          <Surface>
            <SurfaceHeader
              eyebrow="Topics"
              title="Topic performance"
              description="Where your submission volume concentrates, and what it converts into."
            />
            <TopicTable topics={topics} />
          </Surface>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-5">
          <Reveal className="lg:col-span-2">
            <Surface className="h-full">
              <SurfaceHeader
                eyebrow="Languages"
                title="Language usage"
                description="Share of all submissions, per language."
              />
              <div className="px-5 py-5">
                <DistributionBars
                  rows={languages.map((stat, index) => ({
                    label: stat.language,
                    value: stat.usageSharePct,
                    // Languages are categorical — no colour carries meaning, so
                    // only the most-used language takes the accent.
                    color: index === 0 ? CHART_COLORS.accent : "rgba(255,255,255,0.18)",
                    hint: `${stat.totalSubmissions} submissions · ${formatPercent(stat.acceptanceRatePct)} accepted`,
                  }))}
                  max={100}
                  formatValue={(value) => `${value.toFixed(0)}%`}
                />
                <div className="mt-4 border-t border-border-soft pt-3 text-caption text-text-faint">
                  Acceptance rate per language is in each bar tooltip.
                </div>
              </div>
            </Surface>
          </Reveal>

          <Reveal delay={60} className="lg:col-span-3">
            <Surface className="h-full">
              <SurfaceHeader
                eyebrow="Weak spots"
                title="Struggle problems"
                description="Most failed submissions. These feed the revision queue."
              />
              <StruggleList struggles={struggles} />
            </Surface>
          </Reveal>
        </div>
      </PageSection>
    </PageContainer>
  );
}

/**
 * Compact companion to the weekly bar chart. It fills the card's right side
 * with a few facts derived from the same weeks, and nothing else — this is not
 * an insights panel; the page already carries the detail further down.
 */
function WeeklySummary({ weeks }: { weeks: ProgressOverTime[] }) {
  if (weeks.length === 0) return null;

  const total = weeks.reduce((sum, week) => sum + week.totalSubmissions, 0);
  const average = total / Math.max(1, weeks.length);
  const peak = weeks.reduce(
    (best, week) => (week.totalSubmissions > best.totalSubmissions ? week : best),
    weeks[0],
  );

  return (
    <aside className="w-full shrink-0 sm:w-48 sm:border-l sm:border-border-soft sm:pl-8">
      <span className="eyebrow">{weeks.length} weeks</span>
      <div className="mt-3 grid grid-cols-3 gap-3 sm:grid-cols-1 sm:gap-0 sm:divide-y sm:divide-border-soft">
        <SummaryFact label="Submissions" value={formatNumber(total)} />
        <SummaryFact label="Avg / week" value={average.toFixed(1)} />
        <SummaryFact label="Peak week" value={`${peak.label} · ${peak.totalSubmissions}`} />
      </div>
    </aside>
  );
}

function SummaryFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 sm:py-2.5 sm:first:pt-0 sm:last:pb-0">
      <div className="font-technical-sm text-text-faint">{label}</div>
      <div className="mt-0.5 truncate font-technical text-text-secondary tabular-nums">{value}</div>
    </div>
  );
}
