import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getProblems } from "@/lib/data";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { StatStrip } from "@/components/app/stat-strip";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/system/reveal";
import { SubmissionsBrowser } from "@/components/app/submissions/submissions-browser";
import { submissionsOf } from "@/lib/mock/derive";
import { formatNumber, formatPercent } from "@/lib/format";

export const metadata = { title: "Submissions" };

export default function SubmissionsPage() {
  const problems = getProblems();
  const submissions = problems.flatMap((problem) => submissionsOf(problem));

  const total = submissions.length;
  const accepted = submissions.filter((submission) => submission.status === "Accepted").length;
  const failed = total - accepted;
  const acceptanceRate = total === 0 ? 0 : (accepted / total) * 100;
  const languagesUsed = new Set(submissions.map((submission) => submission.language)).size;

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

        <StatStrip
          stats={[
            {
              label: "Total submissions",
              value: total,
              hint: `${formatNumber(problems.length)} problems`,
            },
            { label: "Accepted", value: accepted },
            { label: "Failed", value: failed },
            { label: "Acceptance rate", value: formatPercent(acceptanceRate), accent: true },
            { label: "Languages used", value: languagesUsed },
          ]}
        />

        <Reveal>
          <SubmissionsBrowser problems={problems} />
        </Reveal>
      </PageSection>
    </PageContainer>
  );
}
