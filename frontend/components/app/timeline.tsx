import Link from "next/link";
import { Check, Code2, FileText, Download, RotateCw, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TimelineEvent } from "@/lib/types";
import { formatRelative, formatDateTime } from "@/lib/format";

const ICON_FOR_KIND = {
  solved: { icon: Check, className: "text-success" },
  attempted: { icon: AlertCircle, className: "text-warning" },
  learned: { icon: FileText, className: "text-info" },
  revised: { icon: RotateCw, className: "text-accent" },
  imported: { icon: Download, className: "text-text-muted" },
} as const;

const LABEL_FOR_KIND: Record<TimelineEvent["kind"], string> = {
  solved: "Solved",
  attempted: "Attempted",
  learned: "Noted",
  revised: "System",
  imported: "Imported",
};

/**
 * Activity timeline — the "memory trace" rendered as prose.
 * Each entry hangs off a shared spine, which is the same Problem → Attempt →
 * Pattern relationship drawn in the knowledge graph.
 */
export function Timeline({
  events,
  className,
  limit,
}: {
  events: TimelineEvent[];
  className?: string;
  limit?: number;
}) {
  const shown = limit ? events.slice(0, limit) : events;

  return (
    <ol className={cn("relative flex flex-col", className)}>
      {shown.map((event, index) => {
        const config = ICON_FOR_KIND[event.kind];
        const Icon = config.icon;
        const isLast = index === shown.length - 1;

        return (
          <li key={event.id} className="relative flex gap-3.5">
            {/* Spine */}
            {!isLast ? (
              <span
                aria-hidden="true"
                className="absolute left-[9px] top-[22px] bottom-0 w-px bg-border-soft"
              />
            ) : null}
            <span
              className={cn(
                "relative z-10 mt-0.5 flex h-[19px] w-[19px] shrink-0 items-center justify-center rounded-full border border-border bg-surface-elevated",
                config.className,
              )}
            >
              <Icon className="h-[11px] w-[11px]" aria-hidden="true" strokeWidth={2} />
            </span>

            <div className="min-w-0 flex-1 pb-5">
              <div className="flex items-baseline justify-between gap-3">
                <div className="min-w-0">
                  {event.problemSlug ? (
                    <Link
                      href={`/problems?slug=${event.problemSlug}`}
                      className="truncate text-body-sm font-medium text-text-primary hover:text-accent"
                    >
                      {event.title}
                    </Link>
                  ) : (
                    <span className="truncate text-body-sm font-medium text-text-primary">
                      {event.title}
                    </span>
                  )}
                </div>
                <time
                  dateTime={event.occurredAt}
                  title={formatDateTime(event.occurredAt)}
                  className="shrink-0 font-technical-sm text-text-faint"
                >
                  {formatRelative(event.occurredAt)}
                </time>
              </div>
              <p className="mt-0.5 truncate text-body-sm text-text-muted" title={event.detail}>
                {event.detail}
              </p>
              <div className="mt-1 flex items-center gap-2">
                <span className="eyebrow">{LABEL_FOR_KIND[event.kind]}</span>
                {event.language ? (
                  <span className="inline-flex items-center gap-1 text-caption text-text-faint">
                    <Code2 className="h-3 w-3" aria-hidden="true" />
                    {event.language}
                  </span>
                ) : null}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
