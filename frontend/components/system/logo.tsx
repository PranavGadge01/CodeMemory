import { cn } from "@/lib/utils";

/**
 * CodeMemory mark.
 *
 * The glyph is a memory trace: a spine with three branches of differing
 * length, each ending in a node. It is the same "Problem → Attempt →
 * Pattern" relationship tree that the knowledge graph draws, which is what
 * makes it read as CodeMemory rather than as a generic logo shape.
 */
export function MemoryMark({
  className,
  size = 20,
  withGlow = false,
}: {
  className?: string;
  size?: number;
  withGlow?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={cn("shrink-0", className)}
      aria-hidden="true"
    >
      <rect
        x="0.75"
        y="0.75"
        width="22.5"
        height="22.5"
        rx="6"
        className={withGlow ? "fill-accent-soft" : "fill-surface-card"}
        stroke="currentColor"
        strokeOpacity={withGlow ? 0.35 : 0.16}
        strokeWidth="1"
      />
      <g className="text-accent" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M6 5.5v13" />
        <path d="M6 7.6h6.4" />
        <path d="M6 12h9.2" />
        <path d="M6 16.4h4.2" />
      </g>
      <g className="fill-accent">
        <circle cx="12.4" cy="7.6" r="1.7" />
        <circle cx="15.2" cy="12" r="1.7" />
        <circle cx="10.2" cy="16.4" r="1.7" />
      </g>
    </svg>
  );
}

export function Wordmark({
  className,
  showMark = true,
  markSize = 20,
  markClassName,
}: {
  className?: string;
  showMark?: boolean;
  markSize?: number;
  markClassName?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2 select-none", className)}>
      {showMark ? (
        <MemoryMark size={markSize} className={cn("text-accent", markClassName)} />
      ) : null}
      <span className="text-[15px] font-semibold leading-none tracking-[-0.01em] text-text-primary">
        Code<span className="text-text-muted">Memory</span>
      </span>
    </span>
  );
}

export function WordmarkCollapsed({ className }: { className?: string }) {
  return <MemoryMark size={22} className={cn("text-accent", className)} />;
}
