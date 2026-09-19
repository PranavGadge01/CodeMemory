"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Accessible switch. Focus ring and keyboard support come from the button
 * element itself; the state is carried by `aria-checked`, so the control does
 * not depend on colour alone.
 */
export function Toggle({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "press relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors duration-ui ease-standard",
        "disabled:cursor-not-allowed disabled:opacity-40",
        checked
          ? "border-accent-border bg-accent-soft"
          : "border-border bg-surface-card",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "inline-block h-3.5 w-3.5 rounded-full transition-transform duration-ui ease-standard",
          checked ? "translate-x-[18px] bg-accent" : "translate-x-[3px] bg-text-muted",
        )}
      />
    </button>
  );
}

export function SettingRow({
  label,
  description,
  children,
  htmlFor,
  className,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
  htmlFor?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-b border-border-soft px-5 py-4 last:border-0 sm:flex-row sm:items-center sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        <label htmlFor={htmlFor} className="text-body-sm font-medium text-text-primary">
          {label}
        </label>
        {description ? (
          <p className="mt-1 text-caption text-text-muted">{description}</p>
        ) : null}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export function SettingsGroup({
  id,
  eyebrow,
  title,
  description,
  children,
  className,
}: {
  id: string;
  eyebrow: string;
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      className={cn("scroll-mt-20", className)}
    >
      <div className="mb-3">
        <div className="eyebrow">{eyebrow}</div>
        <h2 id={`${id}-heading`} className="text-heading-md text-text-primary">
          {title}
        </h2>
        {description ? (
          <p className="mt-1.5 text-body-sm text-text-muted">{description}</p>
        ) : null}
      </div>
      <div className="rounded-lg border border-border bg-surface divide-y divide-border-soft">
        {children}
      </div>
    </section>
  );
}

export function SelectField({
  id,
  value,
  onChange,
  options,
  disabled,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ label: string; value: string }>;
  disabled?: boolean;
}) {
  return (
    <select
      id={id}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className={cn(
        "h-8 rounded-md border border-border bg-surface-card px-2.5 text-body-sm text-text-primary",
        "transition-colors duration-micro ease-standard",
        "hover:border-border-strong",
        "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/40",
        "disabled:cursor-not-allowed disabled:opacity-40",
      )}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
