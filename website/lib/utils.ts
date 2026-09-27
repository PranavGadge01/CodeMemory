import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes without specificity conflicts.
 * Used by every CodeMemory component.
 *
 * `tailwind-merge` only knows the classes Tailwind generates itself.
 * CodeMemory's type scale lives in `globals.css` as hand-written utilities
 * (`text-display-xl`, `text-body-md`, …), so without the extension below it
 * files every one of them under *text colour*. The last one in a class list
 * then wins the conflict and a real colour declared earlier — `text-black` on
 * the primary button, for example — is silently discarded, leaving grey text
 * on a white button. Registering the scale as font sizes keeps both.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        "text-display-xl",
        "text-display-lg",
        "text-heading-xl",
        "text-heading-lg",
        "text-heading-md",
        "text-heading-sm",
        "text-body-lg",
        "text-body-md",
        "text-body-sm",
        "text-caption",
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
