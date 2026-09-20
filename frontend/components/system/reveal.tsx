"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Reveal-on-scroll.
 *
 * CSS-only in spirit — IntersectionObserver does nothing more than toggle a
 * class, so the animation itself remains a cheap transform/opacity pair and
 * honours `prefers-reduced-motion` through globals.css.
 *
 * The threshold is 0, not a ratio. A ratio threshold is unreachable for content
 * taller than the viewport: the submissions panel is ~6500px tall, so even when
 * it fills a 800px viewport the intersection ratio caps at ~0.12 and a 0.12
 * threshold with a shrunk root never fires — leaving the panel stranded at
 * opacity 0 until something resizes it. Threshold 0 with a small negative
 * bottom rootMargin still defers the reveal until the element is about to
 * enter the viewport, which is the animation's actual intent.
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
      { threshold: 0, rootMargin: "0px 0px -8% 0px" },
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
