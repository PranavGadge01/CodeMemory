"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp, RotateCcw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/primitives";
import { FilterChip, SearchInput } from "@/components/ui/search-input";
import { Surface } from "@/components/ui/surface";
import { TableHead, TableWrapper, Tbody, Td, Th, Tr } from "@/components/app/data-table";
import { StatusBadge } from "@/components/ui/badges";
import {
  formatBeats,
  formatDateTime,
  formatMemory,
  formatNumber,
  formatRelative,
  formatRuntime,
} from "@/lib/format";
import type { Problem, Submission, SubmissionStatus } from "@/lib/types";

type SortKey = "timestamp" | "runtime" | "memory";
type SortState = { key: SortKey; dir: "asc" | "desc" };

interface SubmissionRow {
  submission: Submission;
  problem: Problem;
}

/**
 * Canonical status order for the filter chips — accepted first, then the
 * failure modes roughly in the order a developer thinks about them. Only
 * statuses that actually occur are rendered.
 */
const STATUS_ORDER: SubmissionStatus[] = [
  "Accepted",
  "Wrong Answer",
  "Time Limit Exceeded",
  "Memory Limit Exceeded",
  "Runtime Error",
  "Compile Error",
  "Unknown",
];

/** Fastest-first for runtime and memory, newest-first for time. */
const DEFAULT_DIR: Record<SortKey, "asc" | "desc"> = {
  timestamp: "desc",
  runtime: "asc",
  memory: "asc",
};

export const QUERY_KEYS = {
  q: "q",
  status: "status",
  language: "language",
} as const;

