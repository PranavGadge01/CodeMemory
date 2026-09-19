"use client";

import * as React from "react";
import Link from "next/link";
import { Check, Clock } from "lucide-react";
import type { RevisionQueueItem } from "@/lib/types";
import { getRevisionQueue } from "@/lib/data";
import { StatStrip } from "@/components/app/stat-strip";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { DifficultyBadge } from "@/components/ui/badges";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/primitives";
import { ScoreBreakdown } from "@/components/app/revision/score-breakdown";
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

/**
 * Revision workspace.
 *
 * The queue is a focused list, not a table: one row per thing to revisit, with
 * the scoring breakdown for whichever row has focus. "Mark reviewed" and
 * "Snooze 7d" are local UI state only — there is no backend to call yet, so
 * both simply retire the row from the current session.
 */
export function RevisionWorkspace() {
  const [queue, setQueue] = React.useState<RevisionQueueItem[]>(() => getRevisionQueue());
  const [selectedId, setSelectedId] = React.useState<string | null>(() => queue[0]?.problemId ?? null);

  const selected = React.useMemo(
    () => queue.find((item) => item.problemId === selectedId) ?? null,
    [queue, selectedId],
  );

  function retire(id: string) {
    setQueue((previous) => {
      const next = previous.filter((item) => item.problemId !== id);
      const stillSelected = next.find((item) => item.problemId === selectedId);
      // Move focus to the next item in priority order rather than leaving the
      // panel pointing at something that is no longer queued.
      if (!stillSelected) setSelectedId(next[0]?.problemId ?? null);
      return next;
    });
  }

  function restore() {
    const fresh = getRevisionQueue();
    setQueue(fresh);
    setSelectedId(fresh[0]?.problemId ?? null);
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
              <span className="font-technical-sm text-text-faint">
                {queue.length} item{queue.length === 1 ? "" : "s"}
              </span>
            }
          />
          {queue.length === 0 ? (
            <EmptyState
              icon={<Check className="h-4 w-4 text-success" aria-hidden="true" />}
              title="Queue cleared"
              description="Everything has been reviewed or snoozed for this session. New items appear as your submission history grows."
              action={
                <Button variant="outline" size="sm" onClick={restore}>
                  Restore queue
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
                  <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border-soft pt-4">
                    <Button variant="primary" size="sm" onClick={() => retire(selected.problemId)}>
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      Mark reviewed
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => retire(selected.problemId)}>
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
