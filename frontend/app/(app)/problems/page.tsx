import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getProblems } from "@/lib/data";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/system/reveal";
import { ProblemsBrowser } from "@/components/app/problems/problems-browser";

export const metadata = { title: "Problems" };

export default async function ProblemsPage({
  searchParams,
}: {
  searchParams: Promise<{ slug?: string | string[] }>;
}) {
  const problems = getProblems();
  const { slug } = await searchParams;
  const initialSlug = Array.isArray(slug) ? slug[0] ?? null : slug ?? null;

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
          <ProblemsBrowser problems={problems} initialSlug={initialSlug} />
        </Reveal>
      </PageSection>
    </PageContainer>
  );
}
