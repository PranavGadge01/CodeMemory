import { cn } from "@/lib/utils";

/**
 * Shared content frame so every product page has identical rhythm.
 * Max-width is 1440px per DESIGN.md §9.
 */
export function PageContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-[1440px] px-4 py-6 md:px-8 md:py-8", className)}>
      {children}
    </div>
  );
}

export function PageSection({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("flex flex-col gap-4", className)}>{children}</div>;
}
