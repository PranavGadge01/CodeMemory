"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, RotateCcw, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/primitives";
import { FilterChip, SearchInput } from "@/components/ui/search-input";
import { Surface } from "@/components/ui/surface";
import { TableHead, TableWrapper, Tbody, Td, Th, Tr } from "@/components/app/data-table";
import { DifficultyBadge } from "@/components/ui/badges";
import { ProblemDrawer } from "@/components/app/problems/problem-drawer";
import {
  attemptCount,
  bestRuntime,
  languagesOf,
  lastActivityAt,
  solveStatus,
} from "@/lib/mock/derive";
import { formatDateTime, formatNumber, formatRelative, formatRuntime } from "@/lib/format";
import type { Difficulty, Problem } from "@/lib/types";

type DifficultyFilter = "All" | Difficulty;
type StatusFilter = "All" | "Solved" | "Attempted";
type SortKey = "activity" | "difficulty" | "title" | "attempts";

const DIFFICULTIES: DifficultyFilter[] = ["All", "Easy", "Medium", "Hard"];
const STATUSES: StatusFilter[] = ["All", "Solved", "Attempted"];
const SORTS: { value: SortKey; label: string }[] = [
  { value: "activity", label: "Latest activity" },
  { value: "difficulty", label: "Difficulty" },
  { value: "title", label: "Title" },
  { value: "attempts", label: "Attempts" },
];
const DIFFICULTY_ORDER: Record<Difficulty, number> = {
  Easy: 0,
  Medium: 1,
  Hard: 2,
  Unknown: 3,
};

/**
 * Query-string keys the browser writes. Kept in one place so the page and the
 * browser can never disagree about a filter's URL name.
 */
export const QUERY_KEYS = {
  q: "q",
  difficulty: "difficulty",
  status: "status",
  sort: "sort",
} as const;

