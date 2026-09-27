import * as React from "react";
import { cn } from "@/lib/utils";
import { formatRuntime } from "@/lib/format";
import type { EvolutionStory } from "@/lib/mock/snippets";
import { DifficultyBadge, StatusBadge } from "@/components/ui/badges";

/**
 * The hero product window.
 *
 * This is the real product surface, not a marketing illustration: the attempt
 * trace below is the same "Problem → attempt → status" data the Submissions
 * and Knowledge pages render. Showing the product is the point.
 */
export function HeroPanel({ story, className }: { story: EvolutionStory; className?: string }) {
  const first = story.steps[0];
  const last = story.steps[story.steps.length - 1];
  if (!first || !last) return null;

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border border-border bg-surface shadow-floating",
        className,
      )}
    >
      {/* Window bar */}
      <div className="flex h-9 items-center gap-3 border-b border-border-soft bg-surface-elevated px-3">
        <span className="flex gap-1.5" aria-hidden="true">
          {[0, 1, 2].map((index) => (
            <span key={index} className="h-2 w-2 rounded-full bg-border-strong" />
          ))}
        </span>
        <span className="mx-auto flex items-center gap-2 font-technical-sm text-text-faint">
          <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
          codememory · local index
        </span>
      </div>

      <div className="grid grid-cols-[56px_minmax(0,1fr)] sm:grid-cols-[120px_minmax(0,1fr)]">
        {/* Mini sidebar */}
        <div className="hidden flex-col gap-1 border-r border-border-soft bg-surface px-2 py-3 sm:flex">
          {["Overview", "Problems", "Analytics", "Knowledge"].map((label, index) => (
            <div
              key={label}
              className={cn(
                "flex items-center gap-2 rounded-md px-2 py-1.5 text-body-sm",
                index === 1
                  ? "bg-surface-active font-medium text-text-primary"
                  : "text-text-faint",
              )}
            >
              <span
                className={cn("h-1.5 w-1.5 rounded-full", index === 1 ? "bg-accent" : "bg-border-strong")}
                aria-hidden="true"
              />
              <span className="hidden md:inline">{label}</span>
            </div>
          ))}
        </div>

        {/* Main surface */}
        <div className="min-w-0 px-4 py-4 sm:px-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2.5">
              <span className="font-technical-sm text-text-faint">prob_3sum</span>
              <DifficultyBadge difficulty={story.difficulty} />
            </div>
            <StatusBadge status={last.status} />
          </div>

          <div className="mt-1.5 text-body-md font-medium text-text-primary">{story.title}</div>

          {/* Attempt trace */}
          <div className="mt-5">
            <div className="eyebrow mb-3">Solution evolution</div>
            <AttemptTrace story={story} />
          </div>

          {/* Metadata rows */}
          <div className="mt-5 grid grid-cols-1 gap-px overflow-hidden rounded-md border border-border-soft bg-border-soft sm:grid-cols-2">
            <Meta label="Complexity" value={`${last.timeComplexity} · ${last.spaceComplexity}`} />
            <Meta label="Improvement" value={`${formatRuntime(first.runtimeMs)} → ${formatRuntime(last.runtimeMs)}`} accent />
            <Meta label="Patterns" value="Two Pointers · Sorting" />
            <Meta label="Memory" value="1 mistake · 2 notes" />
          </div>
        </div>
      </div>
    </div>
  );
}

function AttemptTrace({ story }: { story: EvolutionStory }) {
  return (
    <div className="relative">
      <div className="flex items-center">
        {story.steps.map((step, index) => {
          const accepted = step.status === "Accepted";
          return (
            <React.Fragment key={step.attempt}>
              {index > 0 ? (
                <span className="relative h-px flex-1 bg-border">
                  <span
                    className="absolute inset-0 bg-accent/40"
                    style={{ width: accepted ? "100%" : "0%" }}
                    aria-hidden="true"
                  />
                </span>
              ) : null}
              <div className="flex flex-col items-center gap-2">
                <span
                  className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-full border",
                    accepted
                      ? "border-success/40 bg-success-soft text-success"
                      : "border-warning/40 bg-warning-soft text-warning",
                  )}
                  aria-hidden="true"
                >
                  {accepted ? (
                    <CheckIcon />
                  ) : (
                    <span className="text-[10px] leading-none">{step.attempt}</span>
                  )}
                </span>
              </div>
            </React.Fragment>
          );
        })}
      </div>
      <div className="mt-2 flex">
        {story.steps.map((step, index) => (
          <div
            key={step.attempt}
            className={cn("min-w-0 flex-1", index === story.steps.length - 1 ? "text-right" : index === 0 ? "text-left" : "text-center")}
          >
            <div className="font-technical-sm text-text-secondary truncate">{step.approach}</div>
            <div className="mt-0.5 font-technical-sm text-text-faint">{formatRuntime(step.runtimeMs)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Meta({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-surface px-3 py-2.5">
      <div className="eyebrow">{label}</div>
      <div className={cn("mt-1 font-technical-sm", accent ? "text-accent" : "text-text-secondary")}>
        {value}
      </div>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path
        d="M2.5 6.5L4.75 8.75L9.5 3.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

