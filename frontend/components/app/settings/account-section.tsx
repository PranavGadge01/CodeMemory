"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Code2, Swords, Terminal } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  disconnectLeetCode,
  getLeetCodeStatus,
  revokeLeetCodeCredentials,
  storeLeetCodeCredentials,
  syncAuthenticatedLeetCode,
  validateLeetCodeCredentials,
} from "@/lib/api/leetcode";
import type { LeetCodeAuthSyncResultDTO } from "@/lib/api/types";
import { SettingsGroup } from "./settings-group";
import { ConfirmAction } from "./confirm-action";
import { Button } from "@/components/ui/button";

const PREVIEW_PLATFORMS: { name: string; icon: LucideIcon; description: string }[] = [
  {
    name: "Codeforces",
    icon: Swords,
    description: "Rating history and contest submissions are not connected yet.",
  },
  {
    name: "HackerRank",
    icon: Terminal,
    description: "Skill assessments and practice submissions are not connected yet.",
  },
];

interface AuthState {
  checked: boolean;
  credentialsStored: boolean;
  validating: boolean;
  syncing: boolean;
  message: string | null;
  error: string | null;
  lastSyncStatus: string | null;
  lastSyncTime: string | null;
  syncProgress: LeetCodeAuthSyncResultDTO | null;
}

const EMPTY_AUTH_STATE: AuthState = {
  checked: false,
  credentialsStored: false,
  validating: false,
  syncing: false,
  message: null,
  error: null,
  lastSyncStatus: null,
  lastSyncTime: null,
  syncProgress: null,
};

