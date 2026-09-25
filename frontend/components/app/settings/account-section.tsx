"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Code2, Swords, Terminal } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiGet, apiPost, apiDelete } from "@/lib/api/client";
import { SettingsGroup } from "./settings-group";
import { ConfirmAction } from "./confirm-action";
import { Button } from "@/components/ui/button";

type PlatformId = "leetcode" | "codeforces" | "hackerrank";

interface PlatformState {
  connected: boolean;
  connecting: boolean;
  handle: string;
}

// LeetCode authenticated sync states
interface LeetCodeAuthState {
  credentialsStored: boolean;
  validationMessage: string | null;
  validating: boolean;
  syncing: boolean;
  lastSyncStatus: string | null;
  lastSyncTime: string | null;
  syncProgress: {
    recordsDiscovered: number;
    recordsAdded: number;
    recordsSkipped: number;
    recordsFailed: number;
    codeFetched: number;
    codeFailed: number;
    status: string;
    errorMessage: string | null;
  } | null;
}

const PLATFORMS: {
  id: PlatformId;
  name: string;
  icon: LucideIcon;
  /** Handle shown for the preview-only platform connections. */
  handle: string;
  description: string;
}[] = [
  {
    id: "leetcode",
    name: "LeetCode",
    icon: Code2,
    handle: "",
    description: "Submissions, contest history and problem metadata.",
  },
  {
    id: "codeforces",
    name: "Codeforces",
    icon: Swords,
    handle: "codememory",
    description: "Rating history and contest submissions.",
  },
  {
    id: "hackerrank",
    name: "HackerRank",
    icon: Terminal,
    handle: "codememory",
    description: "Skill assessments and practice submissions.",
  },
];

/**
 * LeetCode connection state is loaded from FastAPI. Other platform rows remain
 * local preview states until their integrations are implemented.
 */
