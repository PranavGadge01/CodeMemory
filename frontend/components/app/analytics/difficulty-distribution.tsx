import type { Difficulty, DifficultyStat } from "@/lib/types";
import { DistributionBars } from "@/components/charts/distribution";
import { CHART_COLORS } from "@/components/charts/lib";
import { formatPercent } from "@/lib/format";

/**
 * Difficulty distribution.
 *
 * Two readings of the same numbers, stacked: solved-attempted per difficulty as
 * rows, then the share of every solved problem that each difficulty contributes
 * as one compact stacked bar. Length carries the comparison; colour is a
 * redundant cue (DESIGN.md §22 — no information by colour alone).
 */

const DIFFICULTY_COLOR: Record<Difficulty, string> = {
  Easy: CHART_COLORS.easy,
  Medium: CHART_COLORS.medium,
  Hard: CHART_COLORS.hard,
  Unknown: CHART_COLORS.muted,
};

export function DifficultyDistribution({ stats }: { stats: DifficultyStat[] }) {
  const solvedTotal = stats.reduce((sum, stat) => sum + stat.solvedProblems, 0);
  const mix = stats.filter((stat) => stat.solvedProblems > 0);

  const mixLabel =
    solvedTotal > 0
      ? `Difficulty mix of ${solvedTotal} solved problems: ${mix
          .map(
            (stat) =>
              `${stat.difficulty} ${formatPercent((stat.solvedProblems / solvedTotal) * 100, 0)}`,
          )
          .join(", ")}`
      : "No solved problems yet.";

  return (
    <div className="flex flex-col gap-5">
      <DistributionBars
        rows={stats.map((stat) => ({
          label: stat.difficulty,
          value: stat.solvedProblems,
          share: stat.totalProblems,
          color: DIFFICULTY_COLOR[stat.difficulty],
          hint: `${stat.solvedProblems} of ${stat.totalProblems} solved · ${formatPercent(
            stat.acceptanceRatePct,
          )} accepted`,
        }))}
        formatValue={(value) => String(value)}
      />

      <div>
        <div className="eyebrow mb-2">Mix of solved</div>
        <div
          role="img"
          aria-label={mixLabel}
          className="flex h-2.5 w-full overflow-hidden rounded-sm bg-surface-card"
        >
          {mix.map((stat) => (
            <span
              key={stat.difficulty}
              className="h-full"
              style={{
                width: `${(stat.solvedProblems / solvedTotal) * 100}%`,
                backgroundColor: DIFFICULTY_COLOR[stat.difficulty],
              }}
            />
          ))}
        </div>
        <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1">
          {mix.map((stat) => (
            <span
              key={stat.difficulty}
              className="inline-flex items-center gap-1.5 text-caption text-text-muted"
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: DIFFICULTY_COLOR[stat.difficulty] }}
                aria-hidden="true"
              />
              {stat.difficulty}
              <span className="font-technical-sm text-text-faint">
                {formatPercent((stat.solvedProblems / solvedTotal) * 100, 0)}
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
