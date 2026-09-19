"use client";

import * as React from "react";
import { Code2, Swords, Terminal } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { SettingsGroup } from "./settings-group";
import { ConfirmAction } from "./confirm-action";
import { Button } from "@/components/ui/button";

type PlatformId = "leetcode" | "codeforces" | "hackerrank";

interface PlatformState {
  connected: boolean;
  connecting: boolean;
  handle: string;
}

const PLATFORMS: {
  id: PlatformId;
  name: string;
  icon: LucideIcon;
  /** Handle shown once a mock connection exists. */
  handle: string;
  description: string;
}[] = [
  {
    id: "leetcode",
    name: "LeetCode",
    icon: Code2,
    handle: "codememory",
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
 * Connected platforms. Nothing leaves the page: "connect" flips a local flag
 * after a brief delay so the state change reads as deliberate rather than
 * instant. LeetCode starts connected to match the memory index.
 */
export function AccountSection() {
  const [platforms, setPlatforms] = React.useState<Record<PlatformId, PlatformState>>({
    leetcode: { connected: true, connecting: false, handle: "codememory" },
    codeforces: { connected: false, connecting: false, handle: "codememory" },
    hackerrank: { connected: false, connecting: false, handle: "codememory" },
  });

  const connect = (platform: PlatformId, handle: string) => {
    setPlatforms((prev) => ({ ...prev, [platform]: { ...prev[platform], connecting: true } }));

    window.setTimeout(() => {
      setPlatforms((prev) => ({
        ...prev,
        [platform]: { connected: true, connecting: false, handle },
      }));
    }, 900);
  };

  const disconnect = (platform: PlatformId) => {
    setPlatforms((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], connected: false, connecting: false },
    }));
  };

  return (
    <SettingsGroup
      id="settings-account"
      eyebrow="03"
      title="Account"
      description="Where your submission history comes from. Connections are local to this preview."
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
