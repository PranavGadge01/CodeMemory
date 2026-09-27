import Link from "next/link";

const FOOTER_LINKS = [
  { label: "Download", href: "/download/" },
  { label: "About", href: "/about/" },
  { label: "Changelog", href: "/changelog/" },
  { label: "Privacy", href: "/privacy/" },
  { label: "Terms", href: "/terms/" },
  { label: "Contact", href: "/contact/" },
];

/**
 * Site footer — the marketing site's public navigation.
 *
 * The desktop build links to the workspace routes (Dashboard, Analytics,
 * Knowledge, Settings); those routes do not exist on the public site, so the
 * same footer surface carries the public pages instead.
 */
export function SiteFooter() {
  return (
    <footer className="border-t border-border-soft">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col items-start justify-between gap-4 px-5 py-8 sm:flex-row sm:items-center md:px-8">
        <span className="font-technical-sm text-text-faint">
          CodeMemory · local-first coding memory
        </span>
        <nav aria-label="Footer" className="flex flex-wrap items-center gap-5">
          {FOOTER_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="font-technical-sm text-text-faint hover:text-text-muted"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
