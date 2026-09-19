"use client";

import * as React from "react";
import { THEME_STORAGE_KEY, type Theme } from "@/lib/theme";

/** Dispatched whenever the theme changes, so subscribers can re-snapshot. */
const THEME_CHANGE_EVENT = "codememory:theme-change";

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggle: () => void;
}

/**
 * Site-wide theme state.
 *
 * The class on `<html>` is applied by an inline script in the root layout
 * before first paint, so there is no dark-to-light flash and no layout shift.
 * The DOM class is the source of truth here — `useSyncExternalStore` snapshots
 * it rather than duplicating the preference in React state, so the toggle and
 * the `<html>` class can never disagree. Changing the theme never reloads.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = React.useSyncExternalStore(subscribe, readTheme, readThemeServer);

  const value = React.useMemo<ThemeContextValue>(
    () => ({ theme, setTheme, toggle }),
    [theme],
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

function subscribe(listener: () => void): () => void {
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

function applyTheme(next: Theme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", next === "dark");
  root.classList.toggle("light", next === "light");
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
  } catch {
    /* Storage is unavailable — the preference holds for this session only. */
  }
  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

function setTheme(next: Theme): void {
  if (next === readTheme()) return;
  applyTheme(next);
}

function toggle(): void {
  applyTheme(readTheme() === "dark" ? "light" : "dark");
}
