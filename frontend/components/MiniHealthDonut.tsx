"use client";

import * as React from "react";
import { Label, Pie, PieChart } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";

type Props = {
  healthy: number;
  warning: number;
  critical: number;
  size?: number;
};

export function MiniHealthDonut({ healthy, warning, critical, size = 140 }: Props) {
  const total = healthy + warning + critical;
  const healthyPct = total > 0 ? Math.round((healthy / total) * 100) : 0;

  const data = [
    { key: "Healthy", value: healthy, fill: "#10b981" },
    { key: "Needs attention", value: warning, fill: "#f59e0b" },
    { key: "Critical", value: critical, fill: "#ef4444" }
  ];

  return (
    <ChartContainer className="flex items-center justify-center" style={{ width: size, height: size }}>
      <PieChart width={size} height={size}>
        <ChartTooltip cursor={false} content={<ChartTooltipContent hideLabel />} />
        <Pie data={data} dataKey="value" nameKey="key" innerRadius={size * 0.32} strokeWidth={5} />
        <Label
          content={({ viewBox }: any) => {
            if (viewBox && "cx" in viewBox && "cy" in viewBox) {
              return (
                <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle" dominantBaseline="middle">
                  <tspan x={viewBox.cx} y={viewBox.cy} className="fill-foreground text-xl font-extrabold">
                    {healthyPct}%
                  </tspan>
                </text>
              );
            }
            return null;
          }}
        />
      </PieChart>
    </ChartContainer>
  );
}


