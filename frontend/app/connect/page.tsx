"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, ArrowRight, Check, RotateCw } from "lucide-react";
import { MemoryMark } from "@/components/system/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/primitives";
import { Surface } from "@/components/ui/surface";
import { ApiError, isNetworkError } from "@/lib/api";
import {
  connectLeetCode,
  getLeetCodeStatus,
  syncLeetCode,
} from "@/lib/api/leetcode";
import type { LeetCodeSyncResultDTO } from "@/lib/api/types";

export default function ConnectPage() {
  const router = useRouter();

  // "checking" reads GET /leetcode/status first, so an account that is already
  // connected never asks for a username again. Every later phase is driven by
  // real API responses — there is no local "connected" flag.
  const [phase, setPhase] = React.useState<
    "checking" | "idle" | "connecting" | "syncing" | "error" | "done"
  >("checking");
  const [username, setUsername] = React.useState("");
  const [error, setError] = React.useState<ApiError | null>(null);
  const [result, setResult] = React.useState<LeetCodeSyncResultDTO | null>(null);
  const [connectedAs, setConnectedAs] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    getLeetCodeStatus()
      .then((status) => {
        if (cancelled) return;
        if (status.connected) {
          setConnectedAs(status.username);
          setPhase("done");
        } else {
          setPhase("idle");
        }
      })
      .catch(() => {
        // Status is advisory: if it cannot be read the form still works, and
        // the connect call reports the real reason if the API is down.
        if (!cancelled) setPhase("idle");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const trimmed = username.trim();
    if (!trimmed) {
      setError(new ApiError("Enter your LeetCode username to continue.", "BAD_REQUEST", 0));
      setPhase("error");
      return;
    }

    setError(null);
    setPhase("connecting");

    try {
      const status = await connectLeetCode(trimmed);
      setConnectedAs(status.username ?? trimmed);

      // The account is only useful once its history is indexed, so a successful
      // connect rolls straight into a sync. Both calls are the backend's own
      // endpoints; nothing is inferred client-side.
      setPhase("syncing");
      const syncResult = await syncLeetCode();
      setResult(syncResult);

      if (syncResult.status.toLowerCase() === "failed") {
        setError(
          new ApiError(
            syncResult.errorMessage ?? "Sync did not complete. Your account is connected.",
            "SYNC_FAILED",
            0,
          ),
        );
        setPhase("error");
        return;
      }

      setPhase("done");

      // Let the success state be read before leaving the page.
      window.setTimeout(() => router.push("/dashboard"), 1400);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught
          : new ApiError("Connection failed. Please try again.", "ERROR", 0),
      );
      setPhase("error");
    }
  };

  const busy = phase === "connecting" || phase === "syncing";

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border-soft">
        <div className="mx-auto flex h-14 w-full max-w-[1200px] items-center px-5 md:px-8">
          <Link href="/" className="press inline-flex items-center gap-2 text-text-muted hover:text-text-secondary">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            <span className="font-technical-sm">Back to home</span>
          </Link>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-[440px]">
          <div className="mb-8 flex items-center gap-3">
            <MemoryMark size={24} className="text-accent" />
            <span className="text-[15px] font-semibold tracking-[-0.01em] text-text-primary">
              Code<span className="text-text-muted">Memory</span>
            </span>
          </div>

          <Surface className="overflow-hidden">
            <div className="border-b border-border-soft px-6 py-5">
              <div className="eyebrow">Connect</div>
              <h1 className="mt-2 text-heading-xl text-text-primary">Connect LeetCode</h1>
              <p className="mt-2 text-body-md text-text-muted">
                CodeMemory reads your public submission history. Enter the username your
                submissions are published under — nothing else.
              </p>
            </div>

            <div className="px-6 py-6">
              {phase === "done" ? (
                <SuccessPanel connectedAs={connectedAs} result={result} />
              ) : phase === "syncing" ? (
                <SyncingPanel connectedAs={connectedAs} />
              ) : (
                <form className="flex flex-col gap-4" onSubmit={onSubmit}>
                  <div className="flex flex-col gap-1.5">
                    <label
                      htmlFor="leetcode-username"
                      className="text-body-sm font-medium text-text-primary"
                    >
                      LeetCode username
                    </label>
                    <Input
                      id="leetcode-username"
                      name="username"
                      type="text"
                      autoComplete="username"
                      autoCapitalize="off"
                      autoCorrect="off"
                      spellCheck={false}
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      placeholder="your-leetcode-username"
                      disabled={busy}
                      aria-describedby={error ? "connect-error" : undefined}
                      aria-invalid={error !== null}
                    />
                    <span className="font-technical-sm text-text-faint">
                      Public profile only — no password, cookie or session token is ever asked for.
                    </span>
                  </div>

                  {error ? <ErrorRow error={error} id="connect-error" /> : null}

                  <Button type="submit" variant="primary" size="lg" disabled={busy}>
                    {phase === "connecting" ? (
                      <>
                        <RotateCw className="h-4 w-4 animate-spin" aria-hidden="true" />
                        Connecting…
                      </>
                    ) : (
                      <>
                        Connect
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </>
                    )}
                  </Button>
                </form>
              )}

              {phase === "done" ? (
                <div className="mt-5 flex flex-col gap-2">
                  <Button variant="primary" size="lg" onClick={() => router.push("/dashboard")}>
                    Open dashboard
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="md"
                    onClick={() => {
                      setResult(null);
                      setError(null);
                      setPhase("idle");
                    }}
                  >
                    Use a different account
                  </Button>
                </div>
              ) : null}
            </div>
          </Surface>

          <Separator className="my-6" />

          <p className="text-caption text-text-faint">
            Your submissions stay local. CodeMemory only stores the public profile handle and the
            problems you have already solved.{" "}
            <Link href="/" className="font-technical-sm text-accent hover:text-accent-hover">
              Learn how it works
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}

