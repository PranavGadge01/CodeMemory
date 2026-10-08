"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getProblem, getSubmission, listSubmissions, ApiError } from "@/lib/api";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { StatStrip } from "@/components/app/stat-strip";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/system/reveal";
import { SubmissionsBrowser, type SubmissionRow } from "@/components/app/submissions/submissions-browser";
import { SubmissionDetail } from "@/components/app/submissions/submission-detail";
import { ErrorState, PageSkeleton } from "@/components/app/data-states";
import { formatNumber, formatPercent } from "@/lib/format";

/**
 * Filter values the browser owns, mirrored in the URL so the backend applies
 * them. The endpoint accepts `language`, `status` and `problem` (a title/slug
 * fragment), which covers the search box the browser previously owned.
 */
export interface SubmissionsSearch {
  q: string;
  status: string;
  language: string;
}

const DEFAULTS: SubmissionsSearch = { q: "", status: "All", language: "All" };

export default function SubmissionsPage() {
  return <React.Suspense fallback={<SubmissionsSurface><PageSkeleton /></SubmissionsSurface>}><SubmissionsContent /></React.Suspense>;
}

function SubmissionsContent() {
  const searchParams = useSearchParams();
  const raw = Object.fromEntries(searchParams.entries());
  const params: SubmissionsSearch = {
    q: typeof raw.q === "string" ? raw.q : DEFAULTS.q,
    status: typeof raw.status === "string" ? raw.status : DEFAULTS.status,
    language: typeof raw.language === "string" ? raw.language : DEFAULTS.language,
  };

  const [state, setState] = React.useState<any>({ status: "loading" });

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      const id = raw.id;
      if (id) {
        const submission = await getSubmission(id);
        // The submission already carries its problem id, so the detail view
        // resolves that single problem directly instead of loading the index.
        const problem = await getProblem(submission.problemId).catch(() => null);
        return { mode: "detail" as const, submission, problem };
      }
      const submissions = await listSubmissions({
        page: 1,
        pageSize: 100,
        // The endpoint's `problem` filter matches on slug or title, which is
        // what the search box is for; the language and status filters map
        // straight through.
        problem: params.q.trim() || undefined,
        status: params.status !== "All" ? params.status : undefined,
        language: params.language !== "All" ? params.language : undefined,
      });

      // Each row now carries its problem title and slug from the list endpoint,
      // so no per-problem detail request is needed to render the table.
      const rows: SubmissionRow[] = submissions.items.map((submission) => ({
        submission,
        problemTitle: submission.problemTitle ?? "Unknown problem",
        problemSlug: submission.problemSlug,
      }));

      return {
        mode: "list" as const,
        rows,
        summary: submissions.summary,
        filterOptions: submissions.filterOptions,
        filteredTotal: submissions.total,
      };
    })().then((data) => { if (!cancelled) setState({ status: "success", data }); })
      .catch((error: unknown) => { if (!cancelled) setState({ status: "error", error: error instanceof ApiError ? error : new ApiError("Could not load submissions.", "ERROR", 0) }); });
    return () => { cancelled = true; };
  }, [raw.id, raw.q, raw.status, raw.language]);

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Submissions"
          title="Submission history"
          description="Every submission in the order it landed — accepted runs, wrong answers, and the timeouts in between."
          actions={
            <Button variant="outline" size="sm" asChild>
              <Link href="/problems">
                Problem history
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          }
        />

        {state.status === "success" && state.data.mode === "detail" ? (
          <>
            <PageHeader
              eyebrow="Submission"
              title="Submission detail"
              description="The submission record CodeMemory has stored."
              actions={<Button variant="outline" size="sm" asChild><Link href="/submissions">All submissions</Link></Button>}
            />
            <Reveal><SubmissionDetail submission={state.data.submission} problem={state.data.problem} /></Reveal>
          </>
        ) : state.status === "success" ? (
          <>
            <StatStrip
              stats={[
                {
                  label: "Total submissions",
                  value: state.data.summary.total,
                  hint: `${formatNumber(state.data.summary.problemCount)} problems`,
                },
                { label: "Accepted", value: state.data.summary.accepted },
                { label: "Failed", value: state.data.summary.failed },
                {
                  label: "Acceptance rate",
                  value: formatPercent(state.data.summary.acceptanceRate),
                  accent: true,
                },
                { label: "Languages used", value: state.data.summary.languageCount },
              ]}
            />

            <Reveal>
                <SubmissionsBrowser
                rows={state.data.rows}
                filterOptions={state.data.filterOptions}
                filteredTotal={state.data.filteredTotal}
                params={params}
              />
            </Reveal>
          </>
        ) : state.status === "error" ? (
          <SubmissionsSurface>
            <ErrorState error={state.error} />
          </SubmissionsSurface>
        ) : (
          <>
            <StatStrip
              stats={[
                { label: "Total submissions", value: "—" },
                { label: "Accepted", value: "—" },
                { label: "Failed", value: "—" },
                { label: "Acceptance rate", value: "—" },
                { label: "Languages used", value: "—" },
              ]}
            />
            <SubmissionsSurface>
              <PageSkeleton />
            </SubmissionsSurface>
          </>
        )}
      </PageSection>
    </PageContainer>
  );
}

function SubmissionsSurface({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg border border-border bg-surface overflow-hidden">{children}</div>;
}
