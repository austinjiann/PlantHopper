"use client";

import * as React from "react";
import { collection, onSnapshot, orderBy, query } from "firebase/firestore";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { db } from "@/lib/firebase/client";

type Reading = { timestamp: any; moisture: number };

interface MoistureBarChartProps {
  plantId?: string; // defaults to "plant1"
}

export function MoistureBarChart({ plantId = "plant1" }: MoistureBarChartProps) {
  const [data, setData] = React.useState<Array<{ dateMs: number; dateLabel: string; timeLabel: string; moisture: number }>>([]);

  React.useEffect(() => {
    const readingsRef = collection(db, "moisturedata", plantId, "readings");
    const q = query(readingsRef, orderBy("timestamp", "asc"));
    const unsub = onSnapshot(q, (snap) => {
      const rows = snap.docs.map((d) => d.data() as Reading);
      console.log("[MoistureChart] snapshot size:", snap.size, rows);
      const formatted = rows
        .map((r) => {
          const ts = r.timestamp as any;
          const hasValidTs = Boolean(ts && (typeof ts?.toDate === "function" || typeof ts?.seconds === "number" || typeof ts === "number"));
          if (!hasValidTs) return null; // skip rows without a timestamp
          const date = typeof ts?.toDate === "function"
            ? ts.toDate()
            : new Date(ts?.seconds ? ts.seconds * 1000 : ts);

          // Parse moisture robustly: accept number, numeric string, or percentage string
          const rawMoisture: any = (r as any).moisture;
          let numeric = typeof rawMoisture === "string" ? parseFloat(rawMoisture.replace(/%/g, "")) : Number(rawMoisture);
          if (Number.isFinite(numeric) && numeric <= 1.5) {
            numeric = numeric * 100; // support 0-1 inputs
          }
          // Clamp to 0-100 and drop invalid
          const moisture = Number.isFinite(numeric) ? Math.min(100, Math.max(0, numeric)) : NaN;

          const dateMs = date.getTime();
          const dateLabel = date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
          const timeLabel = date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false });
          return { dateMs, dateLabel, timeLabel, moisture };
        })
        .filter((p) => p && Number.isFinite(p.dateMs) && Number.isFinite(p.moisture)) as Array<{ dateMs: number; dateLabel: string; timeLabel: string; moisture: number }>;

      console.log("[MoistureChart] formatted points:", formatted.length, formatted);
      setData(formatted);
    });
    return () => unsub();
  }, [plantId]);

  React.useEffect(() => {
    console.log("[MoistureChart] render data length", data.length, data);
  }, [data]);

  return (
    <Card className="py-0" style={{ background: "transparent", border: "none", boxShadow: "none" }}>
      <CardContent className="px-0 py-0">
        <div style={{ width: "100%" }}>
          <ResponsiveContainer width="100%" height={180} key={`${plantId}:${data.length}`}>
            <LineChart data={data} margin={{ left: 12, right: 12, top: 8, bottom: 16 }}>
              <CartesianGrid vertical={false} stroke="rgba(148,163,184,0.25)" />
              <XAxis
                type="number"
                dataKey="dateMs"
                domain={["dataMin", "dataMax"]}
                tickLine
                axisLine
                tickMargin={8}
                stroke="#94a3b8"
                tickFormatter={(ms: number) =>
                  new Date(ms).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false })
                }
              />
              <YAxis domain={[0, 100]} allowDecimals={false} width={36} tickFormatter={(v: number) => `${v}%`} stroke="#94a3b8" />
              <Tooltip
                formatter={(v: any) => [`${Math.round(Number(v))}%`, "Moisture"]}
                labelFormatter={(label: any) => String(label)}
              />
              <Line
                type="monotone"
                dataKey="moisture"
                stroke="#16a34a"
                strokeWidth={2}
                dot={{ r: 4, stroke: '#16a34a', fill: '#16a34a' }}
                activeDot={{ r: 5 }}
                connectNulls
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}