function ErrorRow({ error, id }: { error: ApiError; id: string }) {
  const message = isNetworkError(error)
    ? "The CodeMemory API could not be reached. Check that the local server is running and try again."
    : error.message;

  return (
    <div
      id={id}
      role="alert"
      className="flex items-start gap-2.5 rounded-md border border-error/25 bg-error-soft px-3 py-2.5"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-error" aria-hidden="true" />
      <div className="min-w-0">
        <div className="text-body-sm font-medium text-error">Connection failed</div>
        <div className="mt-0.5 text-body-sm text-text-muted">{message}</div>
      </div>
    </div>
  );
}

function SyncingPanel({ connectedAs }: { connectedAs: string | null }) {
  return (
    <div className="flex flex-col items-start gap-4">
      <div
        className="flex h-9 w-9 items-center justify-center rounded-md border border-info/25 bg-info-soft text-info"
        aria-hidden="true"
      >
        <RotateCw className="h-4 w-4 animate-spin" />
      </div>
      <div>
        <div className="text-body-md font-medium text-text-primary">
          Importing submissions
          {connectedAs ? ` from @${connectedAs}` : ""}…
        </div>
        <p className="mt-1.5 text-body-sm text-text-muted">
          Indexing your recent solving history. This can take a moment on a first sync — the page
          will move on as soon as the index is ready.
        </p>
      </div>
      <div className="w-full overflow-hidden rounded-full bg-surface-card" aria-hidden="true">
        <span className="block h-1.5 w-2/5 animate-pulse rounded-full bg-accent" />
      </div>
    </div>
  );
}

function SuccessPanel({
  connectedAs,
  result,
}: {
  connectedAs: string | null;
  result: LeetCodeSyncResultDTO | null;
}) {
  return (
    <div className="flex flex-col items-start gap-4">
      <div
        className="flex h-9 w-9 items-center justify-center rounded-md border border-success/25 bg-success-soft text-success"
        aria-hidden="true"
      >
        <Check className="h-4 w-4" />
      </div>
      <div>
        <div className="text-body-md font-medium text-text-primary">
          {connectedAs ? `@${connectedAs} is connected` : "LeetCode is connected"}
        </div>
        <p className="mt-1.5 text-body-sm text-text-muted">
          {result
            ? `${result.recordsImported} submission${result.recordsImported === 1 ? "" : "s"} imported` +
              (result.recordsSkipped ? ` · ${result.recordsSkipped} already known` : "") +
              (result.recordsFailed ? ` · ${result.recordsFailed} failed` : "") +
              ". Taking you to your dashboard."
            : "Taking you to your dashboard."}
        </p>
      </div>
    </div>
  );
}
