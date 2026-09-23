/**
 * Settings state store — the frontend's in-memory mirror of the backend
 * ``/settings`` resource.
 *
 * Architecture:
 *   Backend JSON file  →  GET /settings  →  SettingsProvider  →  UI
 *
 * On mount the provider fetches persisted settings from the backend.  The
 * returned model becomes the single in-memory source for every component.
 * When a user flips a switch:
 *   1. frontend state updates immediately (UI responds without network latency)
 *   2. a PATCH /settings request fires to persist the change
 *   3. on failure the previous value is restored and an error is surfaced
 *
 * Theme is the one exception that also reads ``localStorage`` on first render
 * — the no-flash script in ``layout.tsx`` applies the class before React
 * mounts, so localStorage acts as an SSR/readiness cache.  After the backend
 * responds, the backend value is authoritative and overwrites localStorage.
 */

"use client";

import * as React from "react";
import { getSettings, updateSettings } from "@/lib/api";
import type { SettingsDTO } from "@/lib/api/types";
import {
  DEFAULT_THEME_PREFERENCE,
  THEME_CHANGE_EVENT,
  THEME_STORAGE_KEY,
  type Theme,
  type ThemePreference,
  isThemePreference,
  readThemePreference,
  resolveTheme,
} from "@/lib/theme";

type ThemePref = ThemePreference;
const asThemePref = (v: string): ThemePref => (isThemePreference(v) ? (v as ThemePref) : DEFAULT_THEME_PREFERENCE);

const DEFAULTS: SettingsDTO = {
  leetcodeConnected: false,
  autosyncEnabled: false,
  dataDir: "data",
  version: "1.0.0",
  theme: DEFAULT_THEME_PREFERENCE,
  accentEmphasis: true,
  compactDensity: false,
  reducedMotion: false,
  codeFontSize: "13",
  defaultCodeLanguage: "python3",
  defaultDifficulty: "all",
  showFailedAttempts: true,
  autoExpandEvolution: false,
  timestampDisplay: "local",
};

type SettingsState = SettingsDTO;
type SetSetting = <K extends keyof SettingsState>(
  key: K,
  value: SettingsState[K],
) => Promise<void>;

interface SettingsContextValue {
  settings: SettingsState;
  setSetting: SetSetting;
  updateSettingsBatch: (patch: Partial<SettingsDTO>) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  /** Resolved theme (dark/light) for the current preference. */
  resolvedTheme: Theme;
  /** Convenience: set theme preference (including "system"). */
  setTheme: (preference: ThemePref) => Promise<void>;
}

const SettingsContext = React.createContext<SettingsContextValue | null>(null);

export function useSettings(): SettingsContextValue {
  const ctx = React.useContext(SettingsContext);
  if (!ctx) {
    throw new Error("useSettings must be used within a SettingsProvider");
  }
  return ctx;
}

/** Apply non-theme appearance settings to the document element. */
function applyAppearance(settings: SettingsState): void {
  if (typeof document === "undefined") return;

  const root = document.documentElement;

  // Compact density via data attribute
  root.setAttribute("data-density", settings.compactDensity ? "compact" : "comfortable");

  // Accent emphasis via data attribute
  root.setAttribute("data-accent", settings.accentEmphasis ? "on" : "off");

  // Reduced motion override via data attribute
  root.setAttribute("data-reduced-motion", settings.reducedMotion ? "on" : "off");

  // Code font size via CSS custom property
  root.style.setProperty("--code-font-size", `${settings.codeFontSize}px`);

  // Timestamp display via data attribute (consumed by format utilities)
  root.setAttribute("data-timestamp-display", settings.timestampDisplay);
}

/** Apply theme class + localStorage (read-only cache for no-flash script). */
function applyTheme(preference: ThemePref): void {
  if (typeof document === "undefined") return;

  const theme = resolveTheme(preference);
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.classList.toggle("light", theme === "light");

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    /* storage unavailable — preference is session-only */
  }
  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

