import { RevisionWorkspace } from "@/components/app/revision/revision-workspace";
import { PageContainer, PageSection } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";

export const metadata = { title: "Revision queue" };

export default function RevisionPage() {
  return (
    <PageContainer>
      <PageSection className="gap-6">
        <PageHeader
          eyebrow="Revision"
          title="Revision queue"
          description="The things your coding memory says you should revisit, ranked by how likely they are to have faded."
        />
        <RevisionWorkspace />
      </PageSection>
    </PageContainer>
  );
}
