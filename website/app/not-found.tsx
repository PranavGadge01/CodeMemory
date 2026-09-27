import Link from "next/link";
import { SiteNav } from "@/components/home/site-nav";
import { SiteFooter } from "@/components/site/site-footer";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Page not found",
};

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen flex-col">
      <SiteNav />
      <main className="flex flex-1 items-start">
        <section className="relative w-full overflow-hidden border-b border-border-soft">
          <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" aria-hidden="true" />
          <div className="relative mx-auto w-full max-w-[1200px] px-5 py-20 md:px-8 md:py-28">
            <span className="eyebrow flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />
              404
            </span>
            <h1 className="text-display-lg mt-4 max-w-[24ch] text-text-primary">
              That page is not here.
            </h1>
            <p className="mt-5 max-w-[52ch] text-body-lg text-text-muted">
              The address you followed does not exist on this site. The product pages and the
              download page are one step away.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button variant="primary" size="lg" asChild>
                <Link href="/">Back to the homepage</Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href="/download/">Download</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
