import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { getSubmission, getProblem, listProblems, toAsyncState } from "@/lib/api";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/system/reveal";
import { ErrorState, PageSkeleton } from "@/components/app/data-states";
import { SubmissionDetail } from "@/components/app/submissions/submission-detail";

export const metadata = { title: "Submission detail" };

export default async function SubmissionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const state = await toAsyncState(
    (async () => {
      const submission = await getSubmission(id);

      const problems = await listProblems({ page: 1, pageSize: 1000 });
      const known = await Promise.all(
        problems.items.map((item) => getProblem(item.slug)),
      );
      const byId = new Map(known.map((p) => [p.id, p]));
      const problem = byId.get(submission.problemId) ?? null;

      return { submission, problem };
    })(),
  );

  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Submission"
          title="Submission detail"
          description="The submission record CodeMemory has stored."
          actions={
            <Button variant="outline" size="sm" asChild>
              <Link href="/submissions">
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
                All submissions
              </Link>
            </Button>
          }
        />

        {state.status === "success" ? (
          <Reveal>
            <SubmissionDetail
              submission={state.data.submission}
              problem={state.data.problem}
            />
          </Reveal>
        ) : state.status === "error" ? (
          <ErrorState error={state.error} />
        ) : (
          <PageSkeleton />
        )}
      </PageSection>
    </PageContainer>
  );
}
