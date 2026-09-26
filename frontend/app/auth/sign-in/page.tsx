import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { MemoryMark } from "@/components/system/logo";
import { Button } from "@/components/ui/button";

export const metadata = { title: "Sign in" };

export default function SignInPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-5 py-12">
      <section className="w-full max-w-lg rounded-lg border border-border bg-surface-card p-6 sm:p-8" aria-labelledby="sign-in-title">
        <Link href="/" className="inline-flex items-center gap-3" aria-label="CodeMemory home">
          <MemoryMark size={26} className="text-accent" />
          <span className="text-[15px] font-semibold tracking-[-0.01em] text-text-primary">
            Code<span className="text-text-muted">Memory</span>
          </span>
        </Link>

        <div className="eyebrow mt-8">Local-first workspace</div>
        <h1 id="sign-in-title" className="mt-2 text-heading-xl text-text-primary">
          No account needed
        </h1>
        <p className="mt-3 text-body-md text-text-muted">
          CodeMemory runs against your local backend, so this version has no email or password sign-in. Connect a LeetCode profile from the workspace to import submission history.
        </p>

        <div className="mt-7 flex flex-col gap-3 sm:flex-row">
          <Button variant="primary" size="md" asChild>
            <Link href="/dashboard">
              Open workspace
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </Button>
          <Button variant="outline" size="md" asChild>
            <Link href="/connect">Connect LeetCode</Link>
          </Button>
        </div>
      </section>
    </main>
  );
}
