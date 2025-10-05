"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/StatusBadge";
import type { Plant } from "@/types/plant";
import { PlantThumb } from "@/components/PlantThumb";
import * as React from "react";
import { collection, limit, onSnapshot, orderBy, query } from "firebase/firestore";
import { db } from "@/lib/firebase/client";

interface PlantCardProps {
  plant: Plant;
}


function formatDistanceLabel(date: string) {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function PlantCard({ plant }: PlantCardProps) {
  const [lastMeasuredLabel, setLastMeasuredLabel] = React.useState<string>(formatDistanceLabel(plant.lastWatered));
  const [liveMoisture, setLiveMoisture] = React.useState<number>(plant.soilMoisture);

  React.useEffect(() => {
    const readingsRef = collection(db, "moisturedata", plant.id, "readings");
    const q = query(readingsRef, orderBy("timestamp", "desc"), limit(1));
    const unsub = onSnapshot(q, (snap) => {
      if (snap.empty) return;
      const d = snap.docs[0].data() as any;
      // Update "Last watered" relative time based on latest record timestamp
      const ts: any = d?.timestamp;
      const date = typeof ts?.toDate === "function" ? ts.toDate() : new Date(ts?.seconds ? ts.seconds * 1000 : ts);
      if (date && typeof date.getTime === "function" && !Number.isNaN(date.getTime())) {
        setLastMeasuredLabel(formatDistanceToNow(date, { addSuffix: true }));
      }
      let numeric: any = d?.moisture;
      if (typeof numeric === "string") numeric = parseFloat(numeric.replace(/%/g, ""));
      if (Number.isFinite(numeric) && numeric <= 1.5) numeric = Number(numeric) * 100; // convert 0-1 → %
      if (Number.isFinite(numeric)) {
        const pct = Math.max(0, Math.min(100, Number(numeric)));
        setLiveMoisture(Math.round(pct));
      }
    });
    return () => unsub();
  }, [plant.id]);

  return (
    <Link href={`/plants/${plant.id}`} className="plant-card-link">
      <article className="plant-card plant-card--compact">
        <header className="plant-card-header">
          <div>
            <h3 style={{ margin: 0 }}>{plant.name}</h3>
          </div>
          <StatusBadge variant={plant.health} />
        </header>

        <div className="plant-meta">
          <div className="meta-item">
            <PlantThumb plantId={plant.id} />
          </div>

          <div className="meta-item">
            <span className="meta-label">Last watered</span>
            <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{lastMeasuredLabel}</span>
            <span className="meta-label" style={{ marginTop: 10 }}>Soil moisture</span>
            <span className="meta-value">{liveMoisture}%</span>
            <div className="progress">
              <span style={{ width: `${Math.min(liveMoisture, 100)}%` }} />
            </div>
            <span className="meta-label" style={{ marginTop: 8 }}>Watering frequency</span>
            <span className="meta-value" style={{ fontSize: "0.85rem" }}>{plant.wateringFrequency}</span>
          </div>
        </div>
      </article>
    </Link>
  );
}
