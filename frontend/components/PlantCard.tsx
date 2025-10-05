import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/StatusBadge";
import type { Plant } from "@/types/plant";
import { PlantThumb } from "@/components/PlantThumb";

interface PlantCardProps {
  plant: Plant;
}


function formatDistanceLabel(date: string) {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function PlantCard({ plant }: PlantCardProps) {
  const lastMeasuredLabel = formatDistanceLabel(plant.lastWatered);

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
            <span className="meta-value">{plant.soilMoisture}%</span>
            <div className="progress">
              <span style={{ width: `${Math.min(plant.soilMoisture, 100)}%` }} />
            </div>
            <span className="meta-label" style={{ marginTop: 8 }}>Watering frequency</span>
            <span className="meta-value" style={{ fontSize: "0.85rem" }}>{plant.wateringFrequency}</span>
          </div>
        </div>
      </article>
    </Link>
  );
}
