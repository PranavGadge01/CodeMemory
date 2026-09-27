import { ProseSection, SitePageShell } from "@/components/site/page-shell";

export const metadata = {
  title: "Privacy",
  description:
    "What CodeMemory reads, where it is stored, and what leaves your computer when you sync.",
};

export default function PrivacyPage() {
  return (
    <SitePageShell
      eyebrow="Privacy"
      title="What CodeMemory reads, and where it stays."
      intro="CodeMemory is local-first. Your history, notes and review state are stored on your computer; the application talks to LeetCode when you ask it to sync."
    >
      <div className="flex flex-col gap-5">
        <ProseSection title="The desktop application">
          <p>
            Imported problems, attempts, submissions, notes, review state and preferences live in
            your own Windows user folder under{" "}
            <span className="font-technical-sm">%LOCALAPPDATA%\CodeMemory</span>. There is no
            CodeMemory server and no hosted account that receives them.
          </p>
          <p>
            Public sync reads the LeetCode profile you enter. Optional authenticated sync requires
            session credentials, which are encrypted through the operating system credential vault
            and are never returned to the user interface as values.
          </p>
          <p>
            Disconnecting revokes the stored credentials and keeps your history. If you have
            configured an AI provider, only then does the application contact that provider.
          </p>
        </ProseSection>

        <ProseSection title="This website">
          <p>
            These pages are a static build. There is no account system, no cookie, no analytics
            script, no advertising pixel and no third-party font or script request. The single
            value stored by this site is your theme preference, kept in your browser&rsquo;s local
            storage so the page does not flash the wrong colours on the next visit.
          </p>
        </ProseSection>

        <ProseSection title="What leaves your computer">
          <p>
            Requests to LeetCode when you connect or sync, and requests to your configured AI
            provider if you enable AI features. Nothing else is transmitted by the desktop
            application, and nothing at all is transmitted by this website.
          </p>
        </ProseSection>

        <ProseSection title="Removing your data">
          <p>
            Deleting the{" "}
            <span className="font-technical-sm">%LOCALAPPDATA%\CodeMemory</span> folder removes
            your local history. Uninstalling the application does not touch that folder, and
            installing a newer version does not replace it.
          </p>
        </ProseSection>
      </div>
    </SitePageShell>
  );
}
