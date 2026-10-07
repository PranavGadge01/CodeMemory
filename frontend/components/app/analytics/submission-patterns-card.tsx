"use client";

import * as React from "react";
import { getSubmissionPatterns, ApiError } from "@/lib/api";
import type { SubmissionPatternInsightsDTO, SubmissionPatternFindingDTO } from "@/lib/api/types";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, AlertCircle, TrendingUp, Target, AlertTriangle, Info } from "lucide-react";

const CATEGORY_STYLES: Record<string, { icon: React.ReactNode; badgeVariant: "accent" | "warning" | "success" | "error" | "neutral" | "info" }> = {
  fact: { icon: <Info className="h-3.5 w-3.5 text-accent" />, badgeVariant: "accent" },
  interpretation: { icon: <TrendingUp className="h-3.5 w-3.5 text-warning" />, badgeVariant: "warning" },
  recommendation: { icon: <Target className="h-3.5 w-3.5 text-success" />, badgeVariant: "success" },
  caveat: { icon: <AlertTriangle className="h-3.5 w-3.5 text-error" />, badgeVariant: "error" },
};


function FindingCard({ finding }: { finding: SubmissionPatternFindingDTO }) {
  const [expanded, setExpanded] = React.useState(false);
  const style = CATEGORY_STYLES[finding.category] ?? CATEGORY_STYLES.fact;

  return (
    <div className="rounded-lg border border-border-soft bg-surface-card p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {style.icon}
          <span className="text-body-sm font-semibold text-text-primary">{finding.title}</span>
        </div>
        <Badge variant={style.badgeVariant as "accent" | "neutral" | "warning" | "error" | "success"} className="capitalize text-caption shrink-0">
          {finding.category}
        </Badge>
      </div>
      <p className="text-body-sm text-text-secondary">{finding.observation}</p>
      <p className="text-caption text-text-muted font-mono">{finding.metric_or_examples}</p>
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-caption text-accent hover:underline"
      >
        {expanded ? "Show less" : "Why it matters & action →"}
      </button>
      {expanded && (
        <div className="pt-2 border-t border-border-soft space-y-2">
          <p className="text-body-sm text-text-secondary">
            <span className="font-medium text-text-primary">Why it matters: </span>
            {finding.why_it_matters}
          </p>
          <p className="text-body-sm text-accent font-medium">→ {finding.suggested_action}</p>
        </div>
      )}
    </div>
  );
}

export function SubmissionPatternsCard({ className }: { className?: string }) {
  const [data, setData] = React.useState<SubmissionPatternInsightsDTO | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getSubmissionPatterns()
      .then((d) => { setData(d); setLoading(false); })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load pattern insights.");
        setLoading(false);
      });
  }, []);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <Surface className={className}>
      <SurfaceHeader
        eyebrow="Learning Intelligence"
        title="Submission Pattern Analysis"
        description="Observed practice patterns grounded in your submission history."
        action={
          <button onClick={fetchData} disabled={loading} className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        }
      />
      <div className="p-5 space-y-4">
        {loading ? (
          <div className="py-6 text-center space-y-2">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto text-accent" />
            <p className="text-body-sm text-text-muted">Analysing submission patterns…</p>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
            <AlertCircle className="h-4 w-4 shrink-0" /><span>{error}</span>
          </div>
        ) : data ? (
          <>
            <p className="text-body-sm text-text-secondary leading-relaxed">{data.summary}</p>
            {data.most_important_gap && (
              <div className="p-3 rounded-lg bg-accent/8 border border-accent/20">
                <p className="text-body-sm text-accent font-medium">
                  Priority gap: {data.most_important_gap}
                </p>
              </div>
            )}
            <div className="space-y-3">
              {data.findings.map((f, i) => <FindingCard key={i} finding={f} />)}
              {data.findings.length === 0 && (
                <p className="text-body-sm text-text-muted text-center py-4">No patterns detected yet. Keep practising!</p>
              )}
            </div>
            {data.sample_size_notes.length > 0 && (
              <div className="pt-2 border-t border-border-soft">
                {data.sample_size_notes.map((n, i) => (
                  <p key={i} className="text-caption text-text-faint flex items-start gap-1.5">
                    <Info className="h-3 w-3 mt-0.5 shrink-0" />{n}
                  </p>
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>
    </Surface>
  );
}
