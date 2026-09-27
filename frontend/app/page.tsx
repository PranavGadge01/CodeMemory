"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { getLeetCodeStatus } from "@/lib/api/leetcode";
import { MemoryMark } from "@/components/system/logo";
import { Button } from "@/components/ui/button";
import { hasStartedOnboarding } from "@/lib/onboarding";

export default function HomePage() {
  const router = useRouter();
  const [state, setState] = React.useState<"loading" | "intro" | "error">("loading");
  const [error, setError] = React.useState("");
  const [retry, setRetry] = React.useState(0);
  React.useEffect(() => {
    let active = true;
    getLeetCodeStatus().then((status) => {
      if (!active) return;
      if (status.connected) router.replace("/dashboard");
      else if (hasStartedOnboarding()) router.replace("/connect");
      else setState("intro");
    }).catch((failure) => {
      if (!active) return;
      setError(failure instanceof Error ? failure.message : "Could not load your account.");
      setState("error");
    });
    return () => { active = false; };
  }, [router, retry]);
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <div className="w-full max-w-[520px]">
        <div className="mb-12 flex items-center gap-3 text-body-md font-semibold">
          <MemoryMark size={28} className="text-accent" /> CodeMemory
        </div>
        {state === "loading" ? <p role="status" className="text-body-md text-text-muted">Opening your workspace…</p> : state === "error" ? (
          <div role="alert">
            <h1 className="text-heading-xl">Could not open your workspace</h1>
            <p className="my-5 text-body-md text-text-muted">{error}</p>
            <Button onClick={() => { setState("loading"); setRetry((value) => value + 1); }}>Try again</Button>
          </div>
        ) : (
          <>
            <h1 className="text-display-lg text-text-primary">Your coding history,<br />remembered.</h1>
            <p className="mt-6 max-w-[45ch] text-body-lg text-text-muted">CodeMemory connects to your LeetCode profile and turns your submission history into a searchable coding memory.</p>
            <Button variant="primary" size="lg" className="mt-8" asChild>
              <Link href="/connect">Get Started <ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>
            </Button>
            <p className="mt-6 text-caption text-text-faint">Stored on your computer. Start with just your LeetCode username.</p>
          </>
        )}
      </div>
    </main>
  );
}
