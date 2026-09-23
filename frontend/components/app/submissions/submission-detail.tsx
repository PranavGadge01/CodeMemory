"use client";

import * as React from "react";
import Link from "next/link";
import { Copy, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badges";
import { Surface } from "@/components/ui/surface";
import {
  formatDateTime,
  formatMemory,
  formatRelative,
  formatRuntime,
} from "@/lib/format";
import type { Problem, Submission } from "@/lib/types";

export function SubmissionDetail({
  submission,
  problem,
}: {
  submission: Submission;
  problem: Problem | null;
}) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = React.useCallback(() => {
    if (submission.code) {
      navigator.clipboard.writeText(submission.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [submission]);

  return (
    <div className="flex flex-col gap-6">
      {/* Identity & status */}
      <Surface className="flex flex-col gap-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="eyebrow mb-1.5">Submission</div>
            <h2 className="text-heading-md truncate text-text-primary font-mono">
              {submission.id}
            </h2>
          </div>
          <StatusBadge status={submission.status} />
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
          <Fact label="Problem" value={problem?.title ?? "Unknown problem"} />
          <Fact label="Language" value={submission.language} />
          <Fact
            label="Runtime"
            value={formatRuntime(submission.runtimeMs)}
            hint={formatRuntime(submission.runtimeMs) === "—" ? "Not available" : undefined}
          />
          <Fact
            label="Memory"
            value={formatMemory(submission.memoryMb)}
            hint={formatMemory(submission.memoryMb) === "—" ? "Not available" : undefined}
          />
          <Fact
            label="Submitted"
            value={formatRelative(submission.submittedAt)}
            title={formatDateTime(submission.submittedAt)}
          />
          <Fact label="Source account" value={submission.sourceAccount ?? "—"} />
          {submission.errorMessage ? (
            <Fact label="Error" value={submission.errorMessage} />
          ) : null}
        </dl>

        {problem && problem.slug ? (
          <Button variant="outline" size="sm" asChild>
            <Link href={`/problems?slug=${problem.slug}`}>
              Open problem
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </Button>
        ) : null}
      </Surface>

      {/* Code */}
      <Surface className="flex flex-col gap-4 p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="eyebrow mb-1.5">Code</div>
            {problem && problem.url ? (
              <Button variant="ghost" size="sm" asChild>
                <a href={problem.url} target="_blank" rel="noopener noreferrer">
                  {`Open on ${problem.platform}`}
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              </Button>
            ) : null}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            disabled={!submission.code}
            aria-label="Copy code"
          >
            <Copy className="h-3.5 w-3.5" aria-hidden="true" />
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>

        {submission.code ? (
          <CodeBlock code={submission.code} />
        ) : (
          <div className="py-8 text-center text-body-sm text-text-muted">
            Source code not available
          </div>
        )}
      </Surface>
    </div>
  );
}

function Fact({
  label,
  value,
  title,
  hint,
}: {
  label: string;
  value: string;
  title?: string;
  hint?: string;
}) {
  return (
    <div className="min-w-0">
      <dt className="eyebrow">{label}</dt>
      <dd
        className="mt-1 truncate font-technical text-text-primary tabular-nums"
        title={title ?? value}
      >
        {value}
      </dd>
      {hint ? <dd className="mt-1 font-technical-xs text-text-faint">{hint}</dd> : null}
    </div>
  );
}

function CodeBlock({ code }: { code: string }) {
  const lines = code.split("\n");

  return (
    <div className="overflow-x-auto bg-code-surface">
      <pre className="min-w-max py-4 font-mono text-[12.5px] leading-[1.65]">
        <code>
          {lines.map((line, index) => (
            <span key={index} className="flex">
              <span
                className="w-12 shrink-0 select-none pr-4 text-right text-code-line-number"
                aria-hidden="true"
              >
                {index + 1}
              </span>
              <span className="whitespace-pre text-text-secondary">{line || " "}</span>
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
