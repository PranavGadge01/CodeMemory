import { cn } from "@/lib/utils";

/**
 * Table primitives for developer-style dense lists.
 *
 * The whole point of these tables is that they read as a query result: mono
 * for technical fields, hairline separators, right-aligned numbers, and a
 * sticky header so the column context never scrolls away.
 */
export function TableWrapper({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full border-collapse text-body-sm">{children}</table>
    </div>
  );
}

export function TableHead({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <thead className={cn("sticky top-0 z-10 bg-surface", className)}>
      <tr className="border-b border-border">{children}</tr>
    </thead>
  );
}

export function Th({
  children,
  className,
  align = "left",
  sortKey,
  onSort,
  sorted,
}: {
  children?: React.ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
  sortKey?: string;
  onSort?: (key: string) => void;
  sorted?: "asc" | "desc" | null;
}) {
  const isSortable = Boolean(sortKey && onSort);
  return (
    <th
      scope="col"
      className={cn(
        "whitespace-nowrap px-4 py-2.5 font-technical-sm font-medium text-text-muted",
        align === "right" && "text-right",
        align === "center" && "text-center",
        isSortable && "cursor-pointer select-none hover:text-text-primary",
        className,
      )}
      aria-sort={sorted ? (sorted === "asc" ? "ascending" : "descending") : "none"}
      onClick={isSortable ? () => onSort?.(sortKey as string) : undefined}
    >
      {children}
    </th>
  );
}

export function Tbody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <tbody className={cn(className)}>{children}</tbody>;
}

export function Tr({
  children,
  className,
  href,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  href?: string;
  onClick?: () => void;
}) {
  return (
    <tr
      className={cn(
        "border-b border-border-soft transition-colors duration-micro",
        href || onClick ? "cursor-pointer hover:bg-surface-hover" : "",
        className,
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

export function Td({
  children,
  className,
  align = "left",
  mono = false,
  title,
}: {
  children?: React.ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
  mono?: boolean;
  title?: string;
}) {
  return (
    <td
      className={cn(
        "whitespace-nowrap px-4 py-3 align-middle",
        align === "right" && "text-right",
        align === "center" && "text-center",
        mono && "font-technical tabular-nums text-text-muted",
        className,
      )}
      title={title}
    >
      {children}
    </td>
  );
}

/** Mono cell that keeps its value readable: ids, timestamps, runtime. */
export function TechnicalCell({ children, className }: { children: React.ReactNode; className?: string }) {
  return <Td mono className={className}>{children}</Td>;
}
