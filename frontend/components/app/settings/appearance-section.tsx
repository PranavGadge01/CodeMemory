"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { SectionProps, SettingsState, Theme } from "./types";
import { SettingRow } from "./setting-row";
import { SettingsGroup } from "./settings-group";
import { Select } from "./select";
import { Segmented } from "./segmented";
import { Toggle } from "./toggle";

const THEME_OPTIONS = [
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
] satisfies { value: Theme; label: string }[];

const FONT_SIZE_OPTIONS = [
  { value: "12", label: "12 px" },
  { value: "13", label: "13 px" },
  { value: "14", label: "14 px" },
  { value: "16", label: "16 px" },
];

const DENSITY_OPTIONS = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
];

export interface AppearanceSectionProps extends SectionProps {
  /** Resolved `prefers-color-scheme`, so the System choice can be previewed. */
  systemDark: boolean;
  /** Whether the OS asked for reduced motion. */
  systemReducedMotion: boolean;
}

export function AppearanceSection({
  state,
  update,
  systemDark,
  systemReducedMotion,
}: AppearanceSectionProps) {
  const resolved: Theme = state.theme === "system" ? (systemDark ? "dark" : "light") : state.theme;

  return (
    <SettingsGroup
      id="settings-appearance"
      eyebrow="01"
      title="Appearance"
      description="How the workspace looks. Dark is the only finished theme in this phase."
    >
      <SettingRow
        htmlFor="setting-theme"
        label="Theme"
        description="System follows the colour scheme reported by your operating system."
        control={
          <>
            <Select
              id="setting-theme"
              value={state.theme}
              onValueChange={(value) => update("theme", value as Theme)}
              options={THEME_OPTIONS}
              aria-label="Theme"
            />
            <ThemeNote theme={state.theme} resolved={resolved} />
          </>
        }
      />

      <SettingRow
        label="Accent emphasis"
        description="Uses the CodeMemory orange for selected navigation, progress indicators and active states. Turn it off for a neutral workspace."
        control={
          <>
            <Toggle
              checked={state.accentEmphasis}
              onCheckedChange={(checked) => update("accentEmphasis", checked)}
              aria-label="Accent emphasis"
            />
            <span
              className={cn(
                "font-technical-sm",
                state.accentEmphasis ? "text-accent" : "text-text-faint",
              )}
            >
              {state.accentEmphasis ? "Orange accent" : "Neutral"}
            </span>
          </>
        }
      />

      <SettingRow
        label="Density"
        description="Compact tightens the padding of rows and lists throughout this page."
        control={
          <Segmented
            value={state.density}
            onValueChange={(value) => update("density", value as SettingsState["density"])}
            options={DENSITY_OPTIONS}
            aria-label="Density"
          />
        }
      />

      <SettingRow
        label="Reduced motion"
        description={
          systemReducedMotion
            ? "Your system has requested reduced motion. This switch overrides it."
            : "Overrides the interface motion regardless of your system setting."
        }
        control={
          <>
            <Toggle
              checked={state.reducedMotion}
              onCheckedChange={(checked) => update("reducedMotion", checked)}
              aria-label="Reduced motion"
            />
            {systemReducedMotion ? (
              <span className="font-technical-sm text-text-faint">System: reduced</span>
            ) : null}
          </>
        }
      />

      <SettingRow
        htmlFor="setting-code-font-size"
        label="Code font size"
        description="Applied to snippets, solution evolution and diff views."
        control={
          <>
            <Select
              id="setting-code-font-size"
              value={state.codeFontSize}
              onValueChange={(value) =>
                update("codeFontSize", value as SettingsState["codeFontSize"])
              }
              options={FONT_SIZE_OPTIONS}
              aria-label="Code font size"
            />
            <code
              className="font-technical text-text-muted"
              style={{ fontSize: `${state.codeFontSize}px` }}
            >
              two_sum: O(n)
            </code>
          </>
        }
      />
    </SettingsGroup>
  );
}

function ThemeNote({ theme, resolved }: { theme: Theme; resolved: Theme }) {
  if (theme === "light") {
    return (
      <span className="inline-flex items-center gap-1.5 font-technical-sm text-warning">
        <span className="h-1.5 w-1.5 rounded-full bg-warning" aria-hidden="true" />
        Coming soon
      </span>
    );
  }

  return (
    <span className="font-technical-sm text-text-faint">
      Active: <span className="text-text-secondary">{resolved}</span>
    </span>
  );
}
