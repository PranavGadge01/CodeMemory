import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { SiteNav } from "@/components/home/site-nav";
import { SiteFooter } from "@/components/site/site-footer";
import { Reveal } from "@/components/system/reveal";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Button } from "@/components/ui/button";

/** Page shell shared by the supporting public pages (/about, /privacy, ...). */
export function SitePageShell({
  eyebrow,
  title,
  intro,
  children,
}: {
  eyebrow: string;
  title: string;
  intro: string;
  children: React.ReactNode;
}) {
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
              {eyebrow}
            </span>
            <h1 className="text-display-lg mt-4 max-w-[24ch] text-text-primary">{title}</h1>
            <p className="mt-5 max-w-[62ch] text-body-lg text-text-muted">{intro}</p>
          </div>
        </section>
        <section className="border-b border-border-soft">
          <div className="mx-auto w-full max-w-[1200px] px-5 py-14 md:px-8 md:py-16">{children}</div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

/** A titled block of prose inside a supporting page. */
export function ProseSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Reveal>
      <Surface className="p-6">
        <SurfaceHeader title={title} />
        <div className="mt-3 flex flex-col gap-3 text-body-md text-text-muted">{children}</div>
      </Surface>
    </Reveal>
  );
}

/** The closing call to action reused on every supporting page. */
export function DownloadCallout({ label = "Download CodeMemory" }: { label?: string }) {
  return (
    <Button variant="accent" size="lg" asChild>
      <Link href="/download/">
        {label}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </Button>
  );
}
