"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getProblem, getSubmission, listProblems, listSubmissions, ApiError } from "@/lib/api";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { StatStrip } from "@/components/app/stat-strip";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/system/reveal";
import { SubmissionsBrowser } from "@/components/app/submissions/submissions-browser";
import { SubmissionDetail } from "@/components/app/submissions/submission-detail";
import { ErrorState, PageSkeleton } from "@/components/app/data-states";
import { formatNumber, formatPercent } from "@/lib/format";
import type { Problem, Submission } from "@/lib/types";

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
        const problems = await listProblems({ page: 1, pageSize: 100 });
        const known = await Promise.all(problems.items.map((item) => getProblem(item.slug)));
        const problem = known.find((item) => item.id === submission.problemId) ?? null;
        return { mode: "detail" as const, submission, problem };
      }
      const [submissions, problems] = await Promise.all([
        listSubmissions({
          page: 1,
          pageSize: 100,
          // The endpoint's `problem` filter matches on slug or title, which is
          // what the search box is for; the language and status filters map
          // straight through.
          problem: params.q.trim() || undefined,
          status: params.status !== "All" ? params.status : undefined,
          language: params.language !== "All" ? params.language : undefined,
        }),
        // The rows link back to a problem, and the page's stats count problems,
        // so the problem index is needed alongside the submission page.
        listProblems({ page: 1, pageSize: 100 }).then((list) =>
          Promise.all(list.items.map((item) => getProblem(item.slug))),
        ),
      ]);

      // The table rows are paginated, but the API summary covers the complete
      // filtered dataset and stays stable as the requested page changes.
      const rows = pairSubmissions(submissions.items, problems);

      return {
        mode: "list" as const,
        rows,
        problems,
        summary: submissions.summary,
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
                problems={state.data.problems}
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

/** Join each submission to the problem it belongs to, for the row's link. */
function pairSubmissions(
  submissions: Submission[],
  problems: Problem[],
): { submission: Submission; problem: Problem }[] {
  const byId = new Map<string, Problem>();
  for (const problem of problems) byId.set(problem.id, problem);

  const rows: { submission: Submission; problem: Problem }[] = [];
  for (const submission of submissions) {
    // Fall back to a minimal placeholder so a submission whose problem is
    // outside the loaded page still renders its row, with the link dropped.
    const problem = byId.get(submission.problemId) ?? placeholderProblem(submission.problemId);
    rows.push({ submission, problem });
  }
  return rows;
}

function placeholderProblem(problemId: string): Problem {
  return {
    id: problemId,
    title: "Unknown problem",
    slug: "",
    difficulty: "Unknown",
    platform: "Custom",
    url: null,
    topics: [],
    statement: null,
    createdAt: new Date(0).toISOString(),
    updatedAt: new Date(0).toISOString(),
    attempts: [],
    notes: [],
  };
}

function SubmissionsSurface({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg border border-border bg-surface overflow-hidden">{children}</div>;
}
