import { AppShell } from "@/components/app/app-shell";

/**
 * Product shell — every authenticated route renders inside it.
 * The marketing site (`/`) and `/auth/*` deliberately render outside it.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
