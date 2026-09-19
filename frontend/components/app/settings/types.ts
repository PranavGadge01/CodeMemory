import type { Density } from "./density-context";

export type Theme = "dark" | "system" | "light";
export type CodeFontSize = "12" | "13" | "14" | "16";
export type ImportFormat = "leetcode-json" | "csv" | "jsonl";
export type SyncFrequency = "manual" | "15m" | "hourly" | "daily";

export interface StorageBreakdown {
  /** Local DuckDB index, in megabytes. */
  duckdb: number;
  /** Archived Parquet files, in megabytes. */
  parquet: number;
  /** Markdown knowledge base, in megabytes. */
  markdown: number;
}

/**
 * Every persisted-looking setting on the page. None of it reaches a backend —
 * this is the shape of the local UI state only.
 */
export interface SettingsState {
  theme: Theme;
  /** Whether the CodeMemory orange carries selected / active states. */
  accentEmphasis: boolean;
  density: Density;
  /** Manual override on top of `prefers-reduced-motion`. */
  reducedMotion: boolean;
  codeFontSize: CodeFontSize;

  defaultLanguage: string;
  defaultDifficulty: string;
  showFailedAttempts: boolean;
  autoExpandEvolution: boolean;
  timezone: string;

  importFormat: ImportFormat;
  syncFrequency: SyncFrequency;
  storage: StorageBreakdown;
}

export type UpdateSetting = <Key extends keyof SettingsState>(
  key: Key,
  value: SettingsState[Key],
) => void;

export interface SectionProps {
  state: SettingsState;
  update: UpdateSetting;
}
