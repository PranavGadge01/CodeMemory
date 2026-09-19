import type { RevisionQueueItem } from "@/lib/types";
import { DifficultyBadge } from "@/components/ui/badges";
import { formatPercent } from "@/lib/format";

/**
 * Revision score breakdown.
 *
 * The one place CodeMemory shows its working. Every queue position is the same
 * weighted sum, and rendering the arithmetic component by component is what
 * makes the ranking legible instead of opaque.
 *
 *   P = 2.0·difficulty + 3.0·failure + 2.5·recency + 2.0·weakness − 1.5·recent
 *
 * Weights mirror the backend formula in `revision/revision_models.py`
 * (recomputed locally in `lib/mock/revision.ts`). If the weights change there,
 * they change here too.
 */

const WEIGHTS = {
  difficulty: 2.0,
  failure: 3.0,
  recency: 2.5,
  weakness: 2.0,
  recentSolvedPenalty: 1.5,
} as const;

/** Widest weight in the formula — the scale every contribution bar is drawn against. */
const MAX_WEIGHT = Math.max(...Object.values(WEIGHTS));

interface Component {
  key: string;
  label: string;
  weight: number;
  score: number;
  detail: string;
}

export function ScoreBreakdown({ item }: { item: RevisionQueueItem }) {
  const breakdown = item.breakdown;

  const components: Component[] = [
    {
      key: "difficulty",
      label: "Difficulty",
      weight: WEIGHTS.difficulty,
      score: breakdown.difficultyScore,
      detail: `${item.difficulty} problem — harder work is worth more attention.`,
    },
    {
      key: "failure",
      label: "Failure",
      weight: WEIGHTS.failure,
      score: breakdown.failureScore,
      detail:
        breakdown.recentSolvedPenalty > 0
          ? "Discounted by the recent-solved penalty below."
          : "Failed submissions, and any unsolved state.",
    },
    {
      key: "recency",
      label: "Recency",
      weight: WEIGHTS.recency,
      score: breakdown.recencyScore,
      detail: `${breakdown.daysSinceLastActivity} days since you last touched this problem.`,
    },
    {
      key: "weakness",
      label: "Weakness",
      weight: WEIGHTS.weakness,
      score: breakdown.weaknessScore,
      detail:
        breakdown.weaknessScore >= 0.5
          ? "Sits in a topic your history scores as weak."
          : "Topic is within your stronger areas.",
    },
  ];

  const contributions = components.map((component) => ({
    ...component,
    contribution: component.weight * component.score,
  }));
  const penaltyContribution = WEIGHTS.recentSolvedPenalty * breakdown.recentSolvedPenalty;
  const total =
    contributions.reduce((sum, component) => sum + component.contribution, 0) -
    penaltyContribution;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-heading-sm text-text-primary">{item.title}</div>
          <div className="mt-1.5">
            <DifficultyBadge difficulty={item.difficulty} />
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="font-technical text-2xl font-medium tabular-nums text-accent">
            {item.priorityScore.toFixed(2)}
          </div>
          <div className="eyebrow mt-0.5">Priority</div>
        </div>
      </div>

      <p className="text-body-sm text-text-muted">{item.reason}</p>

      <div className="rounded-md border border-border-soft bg-surface-card px-3.5 py-3">
        <div className="font-technical-sm text-text-faint">
          P = 2.0·d + 3.0·f + 2.5·r + 2.0·w − 1.5·s
        </div>
        <div className="mt-1.5 text-caption text-text-faint">
          Each component is a 0–1 signal times its weight. The bars show the contribution.
        </div>
      </div>

      <div className="flex flex-col gap-3.5" role="list" aria-label="Priority score components">
        {contributions.map(({ key, label, weight, score, contribution, detail }) => (
          <div key={key} role="listitem">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-body-sm text-text-secondary">{label}</span>
              <span className="font-technical-sm tabular-nums text-text-muted">
                {weight.toFixed(1)} × {score.toFixed(2)} ={" "}
                <span className="text-text-primary">{contribution.toFixed(2)}</span>
              </span>
            </div>
            <div
              className="mt-1.5 h-2 w-full overflow-hidden rounded-sm bg-surface-card"
              role="img"
              aria-label={`${label}: score ${score.toFixed(2)} of 1.00, weight ${weight.toFixed(1)}, contributes ${contribution.toFixed(2)} points`}
            >
              <span
                className="block h-full bg-accent"
                style={{ width: `${Math.max(2, (contribution / MAX_WEIGHT) * 100)}%` }}
              />
            </div>
            <div className="mt-1 text-caption text-text-faint">{detail}</div>
          </div>
        ))}

        <div role="listitem">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-body-sm text-text-secondary">Recent solved (penalty)</span>
            <span className="font-technical-sm tabular-nums text-text-muted">
              {WEIGHTS.recentSolvedPenalty.toFixed(1)} × {breakdown.recentSolvedPenalty.toFixed(2)} ={" "}
              <span className="text-error">−{penaltyContribution.toFixed(2)}</span>
            </span>
          </div>
          <div
            className="mt-1.5 h-2 w-full overflow-hidden rounded-sm bg-surface-card"
            role="img"
            aria-label={`Recent solved penalty: ${penaltyContribution.toFixed(2)} points subtracted`}
          >
            <span
              className="block h-full bg-error"
              style={{ width: `${Math.max(2, (penaltyContribution / MAX_WEIGHT) * 100)}%` }}
            />
          </div>
          <div className="mt-1 text-caption text-text-faint">
            {breakdown.recentSolvedPenalty > 0
              ? "Solved within the last 14 days — the memory is still fresh."
              : "Not applied: this problem was not solved recently."}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-border-soft pt-4">
        <span className="text-body-sm font-medium text-text-primary">Sum</span>
        <span className="font-technical tabular-nums text-text-primary">
          {total.toFixed(2)}
        </span>
      </div>
      <div className="-mt-3 flex items-center justify-between gap-3">
        <span className="text-caption text-text-faint">Confidence in this ranking</span>
        <span className="font-technical-sm tabular-nums text-text-muted">
          {formatPercent(item.confidence === "High" ? 92 : item.confidence === "Medium" ? 74 : 48, 0)}{" "}
          · {item.confidence}
        </span>
      </div>
    </div>
  );
}