/** Merge a partial patch onto the defaults. */
function mergeSettings(patch: Partial<SettingsDTO>): SettingsState {
  return { ...DEFAULTS, ...patch } as SettingsState;
}

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = React.useState<SettingsState>(() => {
    // Seed from localStorage on first render so the no-flash script's class
    // is not immediately overwritten before the backend responds.
    const cachedTheme = readThemePreference();
    return { ...DEFAULTS, theme: cachedTheme };
  });
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const resolvedTheme: Theme = React.useMemo(() => {
    return resolveTheme(asThemePref(settings.theme));
  }, [settings.theme]);

  // Initial fetch: backend is authoritative.  After this resolves, the
  // in-memory state matches what is persisted server-side.
  React.useEffect(() => {
    let cancelled = false;

    getSettings()
      .then((fresh) => {
        if (cancelled) return;
        const merged = mergeSettings(fresh);
        setSettings(merged);
        applyAppearance(merged);
         applyTheme(asThemePref(merged.theme));
        setIsLoading(false);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setIsLoading(false);
        // Keep the localStorage-seeded defaults so the UI is usable even
        // when the backend is unreachable.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Apply appearance CSS whenever those values change.
  React.useEffect(() => {
    applyAppearance(settings);
  }, [
    settings.compactDensity,
    settings.accentEmphasis,
    settings.reducedMotion,
    settings.codeFontSize,
    settings.timestampDisplay,
    settings,
  ]);

  // Apply theme class whenever the theme preference changes.
  React.useEffect(() => {
    applyTheme(asThemePref(settings.theme));
  }, [settings.theme]);

  const setSetting = React.useCallback<SetSetting>(async (key, value) => {
    const prev = settings;
    const next = { ...settings, [key]: value } as SettingsState;

    setError(null);

    // 1. Optimistically update frontend state
    setSettings(next);

    try {
      // 2. Persist to backend (PUT request with partial body)
      const patched = await updateSettings({ [key]: value } as Partial<SettingsDTO>);
      // 3. Reconcile with whatever the backend actually stored
      const merged = mergeSettings(patched);
      setSettings(merged);
    } catch (err) {
      // 4. Restore previous state on failure
      setSettings(prev);
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [settings]);

  const updateSettingsBatch = React.useCallback<SettingsContextValue["updateSettingsBatch"]>(
    async (patch) => {
      const prev = settings;
      const next = { ...settings, ...patch } as SettingsState;

      setError(null);
      setSettings(next);

      try {
        const patched = await updateSettings(patch);
        const merged = mergeSettings(patched);
        setSettings(merged);
      } catch (err) {
        setSettings(prev);
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [settings],
  );

  const setTheme = React.useCallback<SettingsContextValue["setTheme"]>(
    async (preference) => {
      await setSetting("theme", preference);
    },
    [setSetting],
  );

  const value = React.useMemo<SettingsContextValue>(
    () => ({
      settings,
      setSetting,
      updateSettingsBatch,
      isLoading,
      error,
      resolvedTheme,
      setTheme,
    }),
    [settings, setSetting, updateSettingsBatch, isLoading, error, resolvedTheme, setTheme],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

/**
 * Subscribe to theme changes from the legacy localStorage-based toggle.
 * Kept so the existing ``useTheme`` provider and topbar toggle continue
 * working alongside the settings store.
 */
export function useThemeFromSettings() {
  const { settings, setTheme } = useSettings();
  const [theme, setThemeClass] = React.useState<Theme>(() => resolveTheme(asThemePref(settings.theme)));

  React.useEffect(() => {
    const handler = () => {
      const pref = readThemePreference();
      setThemeClass(resolveTheme(pref));
    };
    window.addEventListener(THEME_CHANGE_EVENT, handler);
    return () => window.removeEventListener(THEME_CHANGE_EVENT, handler);
  }, []);

  return {
    theme,
    preference: asThemePref(settings.theme),
    setPreference: setTheme,
  };
}
