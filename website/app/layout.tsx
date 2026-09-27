import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { THEME_STORAGE_KEY } from "@/lib/theme";
import { ThemeProvider } from "@/components/system/theme";
import "./globals.css";

/**
 * Root layout for the public website.
 *
 * This is the desktop application's layout without the application-only
 * providers: no local API client, no settings store, no runtime data. The
 * design tokens, typography and theme handling are the same ones the product
 * uses, so the website and the application read as one brand.
 */
export const metadata: Metadata = {
  title: {
    default: "CodeMemory — Your coding history, remembered.",
    template: "%s · CodeMemory",
  },
  description:
    "CodeMemory turns your coding history into searchable knowledge, measurable progress, and a memory of how you solve problems. A local-first Windows workspace for your LeetCode submissions.",
  applicationName: "CodeMemory",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFFFFF" },
    { media: "(prefers-color-scheme: dark)", color: "#07080A" },
  ],
  width: "device-width",
  initialScale: 1,
};

const THEME_INIT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)});var d=t==="light"||t==="dark"?t:(t==="system"?(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):"dark");document.documentElement.classList.add(d);}catch(e){document.documentElement.classList.add("dark");}})();`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} suppressHydrationWarning />
      </head>
      <body
        className="min-h-screen bg-canvas text-text-secondary antialiased"
        suppressHydrationWarning
      >
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
