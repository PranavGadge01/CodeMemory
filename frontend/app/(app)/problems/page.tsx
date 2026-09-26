"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getProblem, listProblems, ApiError } from "@/lib/api";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/system/reveal";
import { ProblemsBrowser } from "@/components/app/problems/problems-browser";
import { ErrorState, PageSkeleton } from "@/components/app/data-states";
import type { Problem } from "@/lib/types";

/**
 * Filter values the browser owns. They live in the URL rather than component
 * state so the backend does the filtering — the endpoint accepts `search`,
 * `difficulty` and `status` — and a filter set stays shareable and refresh-safe.
 */
export interface ProblemsSearch {
  q: string;
  difficulty: string;
  status: string;
  sort: string;
}

const DEFAULTS: ProblemsSearch = { q: "", difficulty: "All", status: "All", sort: "activity" };

export default function ProblemsPage() {
  return <React.Suspense fallback={<ProblemsSurface><PageSkeleton /></ProblemsSurface>}><ProblemsContent /></React.Suspense>;
}

function ProblemsContent() {
  const searchParams = useSearchParams();
  const raw = Object.fromEntries(searchParams.entries());
  const params: ProblemsSearch = {
    q: typeof raw.q === "string" ? raw.q : DEFAULTS.q,
    difficulty: typeof raw.difficulty === "string" ? raw.difficulty : DEFAULTS.difficulty,
    status: typeof raw.status === "string" ? raw.status : DEFAULTS.status,
    sort: typeof raw.sort === "string" ? raw.sort : DEFAULTS.sort,
  };
  const slug = raw.slug ?? null;

  // The list endpoint filters server-side; the backend has no sort parameter,
  // so sorting is applied client-side over the loaded page (see the browser).
  const [state, setState] = React.useState<
    | { status: "loading" }
    | { status: "success"; data: { filtered: Awaited<ReturnType<typeof listProblems>>; all: Awaited<ReturnType<typeof getProblem>>[]; drawerProblem: Awaited<ReturnType<typeof getProblem>> | null } }
    | { status: "error"; error: ApiError }
  >({ status: "loading" });

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      const [filtered, unfiltered] = await Promise.all([
        listProblems({
          page: 1,
          pageSize: 100,
          search: params.q.trim() || undefined,
          difficulty: params.difficulty !== "All" ? params.difficulty : undefined,
          status: params.status !== "All" ? params.status.toLowerCase() : undefined,
        }),
        // The unfiltered page underwrites the filter-chip counts, which need the
        // whole index rather than the currently filtered slice.
        listProblems({ page: 1, pageSize: 100 }),
      ]);

      // The list item carries no attempts, but the table renders attempts,
      // languages and best runtime — all derived from the full problem.
      // Details are fetched once, in parallel, for the unfiltered set; the
      // filtered set is a subset of it, so this is one detail fetch per
      // problem rather than one per filter state.
      const all = await Promise.all(unfiltered.items.map((item) => getProblem(item.slug)));

      const drawerProblem = slug ? await getProblem(slug) : null;
      return { filtered, all, drawerProblem };
    })().then((data) => { if (!cancelled) setState({ status: "success", data }); })
      .catch((error: unknown) => { if (!cancelled) setState({ status: "error", error: error instanceof ApiError ? error : new ApiError("Could not load problems.", "ERROR", 0) }); });
    return () => { cancelled = true; };
  }, [raw.q, raw.difficulty, raw.status, raw.sort, slug]);

  const drawerProblem = state.status === "success" ? state.data.drawerProblem : null;

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Problems"
          title="Problem history"
          description="Every problem you have touched, kept with the attempts, submissions and notes that led to the solution."
          actions={
            <Button variant="outline" size="sm" asChild>
              <Link href="/submissions">
                Submission log
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          }
        />

        <Reveal>
          {state.status === "success" ? (
            <ProblemsBrowser
              problems={state.data.all}
              visibleSlugs={new Set(state.data.filtered.items.map((item) => item.slug))}
              filteredTotal={state.data.filtered.total}
              params={params}
              initialSlug={drawerProblem ? slug : null}
              initialProblem={drawerProblem}
            />
          ) : state.status === "error" ? (
            <ProblemsSurface>
              <ErrorState error={state.error} />
            </ProblemsSurface>
          ) : (
            <ProblemsSurface>
              <PageSkeleton />
            </ProblemsSurface>
          )}
        </Reveal>
      </PageSection>
    </PageContainer>
  );
}

function ProblemsSurface({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg border border-border bg-surface overflow-hidden">{children}</div>;
}

export type { Problem };
