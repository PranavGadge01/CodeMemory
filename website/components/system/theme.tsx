"use client";

import * as React from "react";
import {
  DEFAULT_THEME_PREFERENCE,
  THEME_STORAGE_KEY,
  THEME_CHANGE_EVENT,
  readThemePreference,
  resolveTheme,
  type Theme,
  type ThemePreference,
} from "@/lib/theme";

/** Dispatched whenever the theme changes, so subscribers can re-snapshot. */
export { THEME_CHANGE_EVENT };

const COLOR_SCHEME_QUERY = "(prefers-color-scheme: dark)";

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

interface ThemeContextValue {
  /** The theme currently rendered. */
  theme: Theme;
  /** The stored preference — `"system"` follows the OS colour scheme. */
  preference: ThemePreference;
  /** Pick an explicit theme. It also becomes the persisted preference, so a
   *  manual choice always wins over `System`. */
  setTheme: (theme: Theme) => void;
  /** Pick a preference, including `system`. */
  setPreference: (preference: ThemePreference) => void;
  /** Switch between the two explicit themes. */
  toggle: () => void;
}

/**
 * Site-wide theme state.
 *
 * The class on `<html>` is applied by an inline script in the root layout
 * before first paint, so there is no dark-to-light flash and no layout shift.
 * The DOM class is the source of truth here — `useSyncExternalStore` snapshots
 * it rather than duplicating the preference in React state, so the toggle, the
 * settings control and the `<html>` class can never disagree. Changing the
 * theme never reloads.
 *
 * The stored value is a *preference*: `dark`, `light` or `system`. `system`
 * stays live — the `<html>` class follows `prefers-color-scheme` while the tab
 * is open — while an explicit choice is pinned, which is what the topbar toggle
 * and the Settings selector both write.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const preference = React.useSyncExternalStore(
    subscribePreference,
    readThemePreference,
    () => DEFAULT_THEME_PREFERENCE,
  );
  const theme = React.useSyncExternalStore(subscribeTheme, readTheme, readThemeServer);

  // "System" is the only preference that can change without a user action, so
  // it is the only one that needs a live listener on the OS colour scheme.
  React.useEffect(() => {
    if (preference !== "system") return;
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(COLOR_SCHEME_QUERY);
    const onChange = () => applyPreference("system");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [preference]);

  const value = React.useMemo<ThemeContextValue>(
    () => ({
      theme,
      preference,
      setTheme,
      setPreference,
      toggle,
    }),
    [theme, preference],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = React.useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside a ThemeProvider");
  }
  return context;
}

function subscribePreference(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(THEME_CHANGE_EVENT, listener);
  return () => window.removeEventListener(THEME_CHANGE_EVENT, listener);
}

function subscribeTheme(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(THEME_CHANGE_EVENT, listener);
  return () => window.removeEventListener(THEME_CHANGE_EVENT, listener);
}

function readTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

/** The server only ever renders the dark theme; the inline script swaps the
 * class before hydration, and nothing rendered depends on the value. */
function readThemeServer(): Theme {
  return "dark";
}

function applyPreference(preference: ThemePreference): void {
  if (typeof document === "undefined") return;
  const next = resolveTheme(preference);
  const root = document.documentElement;
  root.classList.toggle("dark", next === "dark");
  root.classList.toggle("light", next === "light");
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    /* Storage is unavailable — the preference holds for this session only. */
  }
  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

function setTheme(next: Theme): void {
  if (next === readTheme()) return;
  applyPreference(next);
}

function setPreference(next: ThemePreference): void {
  if (next === readThemePreference()) return;
  applyPreference(next);
}

function toggle(): void {
  applyPreference(readTheme() === "dark" ? "light" : "dark");
}