export function SubmissionsBrowser({
  rows,
  problems,
  filteredTotal,
  params,
}: {
  /** Submission/problem pairs, already filtered and ordered by the backend. */
  rows: SubmissionRow[];
  /** Problems backing the rows — the source of the language and status chips. */
  problems: Problem[];
  filteredTotal: number;
  params: { q: string; status: string; language: string };
}) {
  const router = useRouter();

  const query = params.q;
  const status: SubmissionStatus | "All" = STATUS_ORDER.includes(
    params.status as SubmissionStatus,
  )
    ? (params.status as SubmissionStatus)
    : "All";
  // The mapped language may not be in the UI union when the backend sends a
  // language the frontend has never labelled, so the guard is over `string`.
  const language: string = params.language || "All";
  const [sort, setSort] = React.useState<SortState>({ key: "timestamp", dir: "desc" });

  // The chips are derived from the problems backing the page rather than from
  // the rows alone, so the counts stay stable while a filter is narrowing the
  // set the table shows.
  const allSubmissions = React.useMemo(
    () => problems.flatMap((problem) => problem.attempts.flatMap((attempt) => attempt.submissions)),
    [problems],
  );

  const availableStatuses = React.useMemo(
    () => STATUS_ORDER.filter((value) => rows.some((row) => row.submission.status === value)),
    [rows],
  );

  const availableLanguages = React.useMemo(() => {
    const set = new Set<string>();
    for (const row of rows) set.add(row.submission.language);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rows]);

  /**
   * Push one filter into the query string. The backend applies it — the
   * endpoint filters on `problem`, `status` and `language` — so the browser
   * never re-filters the rows it was handed.
   */
  const setParam = React.useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(window.location.search);
      if (value === "") next.delete(key);
      else next.set(key, value);
      const qs = next.toString();
      router.replace(qs ? `/submissions?${qs}` : "/submissions", { scroll: false });
    },
    [router],
  );

  const hasFilters = query.trim() !== "" || status !== "All" || language !== "All";

  const resetFilters = React.useCallback(() => {
    const next = new URLSearchParams(window.location.search);
    next.delete(QUERY_KEYS.q);
    next.delete(QUERY_KEYS.status);
    next.delete(QUERY_KEYS.language);
    const qs = next.toString();
    router.replace(qs ? `/submissions?${qs}` : "/submissions", { scroll: false });
  }, [router]);

  // The backend already filtered and ordered the rows; sorting has no backend
  // equivalent, so the header sort is applied to the page the server returned.
  const sorted = React.useMemo(() => {
    const direction = sort.dir === "asc" ? 1 : -1;

    const sortValue = (row: SubmissionRow): number => {
      if (sort.key === "timestamp") {
        return new Date(row.submission.submittedAt).getTime();
      }
      if (sort.key === "runtime") {
        return row.submission.runtimeMs ?? Number.POSITIVE_INFINITY;
      }
      return row.submission.memoryMb ?? Number.POSITIVE_INFINITY;
    };

    const byKey = (a: SubmissionRow, b: SubmissionRow): number => {
      const av = sortValue(a);
      const bv = sortValue(b);
      if (av === bv) return 0;
      return av > bv ? 1 : -1;
    };

    // Tie-break on time so equal runtimes keep a stable, sensible order.
    const byTime = (a: SubmissionRow, b: SubmissionRow) =>
      new Date(b.submission.submittedAt).getTime() - new Date(a.submission.submittedAt).getTime();

    return [...rows].sort((a, b) => byKey(a, b) * direction || byTime(a, b));
  }, [rows, sort]);

  const handleSort = React.useCallback((key: string) => {
    const sortKey = key as SortKey;
    setSort((prev) =>
      prev.key === sortKey
        ? { key: sortKey, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key: sortKey, dir: DEFAULT_DIR[sortKey] },
    );
  }, []);

  return (
    <Surface className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-border-soft p-4">
        <SearchInput
          value={query}
          onChange={(value) => setParam(QUERY_KEYS.q, value)}
          placeholder="Search problem title or slug…"
          className="sm:max-w-sm"
          aria-label="Search by problem title or slug"
        />

        <div className="flex flex-wrap items-center gap-1.5">
          <FilterChip
            active={status === "All"}
            onClick={() => setParam(QUERY_KEYS.status, "")}
            count={allSubmissions.length}
          >
            All statuses
          </FilterChip>
          {availableStatuses.map((value) => (
            <FilterChip
              key={value}
              active={status === value}
              onClick={() => setParam(QUERY_KEYS.status, value)}
              count={allSubmissions.filter((sub) => sub.status === value).length}
            >
              {value}
            </FilterChip>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <FilterChip
            active={language === "All"}
            onClick={() => setParam(QUERY_KEYS.language, "")}
            count={allSubmissions.length}
          >
            All languages
          </FilterChip>
          {availableLanguages.map((value) => (
            <FilterChip
              key={value}
              active={language === value}
              onClick={() => setParam(QUERY_KEYS.language, value)}
              count={allSubmissions.filter((sub) => sub.language === value).length}
            >
              {value}
            </FilterChip>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-border-soft px-4 py-2.5">
        <span className="font-technical-sm text-text-muted">
          {`Showing ${formatNumber(sorted.length)} of ${formatNumber(filteredTotal)} submissions`}
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

      {sorted.length === 0 ? (
        <EmptyState
          icon={<Search className="h-4 w-4" aria-hidden="true" />}
          title={hasFilters ? "No submissions match these filters" : "No submissions yet"}
          description={
            hasFilters
              ? "Try a different search term, or clear the status and language filters."
              : "Submissions appear here once a submission history has been imported."
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
        <TableWrapper className="[&>table]:min-w-[980px]">
          <TableHead>
            <Th>Submission</Th>
            <Th>Problem</Th>
            <Th>Status</Th>
            <Th>Language</Th>
            <Th align="right" sortKey="runtime" onSort={handleSort} sorted={sortedState(sort, "runtime")}>
              <SortHeading label="Runtime" active={sort.key === "runtime"} dir={sort.dir} />
            </Th>
            <Th align="right" sortKey="memory" onSort={handleSort} sorted={sortedState(sort, "memory")}>
              <SortHeading label="Memory" active={sort.key === "memory"} dir={sort.dir} />
            </Th>
            <Th align="right" sortKey="timestamp" onSort={handleSort} sorted={sortedState(sort, "timestamp")}>
              <SortHeading label="Timestamp" active={sort.key === "timestamp"} dir={sort.dir} />
            </Th>
          </TableHead>
          <Tbody>
            {sorted.map(({ submission, problem }) => (
              <Tr key={submission.id}>
                <Td mono className="max-w-[170px]">
                  {problem.slug ? (
                    <Link
                      href={`/submissions?id=${encodeURIComponent(submission.id)}`}
                      title={`Open submission ${submission.id}`}
                      className="press block truncate text-body-sm font-medium text-text-primary hover:text-accent"
                    >
                      <span className="block truncate" title={submission.id}>
                        ...{submission.id.slice(-12)}
                      </span>
                    </Link>
                  ) : (
                    <span className="block truncate text-body-sm text-text-muted" title={submission.id}>
                      ...{submission.id.slice(-12)}
                    </span>
                  )}
                </Td>
                <Td className="max-w-[260px]">
                  {problem.slug ? (
                    <Link
                      href={`/problems?slug=${problem.slug}`}
                      title={`Open ${problem.title}`}
                      className="press block truncate text-body-sm font-medium text-text-primary hover:text-accent"
                    >
                      {problem.title}
                    </Link>
                  ) : (
                    <span className="block truncate text-body-sm text-text-muted">
                      {problem.title}
                    </span>
                  )}
                </Td>
                <Td>
                  <StatusBadge status={submission.status} />
                </Td>
                <Td mono>{submission.language}</Td>
                <Td align="right" mono>
                  <div>{formatRuntime(submission.runtimeMs)}</div>
                  {submission.beatsPercent !== null ? (
                    <div className="text-text-faint">{formatBeats(submission.beatsPercent)}</div>
                  ) : null}
                </Td>
                <Td align="right" mono>
                  {formatMemory(submission.memoryMb)}
                </Td>
                <Td align="right" mono title={formatDateTime(submission.submittedAt)}>
                  {formatRelative(submission.submittedAt)}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableWrapper>
      )}
    </Surface>
  );
}

function sortedState(sort: SortState, key: SortKey): "asc" | "desc" | null {
  return sort.key === key ? sort.dir : null;
}

function SortHeading({
  label,
  active,
  dir,
}: {
  label: string;
  active: boolean;
  dir: "asc" | "desc";
}) {
  const Icon = dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <span className="inline-flex items-center gap-1">
      {label}
      {active ? (
        <Icon className="h-3 w-3 text-accent" aria-hidden="true" />
      ) : (
        <ArrowDown className="h-3 w-3 text-text-disabled" aria-hidden="true" />
      )}
    </span>
  );
}
