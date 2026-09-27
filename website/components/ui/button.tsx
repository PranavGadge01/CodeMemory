import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "@/components/ui/slot";
import { cn } from "@/lib/utils";

/**
 * CodeMemory button.
 *
 * White is the default primary — orange is an identity accent, not the colour
 * of every action, so `accent` is reserved for the handful of moments where
 * the brand should carry the action. The primary fill and its foreground come
 * from tokens so the inverted CTA stays legible in either theme. All variants
 * share the same tactile 1 → 0.97 → 1 press from the motion system.
 */
const buttonVariants = cva(
  [
    "press",
    "inline-flex",
    "items-center",
    "justify-center",
    "gap-2",
    "whitespace-nowrap",
    "rounded-md",
    "font-medium",
    "select-none",
    "disabled:pointer-events-none",
    "disabled:opacity-40",
  ],
  {
    variants: {
      variant: {
        primary:
          "bg-btn-primary text-btn-primary-fg hover:bg-btn-primary-hover active:bg-btn-primary-pressed",
        accent:
          "bg-accent text-black hover:bg-accent-hover active:bg-accent-pressed",
        outline:
          "border border-border bg-transparent text-text-primary hover:bg-surface-hover hover:border-border-strong",
        subtle: "bg-surface-card text-text-primary border border-border hover:bg-surface-hover",
        ghost: "text-text-secondary hover:text-text-primary hover:bg-surface-hover",
        danger:
          "border border-error/30 text-error hover:bg-error-soft hover:border-error/50",
      },
      size: {
        sm: "h-8 px-3 text-body-sm",
        md: "h-9 px-4 text-body-sm",
        lg: "h-10 px-5 text-body-md",
        icon: "h-8 w-8",
        "icon-sm": "h-7 w-7",
      },
    },
    defaultVariants: {
      variant: "outline",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = ({ className, variant, size, asChild, ...props }: ButtonProps) => {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      suppressHydrationWarning
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
};

export { buttonVariants };
