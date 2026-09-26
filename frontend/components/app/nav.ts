import {
  Gauge,
  Code2,
  TerminalSquare,
  ChartColumnBig,
  Network,
  RotateCw,
  Settings,
  Search,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Shown when the sidebar is collapsed to a rail. */
  shortLabel: string;
}

export const PRIMARY_NAV: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: Gauge, shortLabel: "Overview" },
  { label: "Problems", href: "/problems", icon: Code2, shortLabel: "Problems" },
  { label: "Submissions", href: "/submissions", icon: TerminalSquare, shortLabel: "Submissions" },
  { label: "Analytics", href: "/analytics", icon: ChartColumnBig, shortLabel: "Analytics" },
  { label: "Knowledge", href: "/knowledge", icon: Network, shortLabel: "Knowledge" },
  { label: "Revision", href: "/revision", icon: RotateCw, shortLabel: "Revision" },
  { label: "Search", href: "/search", icon: Search, shortLabel: "Search" },
];

export const SECONDARY_NAV: NavItem[] = [
  { label: "Settings", href: "/settings", icon: Settings, shortLabel: "Settings" },
];

/** Mobile bottom-nav needs a shorter label set. */
export const MOBILE_NAV: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: Gauge, shortLabel: "Overview" },
  { label: "Problems", href: "/problems", icon: Code2, shortLabel: "Problems" },
  { label: "Analytics", href: "/analytics", icon: ChartColumnBig, shortLabel: "Analytics" },
  { label: "Knowledge", href: "/knowledge", icon: Network, shortLabel: "Knowledge" },
  { label: "Settings", href: "/settings", icon: Settings, shortLabel: "Settings" },
];
