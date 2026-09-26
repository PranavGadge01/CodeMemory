"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { PageContainer } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { Button } from "@/components/ui/button";
import { SettingRow, SettingsGroup, SelectField, Toggle } from "@/components/app/settings/settings";
import { useSettings } from "@/components/app/settings/settings-provider";
import { AccountSection } from "./account-section";
import { useTheme } from "@/components/system/theme";
import type { SettingsDTO } from "@/lib/api/types";
import type { ThemePreference } from "@/lib/theme";

const SECTIONS = [
  { id: "appearance", label: "Appearance" },
  { id: "preferences", label: "Preferences" },
  { id: "account", label: "Account" },
  { id: "data", label: "Data & sync" },
  { id: "about", label: "About" },
];

export function SettingsView() {
  const [active, setActive] = React.useState("appearance");

  const { settings, setSetting } = useSettings();

  // Appearance settings
  const themePreference = settings.theme as ThemePreference;

  const updateSetting = React.useCallback(
    <K extends keyof SettingsDTO>(key: K, value: SettingsDTO[K]) => {
      void setSetting(key, value);
    },
    [setSetting],
  );

  return (
    <PageContainer>
      <div className="flex flex-col gap-3">
        <PageHeader
          eyebrow="Settings"
          title="Preferences"
          description={settings ? "Preferences are saved to your CodeMemory backend." : "Loading settings…"}
        />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[180px_minmax(0,1fr)]">
        {/* Section nav */}
        <nav aria-label="Settings sections" className="hidden lg:block">
          <ul className="sticky top-20 flex flex-col gap-0.5">
            {SECTIONS.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  onClick={() => setActive(section.id)}
                  aria-current={active === section.id ? "page" : undefined}
                  className={cn(
                    "press flex h-8 items-center rounded-md px-2.5 text-body-sm",
                    active === section.id
                      ? "bg-surface-active text-text-primary"
                      : "text-text-muted hover:bg-surface-hover hover:text-text-secondary",
                  )}
                >
                  {section.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex min-w-0 flex-col gap-10">
          <SettingsGroup
            id="appearance"
            eyebrow="Appearance"
            title="Theme and density"
            description="Dark and Light are both finished themes. System follows your operating system's colour scheme, including after the app is open."
          >
             <SettingRow
               label="Theme"
               description="The canvas the whole product renders on. Manual choices — here or in the topbar — are pinned, so they win over System until you switch back."
               htmlFor="theme-select"
             >
               <SelectField
                 id="theme-select"
                 value={themePreference}
                 onChange={(value) => updateSetting("theme", value as ThemePreference)}
                 options={[
                   { label: "Dark", value: "dark" },
                   { label: "System", value: "system" },
                   { label: "Light", value: "light" },
                 ]}
               />
             </SettingRow>
             <SettingRow
               label="Accent emphasis"
               description="Show the CodeMemory orange on selected states and key progress indicators."
             >
               <Toggle
                 checked={settings.accentEmphasis}
                 onChange={(v) => updateSetting("accentEmphasis", v)}
                 label="Accent emphasis"
               />
             </SettingRow>
             <SettingRow label="Compact density" description="Tighten row padding across tables and lists.">
               <Toggle checked={settings.compactDensity} onChange={(v) => updateSetting("compactDensity", v)} label="Compact density" />
             </SettingRow>
             <SettingRow
               label="Reduce motion"
               description="Disable reveal animations and the tactile press feedback."
             >
               <Toggle checked={settings.reducedMotion} onChange={(v) => updateSetting("reducedMotion", v)} label="Reduce motion" />
             </SettingRow>
             <SettingRow label="Code font size" htmlFor="font-size" description="Applied to solution and diff views.">
               <SelectField
                 id="font-size"
                 value={String(settings.codeFontSize)}
                 onChange={(v) => updateSetting("codeFontSize", v as SettingsDTO["codeFontSize"])}
                 options={[
                   { label: "12 px", value: "12" },
                   { label: "13 px", value: "13" },
                   { label: "14 px", value: "14" },
                   { label: "16 px", value: "16" },
                 ]}
               />
             </SettingRow>
             {themePreference === "system" ? (
               <SystemThemeNote />
             ) : null}
          </SettingsGroup>

          <SettingsGroup
            id="preferences"
            eyebrow="Preferences"
            title="Defaults"
            description="How CodeMemory presents your history when you open a page."
          >
             <SettingRow label="Default code language" htmlFor="default-language" description="Used for syntax in solution views.">
               <SelectField
                 id="default-language"
                 value={settings.defaultCodeLanguage}
                 onChange={(v) => updateSetting("defaultCodeLanguage", v)}
                 options={[
                   { label: "Python 3", value: "python3" },
                   { label: "Java", value: "java" },
                   { label: "C++", value: "cpp" },
                   { label: "JavaScript", value: "javascript" },
                   { label: "Go", value: "go" },
                 ]}
               />
             </SettingRow>
             <SettingRow label="Default difficulty filter" htmlFor="default-difficulty" description="Pre-selected on the problems table.">
               <SelectField
                 id="default-difficulty"
                 value={settings.defaultDifficulty}
                 onChange={(v) => updateSetting("defaultDifficulty", v as SettingsDTO["defaultDifficulty"])}
                 options={[
                   { label: "All difficulties", value: "all" },
                   { label: "Easy", value: "easy" },
                   { label: "Medium", value: "medium" },
                   { label: "Hard", value: "hard" },
                 ]}
               />
             </SettingRow>
             <SettingRow label="Show failed attempts" description="List Wrong Answer and TLE submissions by default, not only accepted ones.">
               <Toggle checked={settings.showFailedAttempts} onChange={(v) => updateSetting("showFailedAttempts", v)} label="Show failed attempts" />
             </SettingRow>
             <SettingRow label="Auto-expand solution evolution" description="Open the attempt trace when a problem detail opens.">
               <Toggle checked={settings.autoExpandEvolution} onChange={(v) => updateSetting("autoExpandEvolution", v)} label="Auto-expand solution evolution" />
             </SettingRow>
             <SettingRow label="Timestamp display" htmlFor="timezone" description="Relative times are always local.">
               <SelectField
                 id="timezone"
                 value={settings.timestampDisplay}
                 onChange={(v) => updateSetting("timestampDisplay", v as SettingsDTO["timestampDisplay"])}
                 options={[
                   { label: "Local timezone", value: "local" },
                   { label: "UTC", value: "utc" },
                 ]}
               />
             </SettingRow>
          </SettingsGroup>

          <AccountSection />

          <SettingsGroup
            id="data"
            eyebrow="Data & sync"
            title="Data management"
            description="The current API does not expose file import, index rebuild, or data deletion actions in this screen."
          >
            <SettingRow label="Automatic sync" description="Read-only status reported by the backend. No frequency setting is available here.">
              <span className="font-technical-sm text-text-secondary" role="status">
                {settings.autosyncEnabled ? "Enabled" : "Disabled"}
              </span>
            </SettingRow>
            <div className="border-t border-border-soft px-5 py-4 text-body-sm text-text-muted">
              Import, rebuild, and clear operations are unavailable through the current frontend API. No file or data changes have been made.
            </div>
          </SettingsGroup>

          <SettingsGroup id="about" eyebrow="About" title="Build information">
            <div className="px-5 py-4">
              <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
                <Definition label="Product" value="CodeMemory" />
                <Definition label="Version" value={settings.version ?? "1.0.0"} mono />
                <Definition label="Build" value="Development build" mono />
                <Definition label="Storage" value="DuckDB · Parquet · Markdown" mono />
              </dl>
              <div className="mt-5">
                <div className="eyebrow mb-2">Storage layout</div>
                <ul className="space-y-2 text-body-sm text-text-secondary">
                  <li>DuckDB index — problems, attempts, submissions</li>
                  <li>Parquet shards — analytics and revision caches</li>
                  <li>Markdown knowledge base — your notes and patterns</li>
                </ul>
              </div>
              <div className="mt-5 flex flex-wrap gap-2 border-t border-border-soft pt-4">
                <Button variant="ghost" size="sm" asChild>
                  <a href="#product">Design system</a>
                </Button>
                <Button variant="ghost" size="sm" asChild>
                  <a href="#evolution">How it works</a>
                </Button>
              </div>
            </div>
          </SettingsGroup>
        </div>
      </div>
    </PageContainer>
  );
}

/** What System currently resolves to, read from the rendered `<html>` class so
 *  it follows a live OS colour-scheme change rather than a stale snapshot. */
function SystemThemeNote() {
  const { theme } = useTheme();
  return (
    <div className="px-5 py-3 text-caption text-text-faint">
      {`Following your system — currently ${theme}.`}
    </div>
  );
}

function Definition({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="eyebrow">{label}</dt>
      <dd
        className={cn(
          "mt-1 text-body-sm text-text-secondary",
          mono && "font-technical text-text-muted",
        )}
      >
        {value}
      </dd>
    </div>
  );
}
