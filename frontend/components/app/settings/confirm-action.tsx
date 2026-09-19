"use client";

import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface ConfirmActionProps {
  triggerLabel: string;
  /** Variant of the trigger button. Defaults to `danger`. */
  triggerVariant?: "danger" | "outline" | "subtle";
  /** Heading. Omit for inline use, where the row already names the action. */
  title?: React.ReactNode;
  description?: React.ReactNode;
  confirmLabel?: string;
  /**
   * When set, the confirm button stays disabled until the user types this
   * exact string. Used for destructive, hard-to-reverse operations.
   */
  requireText?: string;
  onConfirm: () => void;
  className?: string;
}

/**
 * Two-step confirmation for irreversible-looking actions. Everything here is
 * UI state — no request is made and nothing outside this page changes.
 *
 * Without `title` it renders inline (the trigger button only, expanding to the
 * confirm panel below); with `title` it renders as a labelled block.
 */
export function ConfirmAction({
  triggerLabel,
  triggerVariant = "danger",
  title,
  description,
  confirmLabel = "Confirm",
  requireText,
  onConfirm,
  className,
}: ConfirmActionProps) {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");

  const confirmed = requireText
    ? text.trim().toLowerCase() === requireText.toLowerCase()
    : true;

  const handleConfirm = () => {
    onConfirm();
    setOpen(false);
    setText("");
  };

  if (!open) {
    return (
      <div
        className={cn(
          "flex items-center gap-4",
          title ? "justify-between" : "justify-end",
          className,
        )}
      >
        {title ? (
          <div className="min-w-0">
            <div className="text-body-sm font-medium text-text-primary">{title}</div>
            {description ? (
              <div className="mt-1 text-body-sm text-text-muted">{description}</div>
            ) : null}
          </div>
        ) : null}
        <Button variant={triggerVariant} size="sm" onClick={() => setOpen(true)}>
          {triggerLabel}
        </Button>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {title ? (
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-error" aria-hidden="true" />
          <div className="min-w-0">
            <div className="text-body-sm font-medium text-text-primary">{title}</div>
            {description ? (
              <div className="mt-1 text-body-sm text-text-muted">{description}</div>
            ) : null}
          </div>
        </div>
      ) : null}
      <div className="flex flex-col gap-3 rounded-md border border-error/25 bg-error-soft p-3">
        {!title && description ? (
          <p className="text-body-sm text-text-secondary">{description}</p>
        ) : null}
        {requireText ? (
          <label className="flex flex-col gap-1.5">
            <span className="font-technical-sm text-text-muted">
              Type <span className="text-error">{requireText}</span> to confirm
            </span>
            <Input
              value={text}
              onChange={(event) => setText(event.target.value)}
              autoFocus
              autoComplete="off"
              spellCheck={false}
              aria-label={`Type ${requireText} to confirm`}
              className="font-technical"
            />
          </label>
        ) : null}
        <div className="flex items-center gap-2">
          <Button variant="danger" size="sm" disabled={!confirmed} onClick={handleConfirm}>
            {confirmLabel}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setOpen(false);
              setText("");
            }}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
