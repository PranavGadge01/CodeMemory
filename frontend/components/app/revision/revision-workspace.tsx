"use client";

import * as React from "react";
import Link from "next/link";
import { Check, Clock } from "lucide-react";
import type { RevisionQueueItem } from "@/lib/types";
import {
  getRevisionQueue,
  markProblemReviewed,
  ApiError,
} from "@/lib/api";
import { StatStrip } from "@/components/app/stat-strip";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { DifficultyBadge } from "@/components/ui/badges";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/primitives";
import { ScoreBreakdown } from "@/components/app/revision/score-breakdown";
import { ErrorState } from "@/components/app/data-states";
import { formatRelative } from "@/lib/format";
import { cn } from "@/lib/utils";

const DAY_MS = 24 * 60 * 60 * 1000;

/** A scheduled item comes due 30 days after its last touch — the same rule the queue itself applies. */
const SCHEDULED_HORIZON = 30;

const STATUS_VARIANT: Record<RevisionQueueItem["status"], "error" | "warning" | "info" | "success"> = {
  Overdue: "error",
  Due: "warning",
  Scheduled: "info",
  Learned: "success",
};

const CONFIDENCE_VARIANT: Record<RevisionQueueItem["confidence"], "error" | "warning" | "success"> = {
  Low: "error",
  Medium: "warning",
  High: "success",
};

const CONFIDENCE_VALUE: Record<RevisionQueueItem["confidence"], number> = {
  Low: 1,
  Medium: 2,
  High: 3,
};

const TOPICS: { value: string; label: string }[] = [
  { value: "all", label: "All topics" },
  { value: "dynamic-programming", label: "Dynamic Programming" },
  { value: "array", label: "Array" },
  { value: "tree", label: "Tree" },
  { value: "graph", label: "Graph" },
];

/**
 * Revision workspace.
 *
 * The queue is a focused list, not a table: one row per thing to revisit, with
 * the scoring breakdown for whichever row has focus. "Mark reviewed" records
 * the review through the API; "Snooze 7d" stays a local UI action because the
 * backend exposes no snooze.
 */
