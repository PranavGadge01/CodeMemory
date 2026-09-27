const KEY = "codememory:onboarding";

export function hasStartedOnboarding(): boolean {
  try { return window.localStorage.getItem(KEY) === "complete"; }
  catch { return false; }
}

export function openWorkspace(): void {
  try { window.localStorage.setItem(KEY, "complete"); } catch { /* Account record remains authoritative. */ }
  // A new document clears every previous account's component and query state.
  window.location.replace("/dashboard");
}