export function AccountSection() {
  const router = useRouter();
  const [platforms, setPlatforms] = React.useState<Record<PlatformId, PlatformState>>({
    leetcode: { connected: false, connecting: false, handle: "" },
    codeforces: { connected: false, connecting: false, handle: "codememory" },
    hackerrank: { connected: false, connecting: false, handle: "codememory" },
  });

  // LeetCode authenticated sync state
  const [authState, setAuthState] = React.useState<LeetCodeAuthState>({
    credentialsStored: false,
    validationMessage: null,
    validating: false,
    syncing: false,
    lastSyncStatus: null,
    lastSyncTime: null,
    syncProgress: null,
  });

  // Form state for credentials
  const [session, setSession] = React.useState("");
  const [csrfToken, setCsrfToken] = React.useState("");
  const [consentGiven, setConsentGiven] = React.useState(false);

  // Check if credentials are already stored on mount
  React.useEffect(() => {
    (async () => {
      try {
        const account = await apiGet<any>("/leetcode/status");
        setPlatforms(prev => ({
          ...prev,
          leetcode: {
            connected: Boolean(account?.connected),
            connecting: false,
            handle: account?.username || "",
          },
        }));
      } catch {
        // An unavailable backend must not show a fabricated connected account.
      }
      try {
        const status = await apiPost<any>("/leetcode/auth/validate");
        setAuthState(prev => ({
          ...prev,
          credentialsStored: Boolean(status?.credentialsStored),
          validationMessage: status?.validationMessage || null,
        }));
      } catch {
        setAuthState(prev => ({
          ...prev,
          validationMessage: "Could not check the stored LeetCode session. Try again when the backend is available.",
        }));
      }
    })();
  }, []);

  const connect = (platform: PlatformId, handle: string) => {
    if (platform === "leetcode") {
      router.push("/connect");
      return;
    }
    setPlatforms((prev) => ({ ...prev, [platform]: { ...prev[platform], connecting: true } }));

    window.setTimeout(() => {
      setPlatforms((prev) => ({
        ...prev,
        [platform]: { connected: true, connecting: false, handle },
      }));
    }, 900);
  };

  const disconnect = async (platform: PlatformId) => {
    if (platform === "leetcode") {
      try {
        await apiDelete<any>("/leetcode/connect");
      } catch (error) {
        alert(`Failed to disconnect LeetCode: ${error instanceof Error ? error.message : String(error)}`);
        return;
      }
    }
    setPlatforms((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], connected: false, connecting: false },
    }));
  };

  // Authenticated LeetCode functions
  const validateAndSaveCredentials = async () => {
    setAuthState(prev => ({ ...prev, validating: true }));
    try {
      // Call backend to store credentials
      const res = await apiPost<any>("/leetcode/auth/store", { session, csrf_token: csrfToken });
      setAuthState(prev => ({ ...prev, credentialsStored: Boolean(res?.credentialsStored), validationMessage: null, validating: false }));
      setConsentGiven(true);
    } catch (error) {
      setAuthState(prev => ({ ...prev, validating: false }));
      alert(`Failed to validate credentials: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const syncFullHistory = async () => {
    setAuthState((prev) => ({ ...prev, syncing: true, syncProgress: {
      recordsDiscovered: 0,
      recordsAdded: 0,
      recordsSkipped: 0,
      recordsFailed: 0,
      codeFetched: 0,
      codeFailed: 0,
      status: "syncing",
      errorMessage: null,
    } }));
    try {
      // Real backend call to sync full history
      const res = await apiPost<any>("/leetcode/auth/sync");
      // Update UI with backend response (BaseCamelModel serializes as camelCase)
      setAuthState((prev) => ({
        ...prev,
        syncing: false,
        lastSyncStatus: res.status,
        lastSyncTime: new Date().toLocaleString(),
        syncProgress: {
          recordsDiscovered: res.recordsDiscovered ?? 0,
          recordsAdded: res.recordsAdded ?? 0,
          recordsSkipped: res.recordsSkipped ?? 0,
          recordsFailed: res.recordsFailed ?? 0,
          codeFetched: res.codeFetched ?? 0,
          codeFailed: res.codeFailed ?? 0,
          status: res.status,
          errorMessage: res.errorMessage ?? null,
        },
      }));
    } catch (error) {
      setAuthState((prev) => ({
        ...prev,
        syncing: false,
        syncProgress: {
          ...(prev.syncProgress || {
            recordsDiscovered: 0,
            recordsAdded: 0,
            recordsSkipped: 0,
            recordsFailed: 0,
            codeFetched: 0,
            codeFailed: 0,
            status: "failed",
            errorMessage: null,
          }),
          status: "failed",
          errorMessage: error instanceof Error ? error.message : String(error),
        }
      }));
    }
  };

  const revokeCredentials = async () => {
    try {
      await apiDelete<any>("/leetcode/auth/revoke");
      setAuthState((prev) => ({ ...prev, credentialsStored: false, validationMessage: null, syncProgress: null, lastSyncStatus: null, lastSyncTime: null }));
      setSession("");
      setCsrfToken("");
      setConsentGiven(false);
    } catch (error) {
      alert(`Failed to revoke credentials: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <SettingsGroup
      id="account"
      eyebrow="03"
      title="Account"
      description="Connect LeetCode to sync your submission history. Other platform connections are preview-only."
    >
      {PLATFORMS.map((platform) => {
        const state = platforms[platform.id];
        const Icon = platform.icon;

        return (
          <div key={platform.id} className="flex flex-col gap-3 px-5 py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-surface-card text-text-muted">
                  <Icon className="h-[18px] w-[18px]" aria-hidden="true" strokeWidth={1.75} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-body-sm font-medium text-text-primary">
                      {platform.name}
                    </span>
                    <ConnectionBadge connected={state.connected} connecting={state.connecting} />
                  </div>
                  {state.connected ? (
                    <div className="mt-1 font-technical-sm text-text-muted">
                      @{state.handle}
                    </div>
                  ) : (
                    <div className="mt-1 text-body-sm text-text-muted">{platform.description}</div>
                  )}
                </div>
              </div>

              {state.connected ? (
                <>
                  {platform.id === "leetcode" && (
                    <>
                      {/* LeetCode Account Actions */}
                      {/* Authenticated Sync Section */}
                      <div className="mt-4 p-4 border border-border/50 rounded-lg">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-font-semibold text-text-primary">Full History (Authenticated)</h3>
                          <Button variant="ghost" size="sm" onClick={() => setConsentGiven(!consentGiven)}>
                            {consentGiven ? "Hide Form" : "Add Credentials"}
                          </Button>
                        </div>

                        {authState.validationMessage && (
                          <div role="status" className="mb-3 text-sm text-destructive">
                            {authState.validationMessage}
                          </div>
                        )}

                        {/* Credential Status */}
                        <div className="mb-3 p-3 bg-surface-card border border-border/25 rounded">
                          <div className="flex items-center gap-2 text-text-muted text-sm">
                            <span className="h-3 w-3 rounded-full">
                              {authState.credentialsStored ? (
                                <span className="bg-success" />
                              ) : (
                                <span className="bg-text-disabled" />
                              )}
                            </span>
                            <span>
                              {authState.credentialsStored ? "Credentials stored" : "No credentials stored"}
                            </span>
                          </div>
                        </div>

                        {/* Last Sync Info */}
                        {authState.lastSyncStatus || authState.lastSyncTime ? (
                          <div className="mb-3 p-3 bg-surface-card border border-border/25 rounded">
                            <div className="flex items-center gap-2 text-text-muted text-sm">
                              <span className="h-3 w-3 rounded-full">
                                {authState.lastSyncStatus === "success" ? (
                                  <span className="bg-success" />
                                ) : authState.lastSyncStatus === "failed" ? (
                                  <span className="bg-destructive" />
                                ) : (
                                  <span className="bg-muted" />
                                )}
                              </span>
                              <span>
                                Last sync: {authState.lastSyncStatus || "Never"} {
                                  authState.lastSyncTime && authState.lastSyncStatus !== null ? (
                                    <span className="ml-1">({authState.lastSyncTime})</span>
                                  ) : null
                                }
                              </span>
                            </div>
                          </div>
                        ) : null}

                        {/* Sync Progress */}
                        {authState.syncing ? (
                          <div className="mb-3 p-3 bg-surface-card border border-border/25 rounded">
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-text-muted text-sm">
                                <span className="h-3 w-3 rounded-full bg-info" />
                                <span>Syncing...</span>
                              </div>
                              {authState.syncProgress && (
                                <div className="text-xs text-text-muted">
                                  <div className="grid grid-cols-2 gap-2">
                                    <div>Discovered: {authState.syncProgress.recordsDiscovered}</div>
                                    <div>Added: {authState.syncProgress.recordsAdded}</div>
                                    <div>Skipped: {authState.syncProgress.recordsSkipped}</div>
                                    <div>Failed: {authState.syncProgress.recordsFailed}</div>
                                    <div>Code fetched: {authState.syncProgress.codeFetched}</div>
                                    <div>Code failed: {authState.syncProgress.codeFailed}</div>
                                  </div>
                                  {authState.syncProgress.errorMessage && (
                                    <div className="mt-1 text-destructive text-xs">{authState.syncProgress.errorMessage}</div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        ) : null}

                        {/* Credential Form */}
                        {consentGiven && !authState.credentialsStored && (
                          <form className="space-y-3" onSubmit={(e) => {
                            e.preventDefault();
                            validateAndSaveCredentials();
                          }}>
                            <div className="space-y-2">
                              <label className="flex flex-col gap-1 text-text-sm font-medium">
                                LEETCODE_SESSION
                                <input
                                  type="password"
                                  value={session}
                                  onChange={(e) => setSession(e.target.value)}
                                  placeholder="Enter your LEETCODE_SESSION cookie"
                                  className="input input-sm w-full"
                                />
                              </label>

                              <label className="flex flex-col gap-1 text-text-sm font-medium">
                                csrftoken
                                <input
                                  type="password"
                                  value={csrfToken}
                                  onChange={(e) => setCsrfToken(e.target.value)}
                                  placeholder="Enter your csrftoken cookie"
                                  className="input input-sm w-full"
                                />
                              </label>

                              <div className="flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={consentGiven}
                                  onChange={(e) => setConsentGiven(e.target.checked)}
                                  className="h-4 w-4"
                                />
                                <span className="text-text-sm">
                                  I understand that storing these credentials allows CodeMemory to access my full LeetCode submission history.
                                </span>
                              </div>
                            </div>

                            <Button
                              type="submit"
                              variant="primary"
                              size="sm"
                              disabled={authState.validating || !(session.trim() && csrfToken.trim())}
                              className="w-full"
                            >
                              {authState.validating ? "Validating..." : "Validate & Save"}
                            </Button>
                          </form>
                        )}

                        {/* Action Buttons */}
                        <div className="flex flex-col sm:flex-row sm:gap-2 mt-4">
                          {authState.credentialsStored && (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={authState.syncing}
                              onClick={syncFullHistory}
                              className="w-full sm:w-auto"
                            >
                              {authState.syncing ? "Syncing..." : "Sync Full History"}
                            </Button>
                          )}

                          {authState.credentialsStored && (
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={revokeCredentials}
                              className="w-full sm:w-auto ml-2 sm:ml-0"
                            >
                              Revoke Credentials
                            </Button>
                          )}
                        </div>
                      </div>
                    </>
                  )}

                  {platform.id === "leetcode" && !state.connected ? (
                    <Button
                      variant="subtle"
                      size="sm"
                      disabled={state.connecting}
                      onClick={() => connect(platform.id, platform.handle)}
                    >
                      {state.connecting ? "Connecting…" : "Connect"}
                    </Button>
                  ) : (
                    <ConfirmAction
                      triggerLabel="Disconnect"
                      triggerVariant="outline"
                      description={
                        <span>
                          Disconnect <span className="text-text-primary">{platform.name}</span>? Your
                          imported history stays in the local index; new submissions stop arriving.
                        </span>
                      }
                      confirmLabel="Disconnect"
                      onConfirm={() => disconnect(platform.id)}
                    />
                  )}
                </>
              ) : (
                <Button
                  variant="subtle"
                  size="sm"
                  disabled={state.connecting}
                  onClick={() => connect(platform.id, platform.handle)}
                >
                  {state.connecting ? "Connecting…" : "Connect"}
                </Button>
              )}
            </div>
          </div>
        );
      })}
    </SettingsGroup>
  );
}

function ConnectionBadge({ connected, connecting }: { connected: boolean; connecting: boolean }) {
  if (connecting) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-sm border border-info/25 bg-info-soft px-1.5 py-0.5 font-technical-sm font-medium text-info">
        <span
          className="h-1.5 w-1.5 rounded-full bg-info"
          aria-hidden="true"
          style={{ animation: "cm-pulse 1.2s ease-in-out infinite" }}
        />
        Connecting
      </span>
    );
  }

  if (connected) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-sm border border-success/25 bg-success-soft px-1.5 py-0.5 font-technical-sm font-medium text-success">
        <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />
        Connected
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border border-border bg-surface-card px-1.5 py-0.5",
        "font-technical-sm font-medium text-text-muted",
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-text-disabled" aria-hidden="true" />
      Not connected
    </span>
  );
}
