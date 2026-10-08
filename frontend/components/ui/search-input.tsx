"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function SearchInput({
  value,
  onChange,
  placeholder = "Search…",
  className,
  autoFocus,
  debounceMs = 0,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
  /**
   * Delay `onChange` until typing pauses. List filters use this so a keystroke
   * does not immediately trigger a server round trip; the input still echoes
   * every keystroke locally, and discrete dropdown changes are never debounced.
   */
  debounceMs?: number;
}) {
  const [draft, setDraft] = React.useState(value);
  const timer = React.useRef<number | null>(null);
  // The last value this input pushed up, so an echoed prop update cannot
  // clobber characters typed after the push.
  const pushed = React.useRef(value);

  React.useEffect(() => {
    if (value !== pushed.current) {
      pushed.current = value;
      setDraft(value);
    }
  }, [value]);

  React.useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    },
    [],
  );

  const shown = debounceMs > 0 ? draft : value;

  const handleChange = (next: string) => {
    if (debounceMs <= 0) {
      onChange(next);
      return;
    }
    setDraft(next);
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      timer.current = null;
      pushed.current = next;
      onChange(next);
    }, debounceMs);
  };

  const clear = () => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    pushed.current = "";
    setDraft("");
    onChange("");
  };

  return (
    <div className={cn("relative", className)}>
      <Search
        className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-faint"
        aria-hidden="true"
      />
      <input
        type="search"
        value={shown}
        autoFocus={autoFocus}
        onChange={(event) => handleChange(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        suppressHydrationWarning
        className={cn(
          "h-9 w-full rounded-md border border-border bg-surface pl-9 pr-8 text-body-md text-text-primary",
          "placeholder:text-text-faint",
          "transition-colors duration-micro ease-standard",
          "hover:border-border-strong",
          "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40",
        )}
      />
      {shown ? (
        <button
          type="button"
          onClick={clear}
          suppressHydrationWarning
          className="press absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded text-text-faint hover:bg-surface-hover hover:text-text-primary"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
}

/**
 * Filter chip. Selected state carries an accent ring as well as colour, so it
 * does not rely on colour alone.
 */
export function FilterChip({
  active,
  onClick,
  children,
  count,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  count?: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "press inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 font-technical-sm",
        active
          ? "border-accent-border bg-accent-soft text-accent"
          : "border-border bg-surface text-text-muted hover:border-border-strong hover:text-text-secondary",
      )}
    >
      {children}
      {count !== undefined ? (
        <span className={cn("tabular-nums", active ? "text-accent" : "text-text-faint")}>
          {count}
        </span>
      ) : null}
    </button>
  );
}