export function RevisionWorkspace() {
  const [queue, setQueue] = React.useState<RevisionQueueItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<ApiError | null>(null);
  const [topic, setTopic] = React.useState("all");
  // Bumped by Retry/Refresh: those refetch the *same* topic, which alone would
  // leave the effect's dependency list unchanged and skip the request.
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [reviewing, setReviewing] = React.useState(false);
  const [reviewError, setReviewError] = React.useState<ApiError | null>(null);

  const load = React.useCallback(async (topicFilter: string) => {
    try {
      const next = await getRevisionQueue({
        limit: 50,
        topic: topicFilter !== "all" ? topicFilter : undefined,
      });
      setQueue(next);
      setSelectedId(next[0]?.problemId ?? null);
      setError(null);
    } catch (failure) {
      setError(
        failure instanceof ApiError
          ? failure
          : new ApiError("Unexpected error", "ERROR", 0),
      );
      setQueue([]);
      setSelectedId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    // The await is what keeps this legal: every setState below happens in the
    // continuation, never synchronously in the effect body.
    void (async () => {
      await load(topic);
    })();
  }, [topic, refreshKey, load]);

  const selected = React.useMemo(
    () => queue.find((item) => item.problemId === selectedId) ?? null,
    [queue, selectedId],
  );

  /**
   * Refetch. Topic changes and retries both flip loading back on here, from the
   * handler rather than the effect — the effect only ever reads, never sets.
   */
  function reload(nextTopic: string) {
    setTopic(nextTopic);
    setRefreshKey((previous) => previous + 1);
    setLoading(true);
  }

  async function markReviewed() {
    if (!selected) return;
    const item = selected;
    setReviewing(true);
    setReviewError(null);
    try {
      await markProblemReviewed(item.slug);
      setQueue((previous) => {
        const next = previous.filter((candidate) => candidate.problemId !== item.problemId);
        // Move focus to the next item in priority order rather than leaving the
        // panel pointing at something that is no longer queued.
        setSelectedId(next[0]?.problemId ?? null);
        return next;
      });
    } catch (failure) {
      setReviewError(
        failure instanceof ApiError
          ? failure
          : new ApiError("Unexpected error", "ERROR", 0),
      );
    } finally {
      setReviewing(false);
    }
  }
  /** Local-only: the backend has no snooze, so the row retires for this session. */
  function snooze() {
    if (!selected) return;
    const item = selected;
    setQueue((previous) => {
      const next = previous.filter((candidate) => candidate.problemId !== item.problemId);
      setSelectedId(next[0]?.problemId ?? null);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <StatStrip
          className="sm:grid-cols-4 lg:grid-cols-4"
          stats={[
            { label: "In queue", value: "—" },
            { label: "Overdue", value: "—" },
            { label: "Avg confidence", value: "—" },
            { label: "Next scheduled", value: "—" },
          ]}
        />
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          <Surface className="lg:col-span-7">
            <SurfaceHeader eyebrow="Queue" title="What to revisit" />
            <div className="p-5">
              <div className="animate-pulse rounded-md bg-surface-card" aria-hidden="true">
                <div className="h-12 border-b border-border-soft" />
                <div className="h-12 border-b border-border-soft" />
                <div className="h-12" />
              </div>
            </div>
          </Surface>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6">
        <Surface>
          <ErrorState error={error} onRetry={() => reload(topic)} />
        </Surface>
      </div>
    );
  }

  const overdue = queue.filter((item) => item.status === "Overdue").length;
  const confidenceLabel = averageConfidence(queue);
  const nextScheduled = nextScheduledAt(queue);

  return (
    <div className="flex flex-col gap-6">
      <StatStrip
        className="sm:grid-cols-4 lg:grid-cols-4"
        stats={[
          { label: "In queue", value: queue.length, hint: "Sorted by priority" },
          {
            label: "Overdue",
            value: overdue,
            hint: overdue ? "Past their revisit window" : "Nothing past due",
            accent: overdue > 0,
          },
          { label: "Avg confidence", value: confidenceLabel, hint: confidenceHint(queue) },
          { label: "Next scheduled", value: nextScheduled, hint: "From last activity" },
        ]}
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <Surface className="lg:col-span-7">
          <SurfaceHeader
            eyebrow="Queue"
            title="What to revisit"
            description="Ordered by priority score. Select a row to see how it was computed."
            action={
              <div className="flex items-center gap-3">
                <TopicSelect value={topic} onChange={reload} />
                <span className="font-technical-sm text-text-faint">
                  {queue.length} item{queue.length === 1 ? "" : "s"}
                </span>
              </div>
            }
          />
          {queue.length === 0 ? (
            <EmptyState
              icon={<Check className="h-4 w-4 text-success" aria-hidden="true" />}
              title="Queue cleared"
              description="Everything has been reviewed or snoozed for this session. New items appear as your submission history grows."
              action={
                <Button variant="outline" size="sm" onClick={() => reload(topic)}>
                  Refresh queue
                </Button>
              }
            />
          ) : (
            <div className="flex flex-col">
              {queue.map((item, index) => (
                <QueueRow
                  key={item.problemId}
                  item={item}
                  rank={index + 1}
                  selected={item.problemId === selectedId}
                  onSelect={() => setSelectedId(item.problemId)}
                />
              ))}
            </div>
          )}
        </Surface>

        <div className="lg:col-span-5">
          <Surface className="lg:sticky lg:top-16">
            <SurfaceHeader
              eyebrow="Scoring"
              title="Priority breakdown"
              description="Why this problem ranks where it does."
            />
            <div className="px-5 py-5">
              {selected ? (
                <>
                  <ScoreBreakdown item={selected} />
                  {reviewError ? (
                    <div className="mt-4">
                      <ErrorState
                        error={reviewError}
                        onRetry={() => void markReviewed()}
                      />
                    </div>
                  ) : null}
                  <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border-soft pt-4">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => void markReviewed()}
                      disabled={reviewing}
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      {reviewing ? "Recording…" : "Mark reviewed"}
                    </Button>
                    <Button variant="outline" size="sm" onClick={snooze}>
                      <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                      Snooze 7d
                    </Button>
                    <Button variant="ghost" size="sm" asChild>
                      <Link href={`/problems?slug=${selected.slug}`}>Open problem</Link>
                    </Button>
                  </div>
                </>
              ) : (
                <div className="py-10 text-center text-body-sm text-text-muted">
                  Select a problem in the queue to see how its revision score was computed.
                </div>
              )}
            </div>
          </Surface>
        </div>
      </div>
    </div>
  );
}

function QueueRow({
  item,
  rank,
  selected,
  onSelect,
}: {
  item: RevisionQueueItem;
  rank: number;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "press group flex w-full flex-wrap items-center gap-x-3 gap-y-2 border-b border-border-soft px-4 py-3.5 text-left last:border-0 transition-colors duration-micro",
        selected ? "bg-surface-active" : "hover:bg-surface-hover",
      )}
    >
      <span className="w-5 shrink-0 text-center font-technical-sm tabular-nums text-text-faint">
        {String(rank).padStart(2, "0")}
      </span>
      <DifficultyBadge difficulty={item.difficulty} className="hidden sm:inline-flex" />
      <div className="min-w-0 flex-1">
        <div className="truncate text-body-sm font-medium text-text-primary">{item.title}</div>
        <div className="mt-0.5 truncate text-body-sm text-text-muted">{item.reason}</div>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {item.topics.slice(0, 3).map((topic) => (
            <Badge key={topic} variant="outline">
              {topic}
            </Badge>
          ))}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2.5">
        <span className="hidden font-technical-sm text-text-faint md:inline">
          {formatRelative(item.lastActivityAt)}
        </span>
        <Badge variant={STATUS_VARIANT[item.status]}>{item.status}</Badge>
        <Badge variant={CONFIDENCE_VARIANT[item.confidence]} className="hidden sm:inline-flex">
          {item.confidence}
        </Badge>
        <PriorityScore value={item.priorityScore} />
      </div>
    </button>
  );
}

