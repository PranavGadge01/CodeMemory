"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowDown, ArrowUp, RotateCcw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/primitives";
import { FilterChip, SearchInput } from "@/components/ui/search-input";
import { Surface } from "@/components/ui/surface";
import { TableHead, TableWrapper, Tbody, Td, Th, Tr } from "@/components/app/data-table";
import { StatusBadge } from "@/components/ui/badges";
import { submissionsOf } from "@/lib/mock/derive";
import {
  formatBeats,
  formatDateTime,
  formatMemory,
  formatNumber,
  formatRelative,
  formatRuntime,
} from "@/lib/format";
import type { Language, Problem, Submission, SubmissionStatus } from "@/lib/types";

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

export function SubmissionsBrowser({ problems }: { problems: Problem[] }) {
  const [query, setQuery] = React.useState("");
  const [status, setStatus] = React.useState<SubmissionStatus | "All">("All");
  const [language, setLanguage] = React.useState<Language | "All">("All");
  const [sort, setSort] = React.useState<SortState>({ key: "timestamp", dir: "desc" });

  const rows = React.useMemo(() => {
    const flattened: SubmissionRow[] = [];
    for (const problem of problems) {
      for (const submission of submissionsOf(problem)) {
        flattened.push({ submission, problem });
      }
    }
    return flattened;
  }, [problems]);

  const availableStatuses = React.useMemo(
    () => STATUS_ORDER.filter((value) => rows.some((row) => row.submission.status === value)),
    [rows],
  );

  const availableLanguages = React.useMemo(() => {
    const set = new Set<Language>();
    for (const row of rows) set.add(row.submission.language);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [rows]);

  const filtered = React.useMemo(() => {
    const needle = query.trim().toLowerCase();

    return rows.filter(({ submission, problem }) => {
      if (status !== "All" && submission.status !== status) return false;
      if (language !== "All" && submission.language !== language) return false;
      if (needle) {
        const haystack = `${submission.id} ${problem.title} ${problem.slug}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    });
  }, [rows, query, status, language]);

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

    return [...filtered].sort((a, b) => byKey(a, b) * direction || byTime(a, b));
  }, [filtered, sort]);

  const handleSort = React.useCallback((key: string) => {
    const sortKey = key as SortKey;
    setSort((prev) =>
      prev.key === sortKey
        ? { key: sortKey, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key: sortKey, dir: DEFAULT_DIR[sortKey] },
    );
  }, []);

  const hasFilters = query.trim() !== "" || status !== "All" || language !== "All";

  const resetFilters = React.useCallback(() => {
    setQuery("");
    setStatus("All");
    setLanguage("All");
  }, []);

  return (
    <Surface className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-border-soft p-4">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search submission id or problem…"
          className="sm:max-w-sm"
          aria-label="Search by submission id or problem title"
        />

        <div className="flex flex-wrap items-center gap-1.5">
          <FilterChip active={status === "All"} onClick={() => setStatus("All")} count={rows.length}>
            All statuses
          </FilterChip>
          {availableStatuses.map((value) => (
            <FilterChip
              key={value}
              active={status === value}
              onClick={() => setStatus(value)}
              count={rows.filter((row) => row.submission.status === value).length}
            >
              {value}
            </FilterChip>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <FilterChip
            active={language === "All"}
            onClick={() => setLanguage("All")}
            count={rows.length}
          >
            All languages
          </FilterChip>
          {availableLanguages.map((value) => (
            <FilterChip
              key={value}
              active={language === value}
              onClick={() => setLanguage(value)}
              count={rows.filter((row) => row.submission.language === value).length}
            >
              {value}
            </FilterChip>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-border-soft px-4 py-2.5">
        <span className="font-technical-sm text-text-muted">
          {`Showing ${formatNumber(sorted.length)} of ${formatNumber(rows.length)} submissions`}
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
          title="No submissions match these filters"
          description="Try a different search term, or clear the status and language filters."
          action={
            <Button variant="subtle" size="sm" onClick={resetFilters}>
              Clear all filters
            </Button>
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
                  <span className="block truncate" title={submission.id}>
                    {submission.id}
                  </span>
                </Td>
                <Td className="max-w-[260px]">
                  <Link
                    href={`/problems?slug=${problem.slug}`}
                    title={`Open ${problem.title}`}
                    className="press block truncate text-body-sm font-medium text-text-primary hover:text-accent"
                  >
                    {problem.title}
                  </Link>
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
