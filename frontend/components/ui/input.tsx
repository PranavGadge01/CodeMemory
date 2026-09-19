import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          "h-9 w-full rounded-md border border-border bg-surface px-3 text-body-md text-text-primary",
          "placeholder:text-text-faint",
          "transition-colors duration-micro ease-standard",
          "hover:border-border-strong",
          "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40",
          "disabled:cursor-not-allowed disabled:opacity-40",
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "w-full rounded-md border border-border bg-surface px-3 py-2 text-body-md text-text-primary",
          "placeholder:text-text-faint",
          "transition-colors duration-micro ease-standard",
          "hover:border-border-strong",
          "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40",
          "disabled:cursor-not-allowed disabled:opacity-40",
          className,
        )}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";
