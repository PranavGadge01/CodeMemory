"use client";

import * as React from "react";
import { Check, Trash2, AlertTriangle, UploadCloud, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageContainer } from "@/components/app/page-container";
import { PageHeader } from "@/components/app/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SettingRow, SettingsGroup, SelectField, Toggle } from "@/components/app/settings/settings";
import { useTheme } from "@/components/system/theme";
import type { ThemePreference } from "@/lib/theme";

const SECTIONS = [
  { id: "appearance", label: "Appearance" },
  { id: "preferences", label: "Preferences" },
  { id: "account", label: "Account" },
  { id: "data", label: "Data & sync" },
  { id: "about", label: "About" },
];

type ImportStatus = "idle" | "working" | "done";
type RebuildStatus = "idle" | "working" | "done";

/**
 * Settings.
 *
 * Every control here is UI state only. Nothing is persisted to a backend, and
 * destructive actions are gated behind a typed confirmation — the intent is a
 * complete, honest shell that later gets a real persistence layer.
 */
export function SettingsView() {
  const [active, setActive] = React.useState("appearance");

  // The one setting with a real effect: the theme preference the root layout
  // reads before first paint. Everything else below is local UI state.
  const { preference: themePreference, setPreference: setThemePreference } = useTheme();
  const [accentEmphasis, setAccentEmphasis] = React.useState(true);
  const [compact, setCompact] = React.useState(false);
  const [reducedMotion, setReducedMotion] = React.useState(false);
  const [codeFontSize, setCodeFontSize] = React.useState("13");

  // Preferences
  const [defaultLanguage, setDefaultLanguage] = React.useState("python3");
  const [defaultDifficulty, setDefaultDifficulty] = React.useState("all");
  const [showFailed, setShowFailed] = React.useState(true);
  const [autoExpand, setAutoExpand] = React.useState(false);
  const [timezone, setTimezone] = React.useState("local");

  // Account + data
  const [leetcodeConnected, setLeetcodeConnected] = React.useState(true);
  const [codeforcesConnected, setCodeforcesConnected] = React.useState(false);
  const [hackerrankConnected, setHackerrankConnected] = React.useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = React.useState(false);
  const [importSource, setImportSource] = React.useState("json");
  const [importStatus, setImportStatus] = React.useState<ImportStatus>("idle");
  const [rebuildStatus, setRebuildStatus] = React.useState<RebuildStatus>("idle");
  const [confirmClear, setConfirmClear] = React.useState(false);
  const [clearPhrase, setClearPhrase] = React.useState("");

  const onImport = React.useCallback(() => {
    setImportStatus("working");
    window.setTimeout(() => setImportStatus("done"), 900);
  }, []);

  const onRebuild = React.useCallback(() => {
    setRebuildStatus("working");
    window.setTimeout(() => setRebuildStatus("done"), 1200);
  }, []);

  return (
    <PageContainer>
      <div className="flex flex-col gap-3">
        <PageHeader
          eyebrow="Settings"
          title="Preferences"
          description="Everything is stored locally in this build. No preference leaves this browser."
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
                onChange={(value) => setThemePreference(value as ThemePreference)}
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
              <Toggle checked={accentEmphasis} onChange={setAccentEmphasis} label="Accent emphasis" />
            </SettingRow>
            <SettingRow label="Compact density" description="Tighten row padding across tables and lists.">
              <Toggle checked={compact} onChange={setCompact} label="Compact density" />
            </SettingRow>
            <SettingRow
              label="Reduce motion"
              description="Disable reveal animations and the tactile press feedback."
            >
              <Toggle checked={reducedMotion} onChange={setReducedMotion} label="Reduce motion" />
            </SettingRow>
            <SettingRow label="Code font size" htmlFor="font-size" description="Applied to solution and diff views.">
              <SelectField
                id="font-size"
                value={codeFontSize}
                onChange={setCodeFontSize}
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
                value={defaultLanguage}
                onChange={setDefaultLanguage}
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
                value={defaultDifficulty}
                onChange={setDefaultDifficulty}
                options={[
                  { label: "All difficulties", value: "all" },
                  { label: "Easy", value: "easy" },
                  { label: "Medium", value: "medium" },
                  { label: "Hard", value: "hard" },
                ]}
              />
            </SettingRow>
            <SettingRow label="Show failed attempts" description="List Wrong Answer and TLE submissions by default, not only accepted ones.">
              <Toggle checked={showFailed} onChange={setShowFailed} label="Show failed attempts" />
            </SettingRow>
            <SettingRow label="Auto-expand solution evolution" description="Open the attempt trace when a problem detail opens.">
              <Toggle checked={autoExpand} onChange={setAutoExpand} label="Auto-expand solution evolution" />
            </SettingRow>
            <SettingRow label="Timestamp display" htmlFor="timezone" description="Relative times are always local.">
              <SelectField
                id="timezone"
                value={timezone}
                onChange={setTimezone}
                options={[
                  { label: "Local timezone", value: "local" },
                  { label: "UTC", value: "utc" },
                ]}
              />
            </SettingRow>
          </SettingsGroup>

          <SettingsGroup
            id="account"
            eyebrow="Account"
            title="Connected platforms"
            description="Import is read-only and file-based. CodeMemory never stores account credentials."
          >
            <PlatformRow
              name="LeetCode"
              username={leetcodeConnected ? "jay.patil" : null}
              connected={leetcodeConnected}
              onToggle={() => {
                if (leetcodeConnected) {
                  setConfirmDisconnect(true);
                } else {
                  setLeetcodeConnected(true);
                }
              }}
            />
            <PlatformRow
              name="Codeforces"
              username={codeforcesConnected ? "jaypatil" : null}
              connected={codeforcesConnected}
              onToggle={() => setCodeforcesConnected((prev) => !prev)}
            />
            <PlatformRow
              name="HackerRank"
              username={hackerrankConnected ? "jay_patil" : null}
              connected={hackerrankConnected}
              onToggle={() => setHackerrankConnected((prev) => !prev)}
            />
            {confirmDisconnect ? (
              <div className="border-t border-warning/20 bg-warning-soft/40 px-5 py-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <div className="text-body-sm font-medium text-text-primary">
                      Disconnect LeetCode?
                    </div>
                    <p className="mt-1 text-caption text-text-muted">
                      Previously imported submissions stay in your local index. Future imports from
                      this account will need re-connecting.
                    </p>
                    <div className="mt-3 flex gap-2">
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => {
                          setLeetcodeConnected(false);
                          setConfirmDisconnect(false);
                        }}
                      >
                        Disconnect
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setConfirmDisconnect(false)}>
                        Keep connected
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </SettingsGroup>

          <SettingsGroup
            id="data"
            eyebrow="Data & sync"
            title="Import and index"
            description="Mock in this build — no file is read and no index is written."
          >
            <SettingRow label="Import source" htmlFor="import-source" description="CodeMemory imports JSON, CSV and JSONL exports.">
              <SelectField
                id="import-source"
                value={importSource}
                onChange={setImportSource}
                options={[
                  { label: "LeetCode export (JSON)", value: "json" },
                  { label: "CSV", value: "csv" },
                  { label: "JSONL", value: "jsonl" },
                ]}
              />
            </SettingRow>
            <div className="px-5 py-4">
              <div className="eyebrow mb-2">Dataset</div>
              <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border-strong bg-surface-card px-6 py-10 text-center">
                <UploadCloud className="h-5 w-5 text-text-faint" aria-hidden="true" />
                <div className="text-body-sm text-text-secondary">
                  Drop a {importSource.toUpperCase()} export here
                </div>
                <div className="text-caption text-text-faint">
                  Deduplicated by SHA-256. Nothing is uploaded anywhere.
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onImport}
                  disabled={importStatus === "working"}
                >
                  {importStatus === "working" ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                      Validating…
                    </>
                  ) : importStatus === "done" ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" />
                      Preview ready
                    </>
                  ) : (
                    "Choose a file"
                  )}
                </Button>
              </div>
            </div>
            <SettingRow
              label="Rebuild memory index"
              description="Re-embeds memory documents whose content hash changed."
            >
              <Button
                variant="subtle"
                size="sm"
                onClick={onRebuild}
                disabled={rebuildStatus === "working"}
              >
                {rebuildStatus === "working" ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                    Rebuilding…
                  </>
                ) : rebuildStatus === "done" ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-success" aria-hidden="true" />
                    63 documents indexed
                  </>
                ) : (
                  "Rebuild index"
                )}
              </Button>
            </SettingRow>
            <SettingRow label="Sync frequency" htmlFor="sync-frequency" description="How often the local index refreshes while the app is open.">
              <SelectField
                id="sync-frequency"
                value="manual"
                onChange={() => {}}
                options={[
                  { label: "Manual only", value: "manual" },
                  { label: "Every 15 minutes", value: "15m" },
                  { label: "Every hour", value: "1h" },
                ]}
              />
            </SettingRow>

            <div className="border-t border-error/20 bg-error-soft/30 px-5 py-4">
              <div className="eyebrow text-error">Danger zone</div>
              <div className="mt-2 text-body-sm font-medium text-text-primary">
                Clear all data
              </div>
              <p className="mt-1 text-caption text-text-muted">
                Deletes the local DuckDB index, every Parquet shard and the Markdown knowledge
                base. This cannot be undone.
              </p>
              {confirmClear ? (
                <div className="mt-4">
                  <label htmlFor="clear-phrase" className="text-caption text-text-secondary">
                    Type <span className="font-mono text-error">clear everything</span> to confirm
                  </label>
                  <input
                    id="clear-phrase"
                    type="text"
                    value={clearPhrase}
                    onChange={(event) => setClearPhrase(event.target.value)}
                    placeholder="clear everything"
                    className="mt-2 h-9 w-full max-w-xs rounded-md border border-border bg-surface px-3 text-body-sm text-text-primary focus:border-error focus:outline-none focus:ring-1 focus:ring-error/40"
                  />
                  <div className="mt-3 flex gap-2">
                    <Button
                      variant="danger"
                      size="sm"
                      disabled={clearPhrase.trim().toLowerCase() !== "clear everything"}
                      onClick={() => {
                        setConfirmClear(false);
                        setClearPhrase("");
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Clear all data
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setConfirmClear(false)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <Button variant="danger" size="sm" className="mt-4" onClick={() => setConfirmClear(true)}>
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  Clear all data
                </Button>
              )}
            </div>
          </SettingsGroup>

          <SettingsGroup id="about" eyebrow="About" title="Build information">
            <div className="px-5 py-4">
              <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
                <Definition label="Product" value="CodeMemory" />
                <Definition label="Version" value="1.0.0" mono />
                <Definition label="Build" value="0a4f9c2" mono />
                <Definition label="Storage" value="DuckDB · Parquet · Markdown" mono />
              </dl>
              <div className="mt-5 border-t border-border-soft pt-4">
                <div className="eyebrow mb-2">Local storage breakdown</div>
                <div className="flex h-2 overflow-hidden rounded-full bg-surface-card">
                  <span className="h-full bg-accent/80" style={{ width: "52%" }} aria-hidden="true" />
                  <span className="h-full bg-info/60" style={{ width: "28%" }} aria-hidden="true" />
                  <span className="h-full bg-success/60" style={{ width: "20%" }} aria-hidden="true" />
                </div>
                <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1">
                  <StorageLabel color="bg-accent/80" name="DuckDB index" size="412 MB" />
                  <StorageLabel color="bg-info/60" name="Parquet shards" size="226 MB" />
                  <StorageLabel color="bg-success/60" name="Markdown KB" size="88 MB" />
                </div>
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

function PlatformRow({
  name,
  username,
  connected,
  onToggle,
}: {
  name: string;
  username: string | null;
  connected: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 px-5 py-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2.5">
          <span className="text-body-sm font-medium text-text-primary">{name}</span>
          {connected ? (
            <Badge variant="success">Connected</Badge>
          ) : (
            <Badge variant="neutral">Not connected</Badge>
          )}
        </div>
        {username ? (
          <div className="mt-1 font-technical-sm text-text-faint">@{username}</div>
        ) : (
          <div className="mt-1 text-caption text-text-faint">
            Import a {name} export to connect.
          </div>
        )}
      </div>
      <Button
        type="button"
        variant={connected ? "outline" : "subtle"}
        size="sm"
        onClick={onToggle}
        aria-pressed={connected}
      >
        {connected ? "Disconnect" : "Connect"}
      </Button>
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

function StorageLabel({ color, name, size }: { color: string; name: string; size: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-technical-sm text-text-muted">
      <span className={cn("h-2 w-2 rounded-full", color)} aria-hidden="true" />
      {name} <span className="text-text-faint">{size}</span>
    </span>
  );
}
