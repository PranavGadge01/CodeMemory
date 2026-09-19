import { cn } from "@/lib/utils";
import type { Difficulty, SubmissionStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

/**
 * Difficulty is signalled with colour *and* a text label, so the signal still
 * reaches users who cannot perceive the colour.
 */
const DIFFICULTY_CLASSES: Record<Difficulty, string> = {
  Easy: "border-success/25 bg-success-soft text-success",
  Medium: "border-accent-border bg-accent-soft text-accent",
  Hard: "border-error/25 bg-error-soft text-error",
  Unknown: "border-border bg-surface-card text-text-muted",
};

const DOT_CLASSES: Record<Difficulty, string> = {
  Easy: "bg-success",
  Medium: "bg-accent",
  Hard: "bg-error",
  Unknown: "bg-text-disabled",
};

export function DifficultyBadge({
  difficulty,
  className,
}: {
  difficulty: Difficulty;
  className?: string;
}) {
  return (
    <Badge
      variant="neutral"
      className={cn("gap-1.5", DIFFICULTY_CLASSES[difficulty], className)}
      aria-label={`${difficulty} difficulty`}
    >
      <span
        className={cn("h-1.5 w-1.5 rounded-full", DOT_CLASSES[difficulty])}
        aria-hidden="true"
      />
      {difficulty}
    </Badge>
  );
}

const STATUS_VARIANT: Record<
  SubmissionStatus,
  "success" | "error" | "warning" | "info" | "neutral"
> = {
  Accepted: "success",
  "Wrong Answer": "error",
  "Time Limit Exceeded": "warning",
  "Memory Limit Exceeded": "warning",
  "Runtime Error": "error",
  "Compile Error": "error",
  Unknown: "neutral",
};

const STATUS_GLYPH: Record<SubmissionStatus, string> = {
  Accepted: "✓",
  "Wrong Answer": "✕",
  "Time Limit Exceeded": "◷",
  "Memory Limit Exceeded": "◷",
  "Runtime Error": "✕",
  "Compile Error": "✕",
  Unknown: "·",
};

export function StatusBadge({
  status,
  className,
}: {
  status: SubmissionStatus;
  className?: string;
}) {
  return (
    <Badge
      variant={STATUS_VARIANT[status]}
      className={cn("gap-1.5", className)}
      aria-label={`Status: ${status}`}
    >
      <span aria-hidden="true" className="-mt-px text-[10px] leading-none">
        {STATUS_GLYPH[status]}
      </span>
      {status}
    </Badge>
  );
}
