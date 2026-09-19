import * as React from "react";

/**
 * Density is page-scoped state rather than a local toggle because it changes
 * the vertical rhythm of every row on the settings page. Every other settings
 * value stays local to whatever section reads it.
 */
export type Density = "comfortable" | "compact";

export const DensityContext = React.createContext<Density>("comfortable");

export function useDensity(): Density {
  return React.useContext(DensityContext);
}
