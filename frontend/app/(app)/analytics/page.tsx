import { getAnalytics } from "@/lib/data";
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
import { formatPercent } from "@/lib/format";

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
            <div className="px-5 py-5">
              <BarChart
                data={weeks.map((week) => ({
                  label: week.label,
                  value: week.totalSubmissions,
                  hint: `${week.totalSubmissions} submissions · ${week.problemsSolved} solved · ${week.acceptedSubmissions} accepted`,
                }))}
                height={170}
              />
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
                  height={190}
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
