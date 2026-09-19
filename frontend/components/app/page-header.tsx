import { cn } from "@/lib/utils";

/**
 * Page header — the consistent opening of every product page.
 *
 * Deliberately light: an eyebrow, a tight heading, one line of description,
 * and an action slot. No card, no border, no shadow.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        {eyebrow ? <div className="eyebrow mb-2">{eyebrow}</div> : null}
        <h1 className="text-heading-xl text-text-primary">{title}</h1>
        {description ? (
          <p className="mt-2 max-w-[68ch] text-body-md text-text-muted">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}
