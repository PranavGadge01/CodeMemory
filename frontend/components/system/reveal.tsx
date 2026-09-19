"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Reveal-on-scroll.
 *
 * CSS-only in spirit — IntersectionObserver does nothing more than toggle a
 * class, so the animation itself remains a cheap transform/opacity pair and
 * honours `prefers-reduced-motion` through globals.css.
 */
export function Reveal({
  children,
  className,
  delay = 0,
  as: Tag = "div",
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  as?: React.ElementType;
}) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const element = ref.current;
    if (!element) return;

    // Reveal is only ever called from a callback — never synchronously in the
    // effect body — so neither path triggers a cascading render.
    const reveal = () => setVisible(true);

    if (typeof IntersectionObserver === "undefined") {
      // Nothing to observe: schedule the reveal on a microtask, which still
      // lands before the next paint, so nothing visibly flickers.
      Promise.resolve().then(reveal);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            reveal();
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag
      ref={ref}
      className={cn("reveal", visible && "is-visible", className)}
      style={delay > 0 ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </Tag>
  );
}
