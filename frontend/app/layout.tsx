import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
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

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} dark`}>
      <body className="min-h-screen bg-canvas text-text-secondary antialiased">
        {children}
      </body>
    </html>
  );
}
