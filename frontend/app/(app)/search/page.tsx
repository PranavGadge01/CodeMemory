"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Search, X, FileText, Code, BookOpen } from "lucide-react";
import { search } from "@/lib/api";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { DifficultyBadge, StatusBadge } from "@/components/ui/badges";
import { SearchInput } from "@/components/ui/search-input";
import { PageSkeleton } from "@/components/app/data-states";
import type { Difficulty, SubmissionStatus, SearchResult } from "@/lib/types";

const MAX_QUERY_LENGTH = 200;

export default function SearchPage() {
  return <React.Suspense fallback={<PageContainer><PageSection><PageSkeleton /></PageSection></PageContainer>}><SearchContent /></React.Suspense>;
}

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const [query, setQuery] = React.useState(initialQuery);
  const [results, setResults] = React.useState<SearchResult[]>([]);
  const [loading, setLoading] = React.useState(initialQuery.length > 0);
  const [error, setError] = React.useState<string | null>(null);

  const trimmed = query.trim();

  React.useEffect(() => {
    if (!trimmed) {
      return;
    }

    let cancelled = false;

    const timer = setTimeout(() => {
      setLoading(true);
      setError(null);

      search(trimmed, 50)
        .then((data) => {
          if (!cancelled) {
            setResults(data);
            setLoading(false);
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setError(err.message);
            setLoading(false);
          }
        });
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [trimmed]);

  const hasQuery = trimmed.length > 0;
  const showNoResults = hasQuery && !loading && !error && results.length === 0;

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Search"
          title="Global search"
          description="Search across your problems, submissions, and knowledge."
        />

        <div className="max-w-2xl">
          <SearchInput
            value={query}
            onChange={(val) => setQuery(val.slice(0, MAX_QUERY_LENGTH))}
            placeholder="Search problems, submissions… (⌘K)"
            autoFocus
          />
        </div>

        {!hasQuery ? (
          <SearchEmptyState />
        ) : error ? (
          <ErrorState message={error} />
        ) : loading ? (
          <SearchResultsSkeleton />
        ) : showNoResults ? (
          <EmptyState query={query} />
        ) : (
          <SearchResults results={results} query={query} />
        )}
      </PageSection>
    </PageContainer>
  );
}

function SearchResults({ results, query }: { results: SearchResult[]; query: string }) {
  const problems = results.filter((r) => r.type === "problem");
  const submissions = results.filter((r) => r.type === "submission");
  const knowledge = results.filter((r) => r.type === "knowledge");

  return (
    <div className="flex flex-col gap-6">
      {problems.length > 0 ? (
        <ResultSection label="Problems" icon={<FileText className="h-4 w-4" />} count={problems.length}>
          {problems.map((r) => (
            <ProblemRow key={`problem-${r.id}`} result={r} query={query} />
          ))}
        </ResultSection>
      ) : null}

      {submissions.length > 0 ? (
        <ResultSection label="Submissions" icon={<Code className="h-4 w-4" />} count={submissions.length}>
          {submissions.map((r) => (
            <SubmissionRow key={`submission-${r.id}`} result={r} query={query} />
          ))}
        </ResultSection>
      ) : null}

      {knowledge.length > 0 ? (
        <ResultSection label="Knowledge" icon={<BookOpen className="h-4 w-4" />} count={knowledge.length}>
          {knowledge.map((r) => (
            <KnowledgeRow key={`knowledge-${r.id}`} result={r} query={query} />
          ))}
        </ResultSection>
      ) : null}
    </div>
  );
}

function ResultSection({
  label,
  icon,
  count,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col">
      <div className="mb-2 flex items-center gap-2 text-caption text-text-muted">
        {icon}
        <span>{label}</span>
        <span className="text-text-faint">({count})</span>
      </div>
      <div className="rounded-lg border border-border bg-surface">
        {children}
      </div>
    </div>
  );
}

function ProblemRow({ result, query }: { result: SearchResult; query: string }) {
  const meta = result.metadata as { difficulty: string; topics: string[] };
  return (
    <Link
      href={`/problems?slug=${encodeURIComponent(result.slug)}`}
      className="press flex items-center justify-between gap-4 border-b border-border-soft px-4 py-3 last:border-0 hover:bg-surface-hover"
    >
      <div className="min-w-0 flex-1">
        <div className="text-body-sm font-medium text-text-primary">{highlight(result.title, query)}</div>
        {meta.topics.length > 0 ? (
          <div className="mt-0.5 font-technical-sm text-text-faint">
            {meta.topics.join(" · ")}
          </div>
        ) : null}
      </div>
      <DifficultyBadge difficulty={meta.difficulty as Difficulty} className="shrink-0" />
    </Link>
  );
}

function SubmissionRow({ result, query }: { result: SearchResult; query: string }) {
  const meta = result.metadata as {
    language: string;
    status: string;
    runtimeMs: number | null;
    memoryMb: number | null;
  };
  return (
    <Link
      href={`/submissions?id=${encodeURIComponent(result.id)}`}
      className="press flex items-center justify-between gap-4 border-b border-border-soft px-4 py-3 last:border-0 hover:bg-surface-hover"
    >
      <div className="min-w-0 flex-1">
        <div className="text-body-sm font-medium text-text-primary">{highlight(result.title, query)}</div>
        <div className="mt-0.5 flex items-center gap-2 font-technical-sm text-text-faint">
          <span>{meta.language}</span>
          <span aria-hidden="true">·</span>
          <StatusBadge status={meta.status as SubmissionStatus} />
          {meta.runtimeMs !== null ? <span>{meta.runtimeMs} ms</span> : null}
          {meta.memoryMb !== null ? <span>{meta.memoryMb} MB</span> : null}
        </div>
      </div>
    </Link>
  );
}

function KnowledgeRow({ result, query }: { result: SearchResult; query: string }) {
  const description = result.metadata?.description as string | undefined;
  return (
    <Link
      href={`/problems?slug=${encodeURIComponent(result.slug)}`}
      className="press flex items-center gap-4 border-b border-border-soft px-4 py-3 last:border-0 hover:bg-surface-hover"
    >
      <div className="min-w-0 flex-1">
        <div className="text-body-sm font-medium text-text-primary">{highlight(result.title, query)}</div>
        {description ? (
          <div className="mt-0.5 truncate font-technical-sm text-text-faint">
            {description.slice(0, 120)}
          </div>
        ) : null}
      </div>
    </Link>
  );
}

function highlight(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="rounded bg-accent/20 text-accent">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

function SearchEmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <Search className="h-8 w-8 text-text-faint" aria-hidden="true" />
      <p className="max-w-sm text-body-sm text-text-muted">
        Start typing to search across your problems, submissions, and knowledge.
      </p>
    </div>
  );
}

function EmptyState({ query }: { query: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <X className="h-8 w-8 text-text-faint" aria-hidden="true" />
      <p className="text-body-sm text-text-muted">
        No results found for &ldquo;{query}&rdquo;.
      </p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <Search className="h-8 w-8 text-error" aria-hidden="true" />
      <p className="text-body-sm text-error">{message}</p>
    </div>
  );
}

function SearchResultsSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-14 rounded-lg border border-border bg-surface">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex-1 space-y-1.5">
              <div className="h-4 w-3/4 rounded bg-surface-card" />
              <div className="h-3 w-1/2 rounded bg-surface-card" />
            </div>
            <div className="h-5 w-12 rounded bg-surface-card" />
          </div>
        </div>
      ))}
    </div>
  );
}
