"use client";

import * as React from "react";
import { getSubmissionLearningAnalysis, ApiError } from "@/lib/api";
import type { SubmissionLearningAnalysisDTO } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import {
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  Sparkles,
  Info,
} from "lucide-react";

function Collapsible({
  title,
  children,
  defaultOpen = false,
}: {
  title: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div className="rounded-lg border border-border-soft bg-surface-card overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left"
      >
        <span className="text-caption font-semibold text-text-primary">{title}</span>
        {open ? <ChevronUp className="h-3.5 w-3.5 text-text-faint" /> : <ChevronDown className="h-3.5 w-3.5 text-text-faint" />}
      </button>
      {open && <div className="px-3 pb-3 space-y-2">{children}</div>}
    </div>
  );
}

export function SubmissionLearningCard({
  submissionId,
  className,
}: {
  submissionId: string;
  className?: string;
}) {
  const [data, setData] = React.useState<SubmissionLearningAnalysisDTO | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getSubmissionLearningAnalysis(submissionId)
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load submission learning analysis.");
        setLoading(false);
      });
  }, [submissionId]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  const cmp = data?.previous_attempt_comparison;

  return (
    <div className={`rounded-xl border border-border-soft bg-surface p-5 flex flex-col gap-4 ${className ?? ""}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent" />
          <div>
            <div className="eyebrow mb-0.5">Submission Learning</div>
            <h3 className="text-heading-xs text-text-primary font-semibold">What to learn from this attempt</h3>
          </div>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {loading ? (
        <div className="py-6 text-center space-y-2">
          <RefreshCw className="h-5 w-5 animate-spin mx-auto text-accent" />
          <p className="text-body-sm text-text-muted">Analysing this submission…</p>
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : data ? (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="neutral" className="text-caption">{data.status}</Badge>
            <Badge variant="neutral" className="text-caption">
              {data.current_time_complexity} time
            </Badge>
            <Badge variant="neutral" className="text-caption">
              {data.current_space_complexity} space
            </Badge>
            {data.complexity_source === "code_estimate" && (
              <span className="text-caption text-text-faint">estimated from code structure</span>
            )}
          </div>

          <p className="text-body-sm text-text-secondary leading-relaxed">{data.overview}</p>

          {data.what_went_well.length > 0 && (
            <Collapsible title="What you did well" defaultOpen>
              <ul className="space-y-1.5">
                {data.what_went_well.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-body-sm text-text-secondary">
                    <CheckCircle2 className="h-3.5 w-3.5 mt-0.5 text-success shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </Collapsible>
          )}

          {data.improvements.length > 0 && (
            <Collapsible title="What could be better" defaultOpen>
              <div className="space-y-2">
                {data.improvements.map((imp, i) => (
                  <div key={i} className="rounded-lg bg-surface-elevated border border-border-soft p-2.5 space-y-1">
                    <p className="text-body-sm font-medium text-text-primary">{imp.title}</p>
                    <p className="text-caption text-text-secondary"><span className="font-medium text-text-primary">What: </span>{imp.what}</p>
                    <p className="text-caption text-text-secondary"><span className="font-medium text-text-primary">Why: </span>{imp.why}</p>
                    <p className="text-caption text-accent"><span className="font-medium">How: </span>{imp.how}</p>
                  </div>
                ))}
              </div>
            </Collapsible>
          )}

          <Collapsible title="Complexity, tradeoffs & edge cases">
            <p className="text-caption text-text-secondary">
              <span className="font-medium text-text-primary">Current: </span>
              {data.current_time_complexity} time, {data.current_space_complexity} space
            </p>
            {data.alternative_approach && (
              <p className="text-caption text-text-secondary">
                <span className="font-medium text-text-primary">Alternative: </span>
                {data.alternative_approach}
                {data.alternative_time_complexity ? ` (${data.alternative_time_complexity} time)` : ""}
              </p>
            )}
            {data.tradeoffs && (
              <p className="text-caption text-text-muted">
                <span className="font-medium text-text-primary">Tradeoff: </span>
                {data.tradeoffs}
              </p>
            )}
            {data.edge_cases.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {data.edge_cases.map((ec) => (
                  <span key={ec} className="px-1.5 py-0.5 rounded text-caption bg-surface-card text-text-muted border border-border-soft">
                    {ec}
                  </span>
                ))}
              </div>
            )}
          </Collapsible>

          {cmp && (
            <Collapsible title="Compared with your previous attempt">
              {cmp.available ? (
                <div className="space-y-1.5">
                  <p className="text-caption text-text-secondary">
                    {cmp.previous_status} → {cmp.current_status}
                  </p>
                  <p className="text-body-sm text-text-secondary">{cmp.summary}</p>
                  {cmp.improvement && (
                    <p className="text-caption text-success flex items-center gap-1.5">
                      <TrendingUp className="h-3.5 w-3.5" />
                      {cmp.improvement}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-caption text-text-muted">{cmp.summary}</p>
              )}
            </Collapsible>
          )}

          {(data.cross_problem_connections.length > 0 || data.lesson || data.next_action) && (
            <Collapsible title="What you learned / try next time" defaultOpen>
              {data.cross_problem_connections.map((c, i) => (
                <p key={i} className="text-caption text-text-secondary">{c}</p>
              ))}
              {data.lesson && (
                <p className="text-body-sm text-text-secondary">
                  <span className="font-medium text-text-primary">Lesson: </span>
                  {data.lesson}
                </p>
              )}
              {data.next_action && (
                <p className="text-caption text-accent font-medium">→ {data.next_action}</p>
              )}
            </Collapsible>
          )}

          {data.limitations.length > 0 && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg bg-surface-elevated border border-border-soft">
              <Info className="h-3.5 w-3.5 mt-0.5 text-text-faint shrink-0" />
              <div className="space-y-0.5">
                {data.limitations.map((lim, i) => (
                  <p key={i} className="text-caption text-text-muted">{lim}</p>
                ))}
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}