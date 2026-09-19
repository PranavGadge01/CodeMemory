"use client";

import * as React from "react";
import { ArrowRight, Check, Clock, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRuntime } from "@/lib/format";
import type { EvolutionStory } from "@/lib/mock/snippets";
import { evolutionImprovement } from "@/lib/mock/snippets";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/badges";

const STATUS_GLYPH = {
  Accepted: <Check className="h-3 w-3" aria-hidden="true" />,
  "Wrong Answer": <span aria-hidden="true" className="text-[11px] leading-none">✕</span>,
  "Time Limit Exceeded": <Clock className="h-3 w-3" aria-hidden="true" />,
};

/**
 * Solution evolution — the strongest CodeMemory concept.
 *
 * A problem is shown as a *sequence*, not a final answer: each attempt keeps
 * its own approach, complexity and runtime, so the user can see how their
 * thinking moved rather than only what it landed on.
 */
export function SolutionEvolution({
  story,
  className,
  compact = false,
}: {
  story: EvolutionStory;
  className?: string;
  compact?: boolean;
}) {
  const [active, setActive] = React.useState(story.steps.length - 1);
  const step = story.steps[active];
  const improvement = evolutionImprovement(story);

  return (
    <div className={cn("flex flex-col", className)}>
      <div className="flex items-center justify-between gap-3 border-b border-border-soft px-5 py-3.5">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="eyebrow shrink-0">Solution evolution</span>
          <span className="text-body-sm font-medium text-text-primary truncate">{story.title}</span>
          <Badge variant="outline" className="hidden sm:inline-flex">
            {story.steps.length} attempts
          </Badge>
        </div>
        {improvement > 0 ? (
          <span className="inline-flex shrink-0 items-center gap-1.5 font-technical-sm text-success">
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            {improvement}% faster
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[230px_minmax(0,1fr)]">
        {/* Attempt rail */}
        <div
          role="tablist"
          aria-label="Attempts"
          className={cn(
            "flex flex-col gap-px border-border-soft p-2",
            compact ? "" : "lg:border-r",
          )}
        >
          {story.steps.map((candidate, index) => {
            const selected = index === active;
            return (
              <button
                key={candidate.attempt}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setActive(index)}
                className={cn(
                  "press flex flex-col items-start gap-1 rounded-md px-3 py-2.5 text-left",
                  selected
                    ? "bg-surface-active ring-1 ring-accent-border"
                    : "hover:bg-surface-hover",
                )}
              >
                <span className="flex w-full items-center justify-between gap-2">
                  <span
                    className={cn(
                      "font-technical-sm font-medium",
                      selected ? "text-accent" : "text-text-muted",
                    )}
                  >
                    Attempt {candidate.attempt}
                  </span>
                  <span
                    className={cn(
                      "flex h-4 w-4 items-center justify-center rounded-full",
                      candidate.status === "Accepted"
                        ? "bg-success-soft text-success"
                        : "bg-warning-soft text-warning",
                    )}
                    aria-hidden="true"
                  >
                    {STATUS_GLYPH[candidate.status]}
                  </span>
                </span>
                <span className="w-full truncate text-body-sm text-text-secondary">
                  {candidate.approach}
                </span>
                <span className="font-technical-sm text-text-faint">
                  {candidate.timeComplexity} · {formatRuntime(candidate.runtimeMs)}
                </span>
              </button>
            );
          })}
        </div>

        {/* Selected attempt */}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 border-b border-border-soft px-5 py-3">
            <StatusBadge status={step.status} />
            <Badge variant="neutral">{step.approach}</Badge>
            <span className="inline-flex items-center gap-1 font-technical-sm text-text-muted">
              <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
              {step.timeComplexity} time
            </span>
            <span className="inline-flex items-center gap-1 font-technical-sm text-text-muted">
              {step.spaceComplexity} space
            </span>
            <span className="ml-auto font-technical-sm text-text-faint">{step.language}</span>
          </div>

          <CodeBlock code={step.code} />

          <div className="border-t border-border-soft px-5 py-3.5">
            <div className="eyebrow mb-1.5">Why this attempt is here</div>
            <p className="text-body-sm text-text-muted">{step.note}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function CodeBlock({ code }: { code: string }) {
  const lines = code.split("\n");

  return (
    <div className="overflow-x-auto bg-[#050608]">
      <pre className="min-w-max py-4 font-mono text-[12.5px] leading-[1.65]">
        <code>
          {lines.map((line, index) => (
            <span key={index} className="flex">
              <span
                className="w-12 shrink-0 select-none pr-4 text-right text-text-disabled"
                aria-hidden="true"
              >
                {index + 1}
              </span>
              <span className="whitespace-pre text-text-secondary">{line || " "}</span>
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
