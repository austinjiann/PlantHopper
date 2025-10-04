"use client";

import * as React from "react";
import { MetricsCard } from "@/components/MetricsCard";
import { plants as mockPlants } from "@/lib/mockData";
import { db } from "@/lib/firebase/client";
import { collection, doc, getDocs, limit, orderBy, query } from "firebase/firestore";

type LatestSnapshot = {
  plantId: string;
  moisture: number | null;
  timestampMs: number | null;
  targetMoisture: number | null;
};

async function fetchLatestMoisture(plantId: string): Promise<{ moisture: number | null; timestampMs: number | null }> {
  try {
    const readingsRef = collection(db, "moisturedata", plantId, "readings");
    const q = query(readingsRef, orderBy("timestamp", "desc"), limit(1));
    const snap = await getDocs(q);
    if (snap.empty) return { moisture: null, timestampMs: null };
    const d = snap.docs[0].data() as any;
    const ts = d?.timestamp;
    const date = typeof ts?.toDate === "function" ? ts.toDate() : new Date(ts?.seconds ? ts.seconds * 1000 : ts);
    let numeric = d?.moisture;
    if (typeof numeric === "string") numeric = parseFloat(numeric.replace(/%/g, ""));
    if (Number.isFinite(numeric) && numeric <= 1.5) numeric = Number(numeric) * 100;
    const moisture = Number.isFinite(numeric) ? Math.max(0, Math.min(100, Number(numeric))) : null;
    return { moisture, timestampMs: Number.isFinite(date?.getTime?.()) ? date.getTime() : null };
  } catch {
    return { moisture: null, timestampMs: null };
  }
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
    (async () => {
      const latest: LatestSnapshot[] = await Promise.all(
        plantIds.map(async (id) => {
          const [{ moisture, timestampMs }, targetMoisture] = await Promise.all([
            fetchLatestMoisture(id),
            fetchTargetMoisture(id),
          ]);
          return { plantId: id, moisture, timestampMs, targetMoisture };
        })
      );

      const now = Date.now();
      const dayMs = 24 * 60 * 60 * 1000;
      const withReadings = latest.filter((l) => l.timestampMs !== null);
      const active = withReadings.filter((l) => (now - (l.timestampMs as number)) <= dayMs).length;
      // Average uses whichever moisture we can resolve (latest Firestore or fallback mock)
      const withMoisture = plantIds.map((id) => {
        const row = latest.find((l) => l.plantId === id);
        const fallbackMoist = mockPlants.find((p) => p.id === id)?.soilMoisture ?? null;
        const moisture = (row?.moisture ?? null) ?? (typeof fallbackMoist === "number" ? fallbackMoist : null);
        const target = row?.targetMoisture ?? (mockPlants.find((p) => p.id === id)?.targetMoisture ?? null);
        return { moisture, target };
      });
      const present = withMoisture.filter((m) => typeof m.moisture === "number");
      const avg = present.length
        ? Math.round(present.reduce((sum, m) => sum + (m.moisture as number), 0) / present.length)
        : 0;
      // Needs attention count should match cards; use current plant health from mock data
      const attention = mockPlants.filter((p) => p.health !== "healthy").length;
      const total = plantIds.length || 1;
      const uptimePct = Math.round((active / total) * 100);

      setStats({ activePlants: active, needsAttention: attention, averageMoisture: avg, uptime: uptimePct });
    })();
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


