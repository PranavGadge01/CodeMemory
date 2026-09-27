import { Download } from "lucide-react";
import { SiteNav } from "@/components/home/site-nav";
import { SiteFooter } from "@/components/site/site-footer";
import { Reveal } from "@/components/system/reveal";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Button } from "@/components/ui/button";
import { artifactName, artifactUrl, release } from "@/lib/release";

export const metadata = {
  title: "Download",
  description:
    "Download CodeMemory for Windows. Install once and keep a searchable memory of every LeetCode submission.",
};

const NOTES = [
  {
    title: "After installation",
    body: "Open CodeMemory, choose Get Started, and enter your LeetCode username. Public sync imports recent accepted submissions. Add credentials in Settings for full history and available code.",
  },
  {
    title: "Updating CodeMemory",
    body: "Close the app before running a newer installer. Your local history, notes, account settings, and encrypted credentials stay in your Windows user data folder.",
  },
  {
    title: "Other platforms",
    body: "Windows is the current desktop target. macOS and Linux installers are not available.",
  },
];

export default function DownloadPage() {
  return (
    <div className="relative flex min-h-screen flex-col">
      <SiteNav />

      <main className="flex-1">
        <section className="relative overflow-hidden border-b border-border-soft">
          <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" aria-hidden="true" />
          <div
            className="pointer-events-none absolute inset-x-0 top-0 h-px"
            style={{ background: "linear-gradient(90deg, transparent, rgba(255,161,22,0.35), transparent)" }}
            aria-hidden="true"
          />
          <div className="relative mx-auto w-full max-w-[1200px] px-5 py-14 md:px-8 md:py-20">
            <span className="eyebrow flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />
              Download
            </span>
            <h1 className="text-display-lg mt-4 max-w-[24ch] text-text-primary">
              A home for your coding history.
            </h1>
            <p className="mt-5 max-w-[58ch] text-body-lg text-text-muted">
              Install once. Keep learning from every attempt.
            </p>
          </div>
        </section>

        <section className="border-b border-border-soft">
          <div className="mx-auto w-full max-w-[1200px] px-5 py-14 md:px-8 md:py-16">
            {release.platforms.map((platform) => (
              <Reveal key={platform.id}>
                <Surface className="p-6 md:p-8">
                  <div className="flex flex-wrap items-start justify-between gap-6">
                    <div>
                      <h2 className="text-heading-xl text-text-primary">
                        CodeMemory for {platform.name}
                      </h2>
                      <p className="mt-2 text-body-md text-text-muted">{platform.requirements}</p>
                      <p className="mt-1 font-technical-sm text-text-faint">
                        Version {release.version}
                      </p>
                    </div>
                    <Download className="h-5 w-5 text-text-faint" aria-hidden="true" />
                  </div>

                  <div className="mt-7 flex flex-wrap items-center gap-3">
                    {platform.artifacts.map((artifact, index) =>
                      release.available ? (
                        <Button
                          key={artifact.file}
                          variant={index === 0 ? "primary" : "outline"}
                          size="lg"
                          asChild
                        >
                          <a href={artifactUrl(artifact.file)} download>
                            {artifact.label}
                          </a>
                        </Button>
                      ) : (
                        <Button
                          key={artifact.file}
                          variant={index === 0 ? "primary" : "outline"}
                          size="lg"
                          disabled
                        >
                          {artifact.label}
                        </Button>
                      ),
                    )}
                  </div>

                  {release.available ? (
                    <p className="mt-4 text-caption text-text-faint">
                      Choose the standard installer, or MSI for managed installation.
                    </p>
                  ) : (
                    <p role="status" className="mt-4 max-w-[70ch] text-caption text-text-muted">
                      The Windows release is being prepared. Version {release.version} is not
                      published yet, so these buttons stay disabled — downloads will appear here
                      once the verified installers are released. No download link is shown before
                      an artifact exists.
                    </p>
                  )}

                  {platform.artifacts.length ? (
                    <p className="mt-3 font-technical-sm text-text-faint">
                      {platform.artifacts.map((artifact) => artifactName(artifact.file)).join("  ·  ")}
                    </p>
                  ) : null}
                </Surface>
              </Reveal>
            ))}

            <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-3">
              {NOTES.map((note, index) => (
                <Reveal key={note.title} delay={index * 50}>
                  <Surface className="h-full p-5">
                    <SurfaceHeader title={note.title} />
                    <p className="mt-3 text-body-sm text-text-muted">{note.body}</p>
                  </Surface>
                </Reveal>
              ))}
            </div>

            <Reveal delay={60}>
              <Surface className="mt-5 p-5">
                <SurfaceHeader title="Release information" />
                <p className="mt-3 text-body-sm text-text-muted">
                  Published assets and release notes live in the{" "}
                  <a
                    className="text-accent-ink hover:underline"
                    href={`${release.repository}/releases`}
                  >
                    GitHub releases
                  </a>
                  . Internet access is needed for LeetCode sync and may be needed to install
                  Microsoft WebView2.
                </p>
              </Surface>
            </Reveal>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
