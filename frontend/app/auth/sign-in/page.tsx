"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowRight, Eye, EyeOff, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { MemoryMark } from "@/components/system/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Toggle } from "@/components/app/settings/settings";
import { Separator } from "@/components/ui/primitives";

type FormState = "idle" | "submitting" | "demo";

export default function SignInPage() {
  const [email, setEmail] = React.useState("jay@codememory.dev");
  const [password, setPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [remember, setRemember] = React.useState(true);
  const [state, setState] = React.useState<FormState>("idle");

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setState("submitting");
    window.setTimeout(() => setState("demo"), 900);
  };

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      {/* Brand panel */}
      <section
        aria-label="CodeMemory"
        className="relative hidden flex-col justify-between overflow-hidden border-r border-border-soft bg-surface px-10 py-12 lg:flex"
      >
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-50" aria-hidden="true" />
        <div className="relative flex items-center gap-3">
          <MemoryMark size={26} className="text-accent" />
          <span className="text-[15px] font-semibold tracking-[-0.01em] text-text-primary">
            Code<span className="text-text-muted">Memory</span>
          </span>
        </div>

        <div className="relative max-w-[34ch]">
          <p className="text-display-lg text-text-primary">Your coding history, remembered.</p>
          <p className="mt-5 text-body-md text-text-muted">
            Every attempt, every mistake, every optimisation — indexed, connected, and ready when
            you need to remember how you actually solved it.
          </p>
          <div className="mt-8 flex items-center gap-3 border-t border-border-soft pt-6">
            <MemoryMark size={18} className="text-text-faint" withGlow />
            <span className="font-technical-sm text-text-faint">
              local-first · no account required
            </span>
          </div>
        </div>

        <div className="relative" />
      </section>

      {/* Form */}
      <section className="flex items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-[380px]">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <MemoryMark size={24} className="text-accent" />
            <span className="text-[15px] font-semibold tracking-[-0.01em] text-text-primary">
              Code<span className="text-text-muted">Memory</span>
            </span>
          </div>

          {state === "demo" ? (
            <div className="rounded-lg border border-border bg-surface p-6">
              <div className="flex h-9 w-9 items-center justify-center rounded-md border border-success/25 bg-success-soft text-success">
                <Check className="h-4 w-4" aria-hidden="true" />
              </div>
              <h1 className="mt-4 text-heading-md text-text-primary">Demo mode</h1>
              <p className="mt-2 text-body-sm text-text-muted">
                Authentication is not connected in this phase, so nothing was verified. The UI you
                are looking at is the complete sign-in shell.
              </p>
              <Separator className="my-5" />
              <div className="flex flex-col gap-2">
                <Button variant="primary" size="md" asChild>
                  <Link href="/dashboard">
                    Continue to dashboard
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
                <Button variant="ghost" size="md" onClick={() => setState("idle")}>
                  Back to sign in
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="eyebrow">Sign in</div>
              <h1 className="mt-2 text-heading-xl text-text-primary">Welcome back</h1>
              <p className="mt-2 text-body-md text-text-muted">
                Sign in to sync your local index across machines. Your submission history stays
                yours.
              </p>

              <form className="mt-8 flex flex-col gap-4" onSubmit={onSubmit}>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="email" className="text-body-sm font-medium text-text-primary">
                    Email
                  </label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    autoComplete="email"
                    placeholder="you@example.com"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label htmlFor="password" className="text-body-sm font-medium text-text-primary">
                    Password
                  </label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      autoComplete="current-password"
                      placeholder="••••••••"
                      className="pr-9"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      aria-pressed={showPassword}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="press absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded text-text-faint hover:bg-surface-hover hover:text-text-primary"
                    >
                      {showPassword ? (
                        <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
                      ) : (
                        <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-2 text-body-sm text-text-secondary">
                    <Toggle checked={remember} onChange={setRemember} label="Remember this device" />
                    Remember this device
                  </span>
                  <button
                    type="button"
                    className="press font-technical-sm text-text-muted hover:text-text-secondary"
                  >
                    Forgot?
                  </button>
                </div>

                <Button type="submit" variant="primary" size="lg" disabled={state === "submitting"}>
                  {state === "submitting" ? "Signing in…" : "Sign in"}
                  {state === "idle" ? <ArrowRight className="h-4 w-4" aria-hidden="true" /> : null}
                </Button>

                <div className="flex items-center gap-3 py-1">
                  <Separator className="flex-1" />
                  <span className="eyebrow">Or</span>
                  <Separator className="flex-1" />
                </div>

                <Button type="button" variant="outline" size="lg">
                  <MemoryMark size={16} className="text-accent" />
                  Continue with LeetCode
                </Button>
              </form>

              <p className="mt-8 text-caption text-text-faint">
                Demo build — no credentials are sent anywhere.{" "}
                <Link href="/dashboard" className={cn("font-technical-sm text-accent hover:text-accent-hover")}>
                  Skip to demo
                </Link>
              </p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