function PriorityScore({ value }: { value: number }) {
  const pct = Math.min(100, Math.round((value / 10) * 100));
  return (
    <div className="flex shrink-0 flex-col items-end gap-1">
      <span className="font-technical-sm font-medium text-accent tabular-nums">
        {value.toFixed(1)}
      </span>
      <span className="h-1 w-12 overflow-hidden rounded-full bg-surface-card" aria-hidden="true">
        <span className="block h-full bg-accent" style={{ width: `${pct}%` }} />
      </span>
    </div>
  );
}

function TopicSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative">
      <label htmlFor="revision-topic" className="sr-only">
        Filter queue by topic
      </label>
      <select
        id="revision-topic"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          "h-8 appearance-none rounded-md border border-border bg-surface-card pl-2.5 pr-8 text-body-sm text-text-primary",
          "transition-colors duration-micro ease-standard",
          "hover:border-border-strong focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40",
        )}
      >
        {TOPICS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <span
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-faint"
        aria-hidden="true"
      >
        ▾
      </span>
    </div>
  );
}

function averageConfidence(items: RevisionQueueItem[]): string {
  if (items.length === 0) return "—";
  const mean =
    items.reduce((sum, item) => sum + CONFIDENCE_VALUE[item.confidence], 0) / items.length;
  if (mean >= 2.5) return "High";
  if (mean >= 1.75) return "Medium";
  return "Low";
}

function confidenceHint(items: RevisionQueueItem[]): string {
  if (items.length === 0) return "Queue empty";
  const counts = { Low: 0, Medium: 0, High: 0 };
  for (const item of items) counts[item.confidence] += 1;
  return `${counts.Low} low · ${counts.Medium} medium · ${counts.High} high`;
}

/** Earliest moment a scheduled item comes due again. */
function nextScheduledAt(items: RevisionQueueItem[]): string {
  const scheduled = items.filter((item) => item.status === "Scheduled");
  if (scheduled.length === 0) return "—";
  const earliest = scheduled
    .map((item) => new Date(item.lastActivityAt).getTime() + SCHEDULED_HORIZON * DAY_MS)
    .sort((a, b) => a - b)[0];
  return formatRelative(new Date(earliest));
}