export function ProblemsBrowser({
  problems,
  /** Slugs the server-side filters kept. Sorting and the drawer stay client-side. */
  visibleSlugs,
  filteredTotal,
  params,
  initialSlug = null,
  initialProblem = null,
}: {
  problems: Problem[];
  visibleSlugs: Set<string>;
  filteredTotal: number;
  params: { q: string; difficulty: string; status: string; sort: string };
  initialSlug?: string | null;
  initialProblem?: Problem | null;
}) {
  const router = useRouter();

  const query = params.q;
  const difficulty = (DIFFICULTIES.includes(params.difficulty as DifficultyFilter)
    ? params.difficulty
    : "All") as DifficultyFilter;
  const status = (STATUSES.includes(params.status as StatusFilter) ? params.status : "All") as StatusFilter;
  const sort = SORTS.some((option) => option.value === params.sort)
    ? (params.sort as SortKey)
    : "activity";

  // The drawer's content outlives its visibility by one transition so the
  // slide-out has something to render against.
  const [drawerOpen, setDrawerOpen] = React.useState(Boolean(initialSlug));
  // A deep-linked problem may not be in the filtered set, so the drawer holds
  // the problem the page fetched for it rather than looking it up locally.
  const [drawerProblem, setDrawerProblem] = React.useState<Problem | null>(initialProblem);
  const closeTimer = React.useRef<number>(0);

  const openProblem = React.useCallback(
    (slug: string, problem: Problem | null) => {
      window.clearTimeout(closeTimer.current);
      setDrawerProblem(problem);
      setDrawerOpen(true);
    },
    [],
  );

  const closeDrawer = React.useCallback(() => {
    window.clearTimeout(closeTimer.current);
    setDrawerOpen(false);
    closeTimer.current = window.setTimeout(() => {
      setDrawerProblem(null);
    }, 260);
  }, []);

  React.useEffect(() => () => window.clearTimeout(closeTimer.current), []);

  /**
   * Push one filter into the query string. The backend applies the filter, so
   * the browser never filters the list itself; sorting has no backend
   * equivalent and is applied to the server-filtered set below.
   */
  const setParam = React.useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(window.location.search);
      if (value === "") next.delete(key);
      else next.set(key, value);
      const qs = next.toString();
      router.replace(qs ? `/problems?${qs}` : "/problems", { scroll: false });
    },
    [router],
  );

  const difficultyCounts = React.useMemo(() => {
    const counts: Record<DifficultyFilter, number> = {
      All: problems.length,
      Easy: 0,
      Medium: 0,
      Hard: 0,
      Unknown: 0,
    };
    for (const problem of problems) counts[problem.difficulty] += 1;
    return counts;
  }, [problems]);

  const statusCounts = React.useMemo(() => {
    let solved = 0;
    let attempted = 0;
    for (const problem of problems) {
      const current = solveStatus(problem);
      if (current === "Solved") solved += 1;
      else if (current === "Attempted") attempted += 1;
    }
    return { All: problems.length, Solved: solved, Attempted: attempted } as Record<
      StatusFilter,
      number
    >;
  }, [problems]);

  // The backend already filtered; this is only the client-side re-sort.
  const filtered = React.useMemo(() => {
    const matches = problems.filter((problem) => visibleSlugs.has(problem.slug));

    const byTitle = (a: Problem, b: Problem) => a.title.localeCompare(b.title);

    switch (sort) {
      case "difficulty":
        return [...matches].sort(
          (a, b) => DIFFICULTY_ORDER[a.difficulty] - DIFFICULTY_ORDER[b.difficulty] || byTitle(a, b),
        );
      case "title":
        return [...matches].sort(byTitle);
      case "attempts":
        return [...matches].sort((a, b) => attemptCount(b) - attemptCount(a) || byTitle(a, b));
      case "activity":
      default:
        return [...matches].sort(
          (a, b) => lastActivityAt(b).localeCompare(lastActivityAt(a)) || byTitle(a, b),
        );
    }
  }, [problems, visibleSlugs, sort]);

  const hasFilters = query.trim() !== "" || difficulty !== "All" || status !== "All";

  const resetFilters = React.useCallback(() => {
    const next = new URLSearchParams(window.location.search);
    next.delete(QUERY_KEYS.q);
    next.delete(QUERY_KEYS.difficulty);
    next.delete(QUERY_KEYS.status);
    const qs = next.toString();
    router.replace(qs ? `/problems?${qs}` : "/problems", { scroll: false });
  }, [router]);

  return (
    <Surface className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-border-soft p-4 lg:flex-row lg:items-center">
        <SearchInput
          value={query}
          onChange={(value) => setParam(QUERY_KEYS.q, value)}
          placeholder="Search title or topic…"
          className="lg:max-w-xs"
          aria-label="Search problems by title or topic"
        />

        <div className="flex flex-wrap items-center gap-1.5">
          {DIFFICULTIES.map((value) => (
            <FilterChip
              key={value}
              active={difficulty === value}
              onClick={() => setParam(QUERY_KEYS.difficulty, value === "All" ? "" : value)}
              count={difficultyCounts[value]}
            >
              {value}
            </FilterChip>
          ))}
        </div>

        <span aria-hidden="true" className="hidden h-5 w-px shrink-0 bg-border-soft lg:block" />

        <div className="flex flex-wrap items-center gap-1.5">
          {STATUSES.map((value) => (
            <FilterChip
              key={value}
              active={status === value}
              onClick={() => setParam(QUERY_KEYS.status, value === "All" ? "" : value)}
              count={statusCounts[value]}
            >
              {value}
            </FilterChip>
          ))}
        </div>

        <div className="lg:ml-auto">
          <SortSelect value={sort} onChange={(value) => setParam(QUERY_KEYS.sort, value)} />
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-border-soft px-4 py-2.5">
        <span className="font-technical-sm text-text-muted">
          {`Showing ${formatNumber(filtered.length)} of ${formatNumber(filteredTotal)} problems`}
        </span>
        {hasFilters ? (
          <button
            type="button"
            onClick={resetFilters}
            className="press inline-flex h-7 items-center gap-1.5 rounded-full px-2.5 font-technical-sm text-text-muted hover:bg-surface-hover hover:text-text-primary"
          >
            <RotateCcw className="h-3 w-3" aria-hidden="true" />
            Reset filters
          </button>
        ) : null}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Search className="h-4 w-4" aria-hidden="true" />}
          title={hasFilters ? "No problems match these filters" : "No problems yet"}
          description={
            hasFilters
              ? "Try a different search term, or clear the difficulty and status filters."
              : "Problems appear here once a submission history has been imported."
          }
          action={
            hasFilters ? (
              <Button variant="subtle" size="sm" onClick={resetFilters}>
                Clear all filters
              </Button>
            ) : null
          }
        />
      ) : (
        <TableWrapper className="[&>table]:min-w-[880px]">
          <TableHead>
            <Th>Problem</Th>
            <Th>Difficulty</Th>
            <Th>Topics</Th>
            <Th align="right">Attempts</Th>
            <Th>Languages</Th>
            <Th align="right">Best runtime</Th>
            <Th align="right">Last activity</Th>
          </TableHead>
          <Tbody>
            {filtered.map((problem) => (
              <Tr key={problem.id} onClick={() => openProblem(problem.slug, problem)}>
                <Td>
                  <div className="flex max-w-[300px] items-baseline">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        openProblem(problem.slug, problem);
                      }}
                      title={`Open details for ${problem.title}`}
                      className="press truncate text-left text-body-sm font-medium text-text-primary hover:text-accent"
                    >
                      {problem.title}
                    </button>
                  </div>
                  <div className="mt-0.5 truncate font-technical-sm text-text-faint">
                    {problem.slug}
                  </div>
                </Td>
                <Td>
                  <DifficultyBadge difficulty={problem.difficulty} />
                </Td>
                <Td className="max-w-[220px]">
                  <TruncatedList items={problem.topics} title={problem.topics.join(", ")} />
                </Td>
                <Td align="right" mono>
                  {attemptCount(problem)}
                </Td>
                <Td className="max-w-[180px]">
                  <TruncatedList
                    items={languagesOf(problem)}
                    title={languagesOf(problem).join(", ")}
                  />
                </Td>
                <Td align="right" mono>
                  {bestRuntime(problem) === null ? "—" : formatRuntime(bestRuntime(problem))}
                </Td>
                <Td align="right" mono title={formatDateTime(lastActivityAt(problem))}>
                  {formatRelative(lastActivityAt(problem))}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableWrapper>
      )}

      <ProblemDrawer
        problem={drawerProblem}
        open={drawerOpen && drawerProblem !== null}
        onClose={closeDrawer}
      />
    </Surface>
  );
}

/** Mono list that collapses to its first two entries plus a remainder count. */
function TruncatedList({ items, title }: { items: string[]; title?: string }) {
  const visible = items.slice(0, 2);
  const extra = items.length - visible.length;

  return (
    <span
      className="block truncate font-technical-sm text-text-muted"
      title={title ?? items.join(", ")}
    >
      {visible.length > 0 ? visible.join(" · ") : "—"}
      {extra > 0 ? <span className="text-text-faint">{` +${extra}`}</span> : null}
    </span>
  );
}

function SortSelect({
  value,
  onChange,
}: {
  value: SortKey;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative">
      <label htmlFor="problem-sort" className="sr-only">
        Sort problems
      </label>
      <select
        id="problem-sort"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          "h-9 w-full appearance-none rounded-md border border-border bg-surface pl-3 pr-9 text-body-sm text-text-primary",
          "transition-colors duration-micro ease-standard",
          "hover:border-border-strong focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40",
          "lg:w-[182px]",
        )}
      >
        {SORTS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-faint"
        aria-hidden="true"
      />
    </div>
  );
}
