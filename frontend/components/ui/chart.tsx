"use client";

import * as React from "react";

export type ChartConfig = Record<
  string,
  {
    label?: string;
    color?: string;
  }
>;

type DivProps = React.HTMLAttributes<HTMLDivElement> & { config?: ChartConfig };

export function ChartContainer({ className, ...props }: DivProps) {
  return <div className={className} {...props} />;
}

export function ChartTooltip(_props: any) {
  return null;
}

export function ChartTooltipContent(_props: any) {
  return null as any;
}


