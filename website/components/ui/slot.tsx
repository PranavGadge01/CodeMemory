import * as React from "react";

/**
 * Minimal `asChild` slot — merges the child element's props with the parent's
 * so a Button can render as a link without duplicating its own markup.
 * Intentionally dependency-free.
 */
export interface SlotProps extends React.HTMLAttributes<HTMLElement> {
  children?: React.ReactNode;
}

export function Slot({ children, ...props }: SlotProps) {
  if (!React.isValidElement(children)) {
    return null;
  }

  const child = children as React.ReactElement<Record<string, unknown>>;
  const childProps = child.props ?? {};

  return React.cloneElement(child, {
    ...props,
    ...childProps,
    className: cnJoin([props.className, childProps.className as string | undefined]),
    style: { ...props.style, ...(childProps.style as React.CSSProperties) },
  });
}

function cnJoin(classes: Array<string | undefined>): string | undefined {
  const value = classes.filter(Boolean).join(" ");
  return value.length > 0 ? value : undefined;
}