export function AccountSection() {
  const router = useRouter();
  const [connected, setConnected] = React.useState(false);
  const [username, setUsername] = React.useState<string | null>(null);
  const [auth, setAuth] = React.useState<AuthState>(EMPTY_AUTH_STATE);
  const [formOpen, setFormOpen] = React.useState(false);
  const [consentGiven, setConsentGiven] = React.useState(false);
  const [session, setSession] = React.useState("");
  const [csrfToken, setCsrfToken] = React.useState("");
  const syncInFlight = React.useRef(false);

  React.useEffect(() => {
    let active = true;

    void Promise.allSettled([getLeetCodeStatus(), validateLeetCodeCredentials()]).then(
      ([accountResult, authResult]) => {
        if (!active) return;

        if (accountResult.status === "fulfilled") {
          setConnected(accountResult.value.connected);
          setUsername(accountResult.value.username);
        }

        if (authResult.status === "fulfilled") {
          setConnected(authResult.value.connected);
          setUsername(authResult.value.username);
          setAuth((prev) => ({
            ...prev,
            checked: true,
            credentialsStored: authResult.value.credentialsStored,
            message: authResult.value.validationMessage,
            lastSyncStatus: authResult.value.syncState,
            lastSyncTime: authResult.value.lastSuccessfulSync,
          }));
        } else {
          setAuth((prev) => ({
            ...prev,
            checked: true,
            error: "Could not check the stored LeetCode session. Try again when the backend is available.",
          }));
        }
      },
    );

    return () => {
      active = false;
    };
  }, []);

  const disconnect = async () => {
    try {
      await disconnectLeetCode();
      setConnected(false);
      setUsername(null);
    } catch {
      setAuth((prev) => ({ ...prev, error: "Could not disconnect the LeetCode account. Please try again." }));
    }
  };

  const saveCredentials = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuth((prev) => ({ ...prev, validating: true, error: null, message: null }));

    try {
      const result = await storeLeetCodeCredentials(session, csrfToken);
      setSession("");
      setCsrfToken("");
      setConsentGiven(false);
      setFormOpen(false);
      setAuth((prev) => ({
        ...prev,
        validating: false,
        credentialsStored: result.credentialsStored,
        message: result.credentialsStored ? "Credentials stored securely." : result.validationMessage,
      }));
      setConnected(result.connected);
      setUsername(result.username);
    } catch {
      setAuth((prev) => ({
        ...prev,
        validating: false,
        error: "Could not validate and store the credentials. Check that the backend is available and try again.",
      }));
    }
  };

  const syncFullHistory = async () => {
    if (syncInFlight.current || !auth.credentialsStored) return;
    syncInFlight.current = true;
    setAuth((prev) => ({ ...prev, syncing: true, error: null, syncProgress: null }));

    try {
      const result = await syncAuthenticatedLeetCode();
      setAuth((prev) => ({
        ...prev,
        syncing: false,
        lastSyncStatus: result.status,
        lastSyncTime: new Date().toISOString(),
        syncProgress: result,
      }));
    } catch {
      setAuth((prev) => ({
        ...prev,
        syncing: false,
        lastSyncStatus: "failed",
        error: "Authenticated sync failed. Check that your LeetCode account is connected and the stored session is valid, then retry.",
      }));
    } finally {
      syncInFlight.current = false;
    }
  };

  const revokeCredentials = async () => {
    setAuth((prev) => ({ ...prev, error: null }));
    try {
      await revokeLeetCodeCredentials();
      setAuth((prev) => ({
        ...prev,
        credentialsStored: false,
        message: "Stored credentials were revoked.",
        lastSyncStatus: null,
        lastSyncTime: null,
        syncProgress: null,
      }));
      setSession("");
      setCsrfToken("");
      setConsentGiven(false);
      setFormOpen(false);
    } catch {
      setAuth((prev) => ({ ...prev, error: "Could not revoke the stored credentials. Please try again." }));
    }
  };

  const retryValidation = async () => {
    setAuth((prev) => ({ ...prev, error: null, checked: false }));
    try {
      const result = await validateLeetCodeCredentials();
      setConnected(result.connected);
      setUsername(result.username);
      setAuth((prev) => ({
        ...prev,
        checked: true,
        credentialsStored: result.credentialsStored,
        message: result.validationMessage,
        lastSyncStatus: result.syncState,
        lastSyncTime: result.lastSuccessfulSync,
      }));
    } catch {
      setAuth((prev) => ({
        ...prev,
        checked: true,
        error: "Could not check the stored LeetCode session. Try again when the backend is available.",
      }));
    }
  };

  return (
    <SettingsGroup
      id="account"
      eyebrow="03"
      title="Account"
      description="Connect a public LeetCode profile, then optionally store credentials securely for full submission history."
    >
      <div className="px-5 py-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <PlatformIcon icon={Code2} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-body-sm font-medium text-text-primary">LeetCode</span>
                <ConnectionBadge connected={connected} connecting={false} />
              </div>
              <p className="mt-1 text-body-sm text-text-muted">
                {connected && username ? `Connected as @${username}.` : "Public profile sync is not connected."}
              </p>
            </div>
          </div>
          {connected ? (
            <ConfirmAction
              triggerLabel="Disconnect"
              triggerVariant="outline"
              description={<span>Disconnect LeetCode? Previously imported history stays in the local index.</span>}
              confirmLabel="Disconnect"
              onConfirm={disconnect}
            />
          ) : (
            <Button variant="subtle" size="sm" onClick={() => router.push("/connect")}>
              Connect LeetCode
            </Button>
          )}
        </div>

        <section aria-labelledby="authenticated-sync-heading" className="mt-5 rounded-lg border border-border-soft bg-surface-elevated p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 id="authenticated-sync-heading" className="text-body-sm font-semibold text-text-primary">
                Full history sync
              </h3>
              <p className="mt-1 text-caption text-text-muted">
                Stores credentials in the backend vault and never displays them after saving.
              </p>
            </div>
            {!auth.credentialsStored && auth.checked ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (formOpen) {
                    setSession("");
                    setCsrfToken("");
                    setConsentGiven(false);
                  }
                  setFormOpen(!formOpen);
                  setAuth((prev) => ({ ...prev, error: null }));
                }}
              >
                {formOpen ? "Close form" : "Add credentials"}
              </Button>
            ) : null}
          </div>

          <div className="mt-3 text-caption text-text-muted" role="status" aria-live="polite">
            {auth.checked
              ? auth.credentialsStored
                ? "Authenticated credentials are stored."
                : "No authenticated credentials are stored."
              : "Checking stored credentials…"}
          </div>

          {auth.message ? <p className="mt-2 text-caption text-text-secondary" role="status">{auth.message}</p> : null}
          {auth.error ? (
            <div className="mt-3 flex flex-wrap items-center gap-3" role="alert">
              <p className="text-body-sm text-error">{auth.error}</p>
              {!auth.credentialsStored ? (
                <Button variant="ghost" size="sm" onClick={retryValidation}>Retry check</Button>
              ) : null}
            </div>
          ) : null}

          {auth.lastSyncStatus || auth.lastSyncTime ? (
            <p className="mt-3 text-caption text-text-muted">
              Last sync: {auth.lastSyncStatus ?? "unknown"}
              {auth.lastSyncTime ? ` · ${new Date(auth.lastSyncTime).toLocaleString()}` : ""}
            </p>
          ) : null}

          {auth.syncProgress ? <SyncSummary result={auth.syncProgress} /> : null}

          {formOpen && !auth.credentialsStored ? (
            <form className="mt-4 space-y-3 border-t border-border-soft pt-4" onSubmit={saveCredentials}>
              <label className="block text-caption font-medium text-text-secondary" htmlFor="leetcode-session">
                LEETCODE_SESSION
                <input
                  id="leetcode-session"
                  type="password"
                  autoComplete="off"
                  value={session}
                  onChange={(event) => setSession(event.target.value)}
                  className="input input-sm mt-1 w-full"
                  required
                  suppressHydrationWarning
                />
              </label>
              <label className="block text-caption font-medium text-text-secondary" htmlFor="leetcode-csrftoken">
                csrftoken
                <input
                  id="leetcode-csrftoken"
                  type="password"
                  autoComplete="off"
                  value={csrfToken}
                  onChange={(event) => setCsrfToken(event.target.value)}
                  className="input input-sm mt-1 w-full"
                  required
                  suppressHydrationWarning
                />
              </label>
              <label className="flex items-start gap-2 text-caption text-text-secondary">
                <input
                  type="checkbox"
                  checked={consentGiven}
                  onChange={(event) => setConsentGiven(event.target.checked)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--color-accent)]"
                  suppressHydrationWarning
                />
                <span>I understand these credentials let CodeMemory access my full LeetCode submission history.</span>
              </label>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={auth.validating || !consentGiven || !session.trim() || !csrfToken.trim()}
              >
                {auth.validating ? "Validating and saving…" : "Validate and save"}
              </Button>
            </form>
          ) : null}

          {auth.credentialsStored ? (
            <div className="mt-4 flex flex-col gap-2 border-t border-border-soft pt-4 sm:flex-row">
              <Button variant="outline" size="sm" disabled={auth.syncing || !connected} onClick={syncFullHistory}>
                {auth.syncing ? "Syncing…" : "Sync full history"}
              </Button>
              {!connected ? <span className="self-center text-caption text-text-muted">Connect the public profile before syncing.</span> : null}
              <ConfirmAction
                triggerLabel="Revoke credentials"
                triggerVariant="danger"
                description={<span>Remove the stored LeetCode session from the backend credential vault?</span>}
                confirmLabel="Revoke credentials"
                onConfirm={revokeCredentials}
              />
            </div>
          ) : null}
        </section>
      </div>

      {PREVIEW_PLATFORMS.map((platform) => (
        <div key={platform.name} className="flex items-start justify-between gap-4 border-t border-border-soft px-5 py-4">
          <div className="flex min-w-0 items-start gap-3">
            <PlatformIcon icon={platform.icon} />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-body-sm font-medium text-text-primary">{platform.name}</span>
                <ConnectionBadge connected={false} connecting={false} />
              </div>
              <p className="mt-1 text-body-sm text-text-muted">{platform.description}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" disabled>Coming soon</Button>
        </div>
      ))}
    </SettingsGroup>
  );
}

