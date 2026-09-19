import Link from "next/link";
import type { StruggleProblem } from "@/lib/types";
import { DifficultyBadge, StatusBadge } from "@/components/ui/badges";

/**
 * Problems with the most failed submissions — the raw material the revision
 * queue is scored from. Row pattern matches the dashboard's weak-spots list so
 * the same signal reads the same way in both places.
 */
export function StruggleList({ struggles }: { struggles: StruggleProblem[] }) {
  if (struggles.length === 0) {
    return (
      <div className="px-5 py-10 text-center text-body-sm text-text-muted">
        No problems with failed submissions. Everything accepted so far.
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {struggles.map((struggle) => (
        <Link
          key={struggle.problemId}
          href={`/problems?slug=${struggle.slug}`}
          className="press group flex items-center gap-4 border-b border-border-soft px-5 py-3.5 last:border-0 hover:bg-surface-hover"
        >
          <DifficultyBadge difficulty={struggle.difficulty} className="hidden sm:inline-flex" />
          <div className="min-w-0 flex-1">
            <div className="truncate text-body-sm font-medium text-text-primary">
              {struggle.title}
            </div>
            <div className="mt-0.5 truncate font-technical-sm text-text-faint">
              {struggle.topics.join(" · ")}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-4">
            <span className="hidden font-technical-sm text-text-muted sm:inline">
              {struggle.totalAttempts} attempts
            </span>
            <span className="font-technical-sm text-error">
              {struggle.failedSubmissions} failed
            </span>
            <StatusBadge status={struggle.status} className="hidden md:inline-flex" />
          </div>
        </Link>
      ))}
    </div>
  );
}
