"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { ExternalLink, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DifficultyBadge, StatusBadge } from "@/components/ui/badges";
import { Separator } from "@/components/ui/primitives";
import {
  attemptCount,
  bestRuntime,
  languagesOf,
  lastActivityAt,
  latestAnalysis,
  solveStatus,
  submissionCount,
} from "@/lib/mock/derive";
import {
  formatDateTime,
  formatMemory,
  formatNumber,
  formatRelative,
  formatRuntime,
} from "@/lib/format";
import type { Attempt, Problem } from "@/lib/types";

/**
 * Problem detail drawer, opened from `/problems` rows.
 *
 * Visibility is a plain class flip owned by the parent: `problem` stays live
 * while the panel slides away, so the exit transition has something to render
 * against, and the enter direction is a one-shot CSS keyframe (see
 * `globals.css`). That keeps the component free of derived state, which in
 * turn keeps it clear of `setState`-in-effect. The portal targets `body` so
 * the panel escapes the transformed scroll-reveal wrapper.
 */
export function ProblemDrawer({
  problem,
  open,
  onClose,
}: {
  problem: Problem | null;
  open: boolean;
  onClose: () => void;
}) {
  const panelRef = React.useRef<HTMLDivElement>(null);

  // Portals target `document.body`, which does not exist on the server. React
  // hydrates against the server snapshot and then re-renders with the client
  // one, so a deep link can still open the drawer without a mismatch.
  const isClient = React.useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

  // Escape closes; focus returns to whatever opened it.
  React.useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previous?.focus?.();
    };
  }, [open, onClose]);

  // Keep the page behind still while the panel is up.
  React.useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  React.useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  if (!isClient || problem === null) return null;

  const status = solveStatus(problem);
  const analysis = latestAnalysis(problem);

  // The portal needs `document.body`, which does not exist during SSR.
  // `useSyncExternalStore` gives a client-only snapshot that React reconciles
  // after hydration, so a deep link can still open the drawer without a
  // server/client mismatch.
  if (!isClient) return null;

  return createPortal(
    <div className="fixed inset-0 z-50" aria-hidden={open ? undefined : "true"}>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close problem detail"
        tabIndex={open ? 0 : -1}
        className={cn(
          "absolute inset-0 bg-black/70 transition-opacity duration-ui ease-standard",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />
      <div
        ref={panelRef}
        tabIndex={-1}
        aria-modal="true"
        role="dialog"
        aria-label={problem.title}
        className={cn(
          "absolute right-0 top-0 flex h-full w-full flex-col border-l border-border bg-surface shadow-floating",
          "transition-transform duration-ui ease-standard sm:max-w-[480px]",
          open ? "drawer-in translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <div className="eyebrow mb-1.5">Problem detail</div>
            <h2 className="text-heading-md truncate text-text-primary">{problem.title}</h2>
            <div className="mt-1 truncate font-technical-sm text-text-faint">{problem.slug}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            tabIndex={open ? 0 : -1}
            className="press inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:bg-surface-hover hover:text-text-primary"
            aria-label="Close problem detail"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex flex-col gap-4 px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              <DifficultyBadge difficulty={problem.difficulty} />
              <Badge variant={status === "Solved" ? "success" : status === "Attempted" ? "warning" : "neutral"}>
                {status === "Solved" ? "Solved" : status}
              </Badge>
              <span className="font-technical-sm text-text-faint">{problem.platform}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {problem.topics.map((topic) => (
                <Badge key={topic} variant="outline">
                  {topic}
                </Badge>
              ))}
            </div>
          </div>

          <Separator />

          <dl className="grid grid-cols-2 gap-x-4 gap-y-4 px-5 py-4 sm:grid-cols-3">
            <Fact label="Attempts" value={formatNumber(attemptCount(problem))} />
            <Fact label="Submissions" value={formatNumber(submissionCount(problem))} />
            <Fact label="Languages" value={formatNumber(languagesOf(problem).length)} />
            <Fact
              label="Best runtime"
              value={bestRuntime(problem) === null ? "—" : formatRuntime(bestRuntime(problem))}
            />
            <Fact
              label="First seen"
              value={formatRelative(problem.createdAt)}
              title={formatDateTime(problem.createdAt)}
            />
            <Fact
              label="Last activity"
              value={formatRelative(lastActivityAt(problem))}
              title={formatDateTime(lastActivityAt(problem))}
            />
          </dl>

          {analysis ? (
            <>
              <Separator />
              <SectionLabel eyebrow="Best known solution" meta={analysis.approachName} />
              <div className="flex flex-col gap-3 px-5 py-4">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="accent">{`${analysis.timeComplexity} time`}</Badge>
                  <Badge variant="outline">{`${analysis.spaceComplexity} space`}</Badge>
                </div>
                {analysis.keyInsights.length > 0 ? (
                  <ul className="space-y-1.5">
                    {analysis.keyInsights.map((insight) => (
                      <li key={insight} className="flex gap-2 text-body-sm text-text-secondary">
                        <span className="mt-px text-accent" aria-hidden="true">
                          —
                        </span>
                        <span>{insight}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {analysis.tradeOffs ? (
                  <p className="text-body-sm text-text-muted">{analysis.tradeOffs}</p>
                ) : null}
                {analysis.bottleneck ? (
                  <p className="text-caption text-text-faint">{`Bottleneck: ${analysis.bottleneck}`}</p>
                ) : null}
              </div>
            </>
          ) : null}

          <Separator />
          <SectionLabel eyebrow="Attempts" meta={`${attemptCount(problem)} total`} />

          <div className="flex flex-col">
            {problem.attempts.map((attempt) => (
              <AttemptRow key={attempt.id} attempt={attempt} />
            ))}
          </div>

          <Separator />
          <SectionLabel
            eyebrow="Notes"
            meta={problem.notes.length > 0 ? `${problem.notes.length} saved` : "none"}
          />

          {problem.notes.length > 0 ? (
            <div className="flex flex-col">
              {problem.notes.map((note) => (
                <div key={note.id} className="border-b border-border-soft px-5 py-4 last:border-0">
                  <div className="flex items-center justify-between gap-3">
                    <Badge variant="outline">{note.noteType}</Badge>
                    <span
                      className="font-technical-sm text-text-faint"
                      title={formatDateTime(note.createdAt)}
                    >
                      {formatRelative(note.createdAt)}
                    </span>
                  </div>
                  <p className="mt-2 text-body-sm text-text-secondary">{note.content}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-5 py-5 text-body-sm text-text-faint">
              No notes saved for this problem yet.
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 border-t border-border px-5 py-3.5">
          <span className="mr-auto font-technical-sm text-text-faint">
            {`${submissionCount(problem)} submissions`}
          </span>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/submissions">All submissions</Link>
          </Button>
          {problem.url ? (
            <Button variant="outline" size="sm" asChild>
              <a href={problem.url} target="_blank" rel="noopener noreferrer">
                {`Open on ${problem.platform}`}
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            </Button>
          ) : null}
        </div>
      </div>
    </div>,
    document.body,
  );
}

function Fact({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div className="min-w-0">
      <dt className="eyebrow">{label}</dt>
      <dd
        className="mt-1 truncate font-technical text-text-primary tabular-nums"
        title={title ?? value}
      >
        {value}
      </dd>
    </div>
  );
}

function SectionLabel({ eyebrow, meta }: { eyebrow: string; meta?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border-soft px-5 py-3">
      <span className="eyebrow">{eyebrow}</span>
      {meta ? <span className="font-technical-sm text-text-faint">{meta}</span> : null}
    </div>
  );
}

function AttemptRow({ attempt }: { attempt: Attempt }) {
  const submission = attempt.submissions[0];
  const approach = attempt.approachSummary.replace(/^Attempt\s+\d+\s*—\s*/, "");

  return (
    <div className="border-b border-border-soft px-5 py-4 last:border-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-technical-sm font-medium text-text-primary">
            {`Attempt ${attempt.attemptNumber}`}
          </div>
          <div className="mt-0.5 text-body-sm text-text-secondary">{approach}</div>
        </div>
        <StatusBadge status={attempt.status} />
      </div>

      {submission ? (
        <div className="mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 font-technical-sm text-text-muted">
          <span>{submission.language}</span>
          <Dot />
          <span>{formatRuntime(submission.runtimeMs)}</span>
          <Dot />
          <span>{formatMemory(submission.memoryMb)}</span>
          <Dot />
          <span title={formatDateTime(submission.submittedAt)}>
            {formatRelative(submission.submittedAt)}
          </span>
        </div>
      ) : (
        <div className="mt-2.5 font-technical-sm text-text-faint">No submission recorded</div>
      )}

      {attempt.analysis ? (
        <div className="mt-2.5 font-technical-sm text-text-muted">
          <span className="text-accent">{attempt.analysis.timeComplexity}</span> time
          <span className="text-text-faint"> · </span>
          <span className="text-accent">{attempt.analysis.spaceComplexity}</span> space
        </div>
      ) : null}

      {attempt.mistakes.length > 0 ? (
        <ul className="mt-2.5 space-y-1">
          {attempt.mistakes.map((mistake) => (
            <li key={mistake} className="flex gap-2 text-caption text-text-muted">
              <span className="mt-px text-text-faint" aria-hidden="true">
                —
              </span>
              <span>{mistake}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function Dot() {
  return (
    <span className="text-text-faint" aria-hidden="true">
      ·
    </span>
  );
}
