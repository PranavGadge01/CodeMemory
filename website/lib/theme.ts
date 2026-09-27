/**
 * Theme constants shared by the server layout and the client provider.
 *
 * This module deliberately holds no client code: the no-flash script in the
 * root layout runs on the server, and values exported from a `"use client"`
 * boundary are not readable there.
 */

/** The theme actually rendered on `<html>`. */
export type Theme = "dark" | "light";

/** The stored preference. `"system"` defers to the OS colour scheme. */
export type ThemePreference = Theme | "system";

/**
 * The storage key the no-flash script in the root layout reads. Dark is the
 * CodeMemory default, so an unset or unreadable preference always resolves to
 * dark rather than to the OS colour scheme. Settings and the topbar toggle
 * write to the same key, so there is a single source of truth.
 */
export const THEME_STORAGE_KEY = "codememory:theme";

/** Dispatched on `window` whenever the theme changes, so every subscriber
 *  snapshotting via `useSyncExternalStore` can re-read in lockstep. */
export const THEME_CHANGE_EVENT = "codememory:theme-change";

/** The preference used when none is stored, or storage is unreadable. */
export const DEFAULT_THEME_PREFERENCE: ThemePreference = "dark";

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "dark" || value === "light" || value === "system";
}

/** Reads the stored preference without resolving the OS colour scheme. */
export function readThemePreference(): ThemePreference {
  if (typeof window === "undefined") return DEFAULT_THEME_PREFERENCE;
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(stored) ? stored : DEFAULT_THEME_PREFERENCE;
  } catch {
    /* Storage is unavailable — the preference holds for this session only. */
    return DEFAULT_THEME_PREFERENCE;
  }
}

/**
 * The OS colour scheme. Dark when the query is unavailable (SSR, blocked
 * storage, private browsing) so the no-flash script and the provider always
 * agree on a default.
 */
export function systemTheme(): Theme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return "dark";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Resolve a preference to the theme that should be rendered. */
export function resolveTheme(preference: ThemePreference): Theme {
  return preference === "system" ? systemTheme() : preference;
}
