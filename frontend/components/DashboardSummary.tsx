"use client";

import * as React from "react";
import { MetricsCard } from "@/components/MetricsCard";
import { plants as mockPlants } from "@/lib/mockData";
import { db } from "@/lib/firebase/client";
import { collection, limit, onSnapshot, orderBy, query, getDocs } from "firebase/firestore";

type LatestSnapshot = {
  plantId: string;
  moisture: number | null;
  timestampMs: number | null;
  targetMoisture: number | null;
};

// Utility: parse a single reading row into normalized percentage and epoch ms
function parseReading(row: any): { moisture: number | null; timestampMs: number | null } {
  const ts = row?.timestamp;
  const date = typeof ts?.toDate === "function" ? ts.toDate() : new Date(ts?.seconds ? ts.seconds * 1000 : ts);
  let numeric = row?.moisture;
  if (typeof numeric === "string") numeric = parseFloat(numeric.replace(/%/g, ""));
  if (Number.isFinite(numeric) && numeric <= 1.5) numeric = Number(numeric) * 100; // convert 0-1 to 0-100
  const moisture = Number.isFinite(numeric) ? Math.max(0, Math.min(100, Number(numeric))) : null;
  return { moisture, timestampMs: Number.isFinite(date?.getTime?.()) ? date.getTime() : null };
}

async function fetchTargetMoisture(plantId: string): Promise<number | null> {
  try {
    const imagesRef = collection(db, "plant_images");
    const q = query(imagesRef, orderBy("timestamp", "desc"), limit(25));
    const snap = await getDocs(q);
    const row = snap.docs.map((d) => d.data() as any).find((d) => d?.plantId === plantId);
    const tm = row?.targetMoisture;
    if (typeof tm === "number") return Math.round(Math.max(0, Math.min(100, tm)));
  } catch {}
  // Fallback to mock target
  const fallback = mockPlants.find((p) => p.id === plantId)?.targetMoisture;
  return typeof fallback === "number" ? fallback : null;
}

export function DashboardSummary() {
  const [stats, setStats] = React.useState({
    activePlants: 0,
    needsAttention: 0,
    averageMoisture: 0,
    uptime: 0,
  });

  React.useEffect(() => {
    const plantIds = mockPlants.map((p) => p.id);
    const latestById: Record<string, LatestSnapshot> = Object.create(null);

    const recompute = () => {
      const now = Date.now();
      const dayMs = 24 * 60 * 60 * 1000;
      const latest = plantIds.map((id) => latestById[id]).filter(Boolean) as LatestSnapshot[];
      const active = latest.filter((l) => l?.timestampMs && (now - (l.timestampMs as number)) <= dayMs).length;
      const withMoisture = plantIds.map((id) => {
        const row = latestById[id];
        const fallbackMoist = mockPlants.find((p) => p.id === id)?.soilMoisture ?? null;
        const moisture = (row?.moisture ?? null) ?? (typeof fallbackMoist === "number" ? fallbackMoist : null);
        const target = row?.targetMoisture ?? (mockPlants.find((p) => p.id === id)?.targetMoisture ?? null);
        return { moisture, target };
      });
      const present = withMoisture.filter((m) => typeof m.moisture === "number");
      const avg = present.length ? Math.round(present.reduce((sum, m) => sum + (m.moisture as number), 0) / present.length) : 0;
      const attention = mockPlants.filter((p) => p.health !== "healthy").length;
      const total = plantIds.length || 1;
      const uptimePct = Math.round((active / total) * 100);
      setStats({ activePlants: active, needsAttention: attention, averageMoisture: avg, uptime: uptimePct });
    };

    // Seed targets (from images) once, in the background
    (async () => {
      const targets = await Promise.all(plantIds.map((id) => fetchTargetMoisture(id)));
      targets.forEach((tm, i) => {
        const id = plantIds[i];
        latestById[id] = { plantId: id, moisture: latestById[id]?.moisture ?? null, timestampMs: latestById[id]?.timestampMs ?? null, targetMoisture: tm };
      });
      recompute();
    })();

    // Live listeners for each plant's latest reading
    const unsubs = plantIds.map((id) => {
      const readingsRef = collection(db, "moisturedata", id, "readings");
      const q = query(readingsRef, orderBy("timestamp", "desc"), limit(1));
      return onSnapshot(q, (snap) => {
        if (!snap.empty) {
          const row = snap.docs[0].data();
          const parsed = parseReading(row);
          latestById[id] = {
            plantId: id,
            moisture: parsed.moisture,
            timestampMs: parsed.timestampMs,
            targetMoisture: latestById[id]?.targetMoisture ?? null,
          };
          recompute();
        }
      });
    });

    return () => unsubs.forEach((u) => u());
  }, []);

  return (
    <section className="dashboard-grid" aria-label="System summary">
      <MetricsCard label="Active plants" value={String(stats.activePlants)} description="Connected to the watering network" trend={{ direction: "up", label: "+" + Math.max(0, stats.activePlants - 0).toString() + " new today" }} />
      <MetricsCard label="Needs attention" value={String(stats.needsAttention)} description="Review moisture or nutrient alerts" trend={{ direction: "steady", label: "Live" }} accent="amber" />
      <MetricsCard label="Average moisture" value={`${stats.averageMoisture}%`} description="Across last 24 hours" trend={{ direction: "up", label: "Live" }} accent="blue" />
      <MetricsCard label="Remaining water" value={`75 ml`} description="Reservoir" trend={{ direction: "up", label: "Live" }} accent="green" />
    </section>
  );
}


