import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import { ThemeProvider } from "@/components/system/theme";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "CodeMemory — Your coding history, remembered.",
    template: "%s · CodeMemory",
  },
  description:
    "CodeMemory turns your coding history into searchable knowledge, measurable progress, and a memory of how you solve problems.",
  applicationName: "CodeMemory",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#07080A",
  width: "device-width",
  initialScale: 1,
};

/**
 * Applies the stored theme before first paint. Runs inline in `<head>` so it
 * completes before the body is parsed — no dark-to-light flash, and the class
 * React hydrates can differ from this one, hence `suppressHydrationWarning`.
 * Dark is the default for any unreadable or unset preference.
 */
const THEME_INIT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)});var theme=t==="light"||t==="dark"?t:"dark";document.documentElement.classList.add(theme);}catch(e){document.documentElement.classList.add("dark");}})();`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body className="min-h-screen bg-canvas text-text-secondary antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
