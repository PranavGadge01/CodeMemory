"use client";

import * as React from "react";
import type { SectionProps, SettingsState } from "./types";
import { SettingRow } from "./setting-row";
import { SettingsGroup } from "./settings-group";
import { Select } from "./select";
import { Toggle } from "./toggle";

const LANGUAGE_OPTIONS = [
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "java", label: "Java" },
  { value: "cpp", label: "C++" },
  { value: "go", label: "Go" },
  { value: "rust", label: "Rust" },
];

const DIFFICULTY_OPTIONS = [
  { value: "all", label: "All difficulties" },
  { value: "Easy", label: "Easy" },
  { value: "Medium", label: "Medium" },
  { value: "Hard", label: "Hard" },
];

const TIMEZONE_OPTIONS = [
  { value: "local", label: "Local system" },
  { value: "UTC", label: "UTC" },
  { value: "America/New_York", label: "America / New York" },
  { value: "America/Los_Angeles", label: "America / Los Angeles" },
  { value: "Europe/London", label: "Europe / London" },
  { value: "Europe/Berlin", label: "Europe / Berlin" },
  { value: "Asia/Kolkata", label: "Asia / Kolkata" },
  { value: "Asia/Tokyo", label: "Asia / Tokyo" },
  { value: "Australia/Sydney", label: "Australia / Sydney" },
];

export function PreferencesSection({ state, update }: SectionProps) {
  return (
    <SettingsGroup
      id="settings-preferences"
      eyebrow="02"
      title="Preferences"
      description="Defaults applied when you open the problems table, a solution, or a timeline."
    >
      <SettingRow
        htmlFor="setting-language"
        label="Default language"
        description="The language pre-selected for code views and snippets."
        control={
          <Select
            id="setting-language"
            value={state.defaultLanguage}
            onValueChange={(value) => update("defaultLanguage", value)}
            options={LANGUAGE_OPTIONS}
            aria-label="Default language"
          />
        }
      />

      <SettingRow
        htmlFor="setting-difficulty"
        label="Default difficulty filter"
        description="Applied to the problems table the first time you open it in a session."
        control={
          <Select
            id="setting-difficulty"
            value={state.defaultDifficulty}
            onValueChange={(value) => update("defaultDifficulty", value)}
            options={DIFFICULTY_OPTIONS}
            aria-label="Default difficulty filter"
          />
        }
      />

      <SettingRow
        label="Show failed attempts by default"
        description="Wrong answers and time-limit exceeds are kept in the timeline rather than collapsed away."
        control={
          <Toggle
            checked={state.showFailedAttempts}
            onCheckedChange={(checked) => update("showFailedAttempts", checked)}
            aria-label="Show failed attempts by default"
          />
        }
      />

      <SettingRow
        label="Auto-expand solution evolution"
        description="Opens the full attempt-by-attempt diff when you open a solved problem."
        control={
          <Toggle
            checked={state.autoExpandEvolution}
            onCheckedChange={(checked) => update("autoExpandEvolution", checked)}
            aria-label="Auto-expand solution evolution"
          />
        }
      />

      <SettingRow
        htmlFor="setting-timezone"
        label="Timezone display"
        description="Used for timestamps on submissions, revisions and activity charts."
        control={
          <>
            <Select
              id="setting-timezone"
              value={state.timezone}
              onValueChange={(value) => update("timezone", value as SettingsState["timezone"])}
              options={TIMEZONE_OPTIONS}
              aria-label="Timezone display"
            />
            <TimezonePreview timezone={state.timezone} />
          </>
        }
      />
    </SettingsGroup>
  );
}

/**
 * Shows the wall clock in the selected zone. Formatted on the client only:
 * `Intl.DateTimeFormat` with a fixed zone renders nothing useful on a server
 * that does not know the visitor's locale.
 */
function TimezonePreview({ timezone }: { timezone: string }) {
  const [time, setTime] = React.useState<string | null>(null);

  React.useEffect(() => {
    const tick = () => {
      setTime(
        new Intl.DateTimeFormat(undefined, {
          timeZone: timezone === "local" ? undefined : timezone,
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }).format(new Date()),
      );
    };

    tick();
    const interval = window.setInterval(tick, 30_000);
    return () => window.clearInterval(interval);
  }, [timezone]);

  return (
    <span className="font-technical-sm text-text-faint" aria-live="off">
      {time ? `Now ${time}` : "Now —"}
    </span>
  );
}
