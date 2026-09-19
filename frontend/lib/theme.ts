/**
 * Theme constants shared by the server layout and the client provider.
 *
 * This module deliberately holds no client code: the no-flash script in the
 * root layout runs on the server, and values exported from a `"use client"`
 * boundary are not readable there.
 */

export type Theme = "dark" | "light";

/**
 * The storage key the no-flash script in the root layout reads. Dark is the
 * CodeMemory default, so an unset or unreadable preference always resolves to
 * dark rather than to the OS colour scheme.
 */
export const THEME_STORAGE_KEY = "codememory:theme";
