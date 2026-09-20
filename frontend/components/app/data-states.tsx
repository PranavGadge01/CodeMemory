import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/primitives";
import { Skeleton } from "@/components/ui/primitives";
import { ApiError, isNetworkError } from "@/lib/api";

/**
 * Loading / empty / error states.
 *
 * Every one of these is built from the existing primitives — `Skeleton` and
 * `EmptyState` — so a page that is fetching or failing still renders inside the
 * approved CodeMemory visual language. No new card shapes, no spinners, no
 * layout redesign.
 */

/**
 * The skeleton the data-driven pages render while the request is in flight.
 * Deliberately quiet: the same ruled strip the page already uses, sized to the
 * sections that are actually loading.
 */
export function PageSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-[76px] rounded-lg" />
      <Skeleton className="h-[220px] rounded-lg" />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Skeleton className="h-[260px] rounded-lg lg:col-span-2" />
        <Skeleton className="h-[260px] rounded-lg" />
      </div>
    </div>
  );
}

/**
 * Error state. The message is the backend's own — the API preserves its error
 * shape end to end — so what the user reads is what actually went wrong.
 * `onRetry` re-runs the fetch; when it is unavailable the row is omitted rather
 * than wired to a no-op.
 */
export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: ApiError;
  onRetry?: () => void;
  className?: string;
}) {
  const message = isNetworkError(error)
    ? "The CodeMemory API could not be reached. Check that the local server is running and try again."
    : error.message;

  return (
    <EmptyState
      className={className}
      icon={<AlertCircle className="h-4 w-4 text-error" aria-hidden="true" />}
      title={isNetworkError(error) ? "Cannot reach the API" : "Something went wrong"}
      description={message}
      action={
        onRetry ? (
          <Button variant="subtle" size="sm" onClick={onRetry}>
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Try again
          </Button>
        ) : null
      }
    />
  );
}

/**
 * Empty state for a section that loaded successfully and has no data. Kept
 * separate from `ErrorState` so a page never renders an apology for data that
 * simply does not exist yet.
 */
export function EmptyDataState({
  title,
  description,
  className,
}: {
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <EmptyState
      className={className}
      title={title}
      description={description}
    />
  );
}
