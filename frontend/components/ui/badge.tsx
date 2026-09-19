import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Small technical label. CodeMemory uses mono for these because they are
 * state signals, not prose — the shape of the word should be as stable as
 * its colour.
 */
const badgeVariants = cva(
  [
    "inline-flex",
    "items-center",
    "gap-1.5",
    "rounded-sm",
    "border",
    "font-technical-sm",
    "font-medium",
    "whitespace-nowrap",
  ],
  {
    variants: {
      variant: {
        neutral: "border-border bg-surface-card text-text-secondary",
        accent: "border-accent-border bg-accent-soft text-accent",
        success: "border-success/25 bg-success-soft text-success",
        warning: "border-warning/25 bg-warning-soft text-warning",
        error: "border-error/25 bg-error-soft text-error",
        info: "border-info/25 bg-info-soft text-info",
        outline: "border-border bg-transparent text-text-muted",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { badgeVariants };
