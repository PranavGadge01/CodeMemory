"use client";

import * as React from "react";
import { getLearningAnalysis, ApiError } from "@/lib/api";
import type { AttemptEvolutionAnalysisDTO, AttemptTimelineEntryDTO } from "@/lib/api/types";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, AlertCircle, TrendingUp, TrendingDown, Minus, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, string> = {
  Accepted: "bg-success/10 text-success border-success/30",
  "Wrong Answer": "bg-error/10 text-error border-error/30",
  "Time Limit Exceeded": "bg-warning/10 text-warning border-warning/30",
  "Memory Limit Exceeded": "bg-warning/10 text-warning border-warning/30",
  "Runtime Error": "bg-error/10 text-error border-error/30",
};

function TimelineEntry({ entry, total }: { entry: AttemptTimelineEntryDTO; total: number }) {
  const isLast = entry.attempt === total;
  const statusClass = STATUS_STYLE[entry.status] ?? "bg-surface-card text-text-secondary border-border-soft";

  return (
    <div className="flex gap-3">
      {/* Line */}
      <div className="flex flex-col items-center">
        <div className={cn("w-7 h-7 rounded-full border-2 flex items-center justify-center text-caption font-bold shrink-0", statusClass)}>
          {entry.attempt}
        </div>
        {!isLast && <div className="w-0.5 flex-1 bg-border-soft my-1 min-h-[16px]" />}
      </div>
      {/* Content */}
      <div className="pb-4 flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={entry.status === "Accepted" ? "success" : "error"} className="text-caption">
            {entry.status}
          </Badge>
          <span className="text-caption text-text-muted">{entry.language}</span>
          {entry.runtime_ms != null && (
            <span className="text-caption text-text-faint font-mono">{entry.runtime_ms}ms</span>
          )}
          {entry.memory_mb != null && (
            <span className="text-caption text-text-faint font-mono">{entry.memory_mb}MB</span>
          )}
          {entry.date && (
            <span className="text-caption text-text-faint">
              {new Date(entry.date).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function List({ title, items, icon, color }: { title: string; items: string[]; icon: React.ReactNode; color: string }) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-1.5">
      <div className={cn("flex items-center gap-1.5 text-caption font-medium", color)}>
        {icon}<span>{title}</span>
      </div>
      <ul className="space-y-1 pl-1">
        {items.map((item, i) => (
          <li key={i} className="text-body-sm text-text-secondary flex items-start gap-1.5">
            <span className={cn("mt-1 shrink-0 text-xs", color)}>•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function LearningAnalysisCard({ slug, className }: { slug: string; className?: string }) {
  const [data, setData] = React.useState<AttemptEvolutionAnalysisDTO | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getLearningAnalysis(slug)
      .then((d) => { setData(d); setLoading(false); })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load learning analysis.");
        setLoading(false);
      });
  }, [slug]);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <Surface className={className}>
      <SurfaceHeader
        eyebrow="Attempt History"
        title="Learning Evolution"
        description="Chronological analysis of how your approach changed across attempts."
        action={
          <button onClick={fetchData} disabled={loading} className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        }
      />
      <div className="p-5 space-y-5">
        {loading ? (
          <div className="py-6 text-center space-y-2">
            <RefreshCw className="h-5 w-5 animate-spin mx-auto text-accent" />
            <p className="text-body-sm text-text-muted">Analysing your attempt history…</p>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
            <AlertCircle className="h-4 w-4 shrink-0" /><span>{error}</span>
          </div>
        ) : data ? (
          <>
            {/* Timeline */}
            {data.timeline.length > 0 ? (
              <div>
                <p className="text-caption font-medium text-text-primary mb-3">Attempt timeline</p>
                <div>
                  {data.timeline.map((entry) => (
                    <TimelineEntry key={entry.submission_id} entry={entry} total={data.timeline.length} />
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-body-sm text-text-muted text-center py-2">No submission history yet for this problem.</p>
            )}

            {/* Changes between attempts */}
            {data.changes_between_attempts.length > 0 && (
              <div>
                <p className="text-caption font-medium text-text-primary mb-2">What changed between attempts</p>
                <ul className="space-y-1">
                  {data.changes_between_attempts.map((c, i) => (
                    <li key={i} className="text-body-sm text-text-secondary flex items-start gap-1.5">
                      <Minus className="h-3.5 w-3.5 mt-0.5 text-text-faint shrink-0" />{c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="space-y-3">
              <List
                title="Improvements"
                items={data.improvements}
                icon={<TrendingUp className="h-3.5 w-3.5" />}
                color="text-success"
              />
              <List
                title="Regressions"
                items={data.regressions}
                icon={<TrendingDown className="h-3.5 w-3.5" />}
                color="text-error"
              />
              <List
                title="Unresolved issues"
                items={data.unresolved_issues}
                icon={<AlertCircle className="h-3.5 w-3.5" />}
                color="text-warning"
              />
            </div>

            {/* Summary */}
            {data.learning_summary && (
              <div className="rounded-lg p-3 bg-surface-card border border-border-soft space-y-1.5">
                <div className="flex items-center gap-1.5 text-caption font-medium text-text-primary">
                  <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
                  <span>Learning summary</span>
                </div>
                <p className="text-body-sm text-text-secondary leading-relaxed">{data.learning_summary}</p>
              </div>
            )}

            {/* Next action */}
            {data.recommended_next_action && (
              <div className="rounded-lg p-3 bg-accent/8 border border-accent/20">
                <p className="text-caption font-medium text-accent mb-1">Recommended next action</p>
                <p className="text-body-sm text-text-secondary">{data.recommended_next_action}</p>
              </div>
            )}
          </>
        ) : null}
      </div>
    </Surface>
  );
}
