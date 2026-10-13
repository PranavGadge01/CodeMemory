"use client";

import * as React from "react";
import { getOptimizationExplanation, ApiError } from "@/lib/api";
import type { OptimizationExplanation } from "@/lib/types";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, AlertCircle, Zap, ArrowRight, Info } from "lucide-react";
import { cn } from "@/lib/utils";

function ComplexityRow({ label, before, after, better }: { label: string; before: string; after: string; better: boolean }) {
  return (
    <div className="flex items-center gap-2 text-body-sm">
      <span className="w-14 text-text-muted text-caption shrink-0">{label}</span>
      <span className={cn("font-mono px-1.5 py-0.5 rounded text-caption", better ? "bg-error/10 text-error" : "bg-surface-card text-text-secondary")}>
        {before}
      </span>
      <ArrowRight className="h-3 w-3 text-text-faint shrink-0" />
      <span className={cn("font-mono px-1.5 py-0.5 rounded text-caption", better ? "bg-success/10 text-success font-semibold" : "bg-surface-card text-text-secondary")}>
        {after}
      </span>
    </div>
  );
}

function Section({ title, children, accent }: { title: string; children: React.ReactNode; accent?: boolean }) {
  return (
    <div className={cn("rounded-lg p-3 space-y-1.5", accent ? "bg-accent/8 border border-accent/20" : "bg-surface-card border border-border-soft")}>
      <p className="text-caption font-semibold text-text-primary uppercase tracking-wide">{title}</p>
      {children}
    </div>
  );
}

export function OptimizationExplanationCard({ slug, className }: { slug: string; className?: string }) {
  const [data, setData] = React.useState<OptimizationExplanation | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(() => {
    setLoading(true);
    setError(null);
    getOptimizationExplanation(slug)
      .then((d) => { setData(d); setLoading(false); })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Could not load optimization analysis.");
        setLoading(false);
      });
  }, [slug]);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  const timeImproved = data
    ? data.complexityComparison.currentTime !== data.complexityComparison.proposedTime
    : false;
  const spaceImproved = data
    ? data.complexityComparison.currentSpace !== data.complexityComparison.proposedSpace
    : false;

  return (
    <Surface className={className}>
      <SurfaceHeader
        eyebrow="Explainable AI"
        title="Optimization Analysis"
        description="Evidence-grounded explanation of your current approach and how to improve it."
        action={
          <button onClick={fetchData} disabled={loading} className="flex items-center gap-1.5 text-caption text-text-muted hover:text-text-primary transition-colors disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        }
      />
      <div className="p-5 space-y-4">
        {loading ? (
          <div className="py-8 text-center space-y-2">
            <Zap className="h-5 w-5 animate-pulse mx-auto text-accent" />
            <p className="text-body-sm text-text-muted">Analysing your solution…</p>
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-3 rounded bg-error-soft text-error text-body-sm border border-error/25">
            <AlertCircle className="h-4 w-4 shrink-0" /><span>{error}</span>
          </div>
        ) : data ? (
          <>
            {/* Current approach */}
            <Section title="Current approach">
              <p className="text-body-sm text-text-secondary leading-relaxed">{data.currentApproach}</p>
              <div className="flex items-center gap-1.5 mt-1">
                <Badge variant="neutral" className="text-caption">{data.approachSource}</Badge>
              </div>
            </Section>

            {/* Bottleneck */}
            <Section title="Bottleneck" accent>
              <p className="text-body-sm text-text-secondary">{data.bottleneck}</p>
              <p className="text-caption text-text-muted">{data.whyItMatters}</p>
            </Section>

            {/* Complexity comparison */}
            <Section title="Complexity change">
              <div className="space-y-1.5">
                <ComplexityRow label="Time" before={data.complexityComparison.currentTime} after={data.complexityComparison.proposedTime} better={timeImproved} />
                <ComplexityRow label="Space" before={data.complexityComparison.currentSpace} after={data.complexityComparison.proposedSpace} better={spaceImproved} />
              </div>
              <p className="text-caption text-text-muted mt-1">{data.complexityComparison.explanation}</p>
              {data.complexityComparison.assumptions && (
                <p className="text-caption text-text-faint flex items-start gap-1">
                  <Info className="h-3 w-3 mt-0.5 shrink-0" />
                  {data.complexityComparison.assumptions}
                </p>
              )}
            </Section>

            {/* Recommended approach */}
            <Section title="Recommended approach">
              <p className="text-body-sm text-text-secondary leading-relaxed">{data.recommendedApproach}</p>
              <p className="text-caption text-text-muted">{data.whyItWorks}</p>
            </Section>

            {/* Step-by-step transformation */}
            {data.transformationSteps && data.transformationSteps.length > 0 && (
              <Section title="How to get there">
                <ol className="space-y-1.5">
                  {data.transformationSteps.map((step, i) => (
                    <li key={i} className="text-body-sm text-text-secondary flex items-start gap-2">
                      <span className="shrink-0 w-5 h-5 rounded-full bg-accent/15 text-accent text-caption font-bold flex items-center justify-center">
                        {i + 1}
                      </span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              </Section>
            )}

            {/* Tradeoffs */}
            {data.tradeoffs && (
              <div className="p-3 rounded-lg bg-warning/8 border border-warning/20">
                <p className="text-caption font-semibold text-warning mb-1">Tradeoffs</p>
                <p className="text-body-sm text-text-secondary">{data.tradeoffs}</p>
              </div>
            )}

            {/* Edge cases */}
            {data.edgeCases.length > 0 && (
              <Section title="Edge cases to test">
                <ul className="space-y-1">
                  {data.edgeCases.map((e, i) => (
                    <li key={i} className="text-body-sm text-text-secondary flex items-start gap-1.5">
                      <span className="text-accent shrink-0">•</span>{e}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {/* Takeaway */}
            <div className="p-3 rounded-lg bg-success/8 border border-success/20">
              <p className="text-caption font-semibold text-success mb-1">Key takeaway</p>
              <p className="text-body-sm text-text-secondary">{data.takeaway}</p>
              {data.generalPattern && (
                <p className="text-caption text-text-muted mt-2">
                  <span className="font-medium text-text-primary">General pattern: </span>
                  {data.generalPattern}
                </p>
              )}
              {data.whenOriginalIsAcceptable && (
                <p className="text-caption text-text-muted mt-1">{data.whenOriginalIsAcceptable}</p>
              )}
              {data.followUpQuestion && (
                <p className="text-caption text-text-muted mt-2 italic">💭 {data.followUpQuestion}</p>
              )}
            </div>
          </>
        ) : null}
      </div>
    </Surface>
  );
}
