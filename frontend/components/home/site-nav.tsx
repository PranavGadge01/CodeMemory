"use client";

import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Wordmark } from "@/components/system/logo";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/system/theme-toggle";

const NAV_LINKS = [
  { label: "Product", href: "/#product" },
  { label: "How it works", href: "/#evolution" },
  { label: "Insights", href: "/#analytics" },
];

export function SiteNav() {
  const [scrolled, setScrolled] = React.useState(false);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 transition-colors duration-ui ease-standard",
        scrolled ? "border-b border-border bg-canvas/85 backdrop-blur-md" : "border-b border-transparent",
      )}
    >
      <div className="mx-auto flex h-14 w-full max-w-[1200px] items-center justify-between px-5 md:px-8">
        <div className="flex items-center gap-7">
          <Link href="/" className="press" aria-label="CodeMemory home">
            <Wordmark />
          </Link>
          <nav aria-label="Site" className="hidden items-center gap-5 sm:flex">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="press text-body-sm text-text-muted hover:text-text-secondary"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="primary" size="sm" asChild>
            <Link href="/connect">Connect LeetCode</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