function PlatformIcon({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-surface-card text-text-muted">
      <Icon className="h-[18px] w-[18px]" aria-hidden="true" strokeWidth={1.75} />
    </div>
  );
}

function SyncSummary({ result }: { result: LeetCodeAuthSyncResultDTO }) {
  return (
    <div className="mt-3 rounded-md border border-border-soft bg-surface-card p-3" role="status" aria-live="polite">
      <div className="text-body-sm font-medium text-text-primary">Sync {result.status}</div>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-caption text-text-muted sm:grid-cols-3">
        <div><dt className="inline">Discovered: </dt><dd className="inline">{result.recordsDiscovered}</dd></div>
        <div><dt className="inline">Added: </dt><dd className="inline">{result.recordsAdded}</dd></div>
        <div><dt className="inline">Skipped: </dt><dd className="inline">{result.recordsSkipped}</dd></div>
        <div><dt className="inline">Failed: </dt><dd className="inline">{result.recordsFailed}</dd></div>
        <div><dt className="inline">Code fetched: </dt><dd className="inline">{result.codeFetched}</dd></div>
        <div><dt className="inline">Code failed: </dt><dd className="inline">{result.codeFailed}</dd></div>
      </dl>
    </div>
  );
}

function ConnectionBadge({ connected, connecting }: { connected: boolean; connecting: boolean }) {
  const label = connecting ? "Connecting" : connected ? "Connected" : "Not connected";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5 font-technical-sm font-medium",
        connected ? "border-success/25 bg-success-soft text-success" : "border-border bg-surface-card text-text-muted",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", connected ? "bg-success" : "bg-text-disabled")} aria-hidden="true" />
      {label}
    </span>
  );
}
