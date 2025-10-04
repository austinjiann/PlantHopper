import { formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/StatusBadge";
import type { Plant } from "@/types/plant";

interface PlantCardProps {
  plant: Plant;
}


function formatDistanceLabel(date: string) {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

export function PlantCard({ plant }: PlantCardProps) {
  const moistureDelta = plant.soilMoisture - plant.targetMoisture;
  const nextWateringLabel = formatDistanceLabel(plant.nextWatering);
  const lastWateredLabel = formatDistanceLabel(plant.lastWatered);

  return (
    <article className="plant-card">
      <header className="plant-card-header">
        <div>
          <h3 style={{ margin: 0 }}>{plant.name}</h3>
          <p className="secondary-text" style={{ fontSize: "0.85rem" }}>
            {plant.species} • {plant.location}
          </p>
        </div>
        <StatusBadge variant={plant.health} />
      </header>

      <div className="plant-meta">
        <div className="meta-item">
          <span className="meta-label">Soil moisture</span>
          <span className="meta-value">{plant.soilMoisture}%</span>
          <div className="progress">
            <span style={{ width: `${Math.min(plant.soilMoisture, 100)}%` }} />
          </div>
          <p className="secondary-text" style={{ fontSize: "0.8rem" }}>
            Target {plant.targetMoisture}% ({moistureDelta >= 0 ? "+" : ""}
            {moistureDelta}%)
          </p>
        </div>

        <div className="meta-item">
          <span className="meta-label">Light exposure</span>
          <span className="meta-value" style={{ textTransform: "capitalize" }}>
            {plant.lightExposure}
          </span>
          <span className="meta-label">Pump status</span>
          <p className="secondary-text" style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <StatusBadge variant={plant.pumpStatus} />
          </p>
        </div>

        <div className="meta-item">
          <span className="meta-label">Environment</span>
          <span className="meta-value">{plant.temperature}°C • {plant.humidity}% RH</span>
          <span className="meta-label">Last watered</span>
          <span className="secondary-text">{lastWateredLabel}</span>
        </div>

        <div className="meta-item">
          <span className="meta-label">Next watering</span>
          <span className="meta-value">{nextWateringLabel}</span>
          <span className="meta-label">Moisture trend</span>
          <div className="sparkline">
            {plant.moistureHistory.map((value, index) => (
              <span
                key={`${plant.id}-spark-${index}`}
                className={value < plant.targetMoisture - 5 ? "sparkline-bar is-low" : "sparkline-bar"}
                style={{ height: `${Math.max(12, value / 100 * 36)}px` }}
              />
            ))}
          </div>
        </div>
      </div>
    </article>
  );
}
