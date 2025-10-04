import Link from "next/link";
import { format, formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/StatusBadge";
import { WaterPlantButton } from "@/components/WaterPlantButton";
import { wateringTimeline } from "@/lib/mockData";
import { getPlantIds, getRequiredPlant } from "@/lib/plants";
import { MoistureBarChart } from "@/components/MoistureBarChart";

interface PlantDetailPageProps {
  params: {
    plantId: string;
  };
}

export function generateStaticParams() {
  return getPlantIds().map((plantId) => ({ plantId }));
}

export default function PlantDetailPage({ params }: PlantDetailPageProps) {
  const plant = getRequiredPlant(params.plantId);

  const nextWateringAbsolute = format(new Date(plant.nextWatering), "PPpp");
  const lastWateredAbsolute = format(new Date(plant.lastWatered), "PPpp");
  const nextWateringRelative = formatDistanceToNow(new Date(plant.nextWatering), { addSuffix: true });
  const lastWateredRelative = formatDistanceToNow(new Date(plant.lastWatered), { addSuffix: true });

  const upcomingActions = wateringTimeline.filter((item) => item.plantId === plant.id);

  return (
    <main className="detail-main">

      <section className="detail-hero">
        {/* Large visual on the left to mirror the reference */}
        <div className="detail-image-shell">
          <div className="detail-image-placeholder">
            <div className="detail-image-content">
              <span>Custom plant image</span>
            </div>
          </div>
        </div>

        {/* Right-side stacked content: title + metric chips + cards */}
        <div className="detail-side">
          <div className="detail-hero-body">
            <div className="detail-hero-top">
              <StatusBadge variant={plant.health} />
              <span className="detail-id">#{plant.id}</span>
            </div>
            <h1>{plant.name}</h1>
            <p className="detail-subtitle">
              {plant.species} • {plant.location}
            </p>
            <div className="detail-hero-metrics">
              <div className="detail-hero-metric">
                <span className="metric-label">Soil moisture</span>
                <span className="metric-value">{plant.soilMoisture}%</span>
              </div>
              <div className="detail-hero-metric">
                <span className="metric-label">Target</span>
                <span className="metric-value">{plant.targetMoisture}%</span>
              </div>
              <div className="detail-hero-metric detail-hero-metric--pump">
                <span className="metric-label">Pump status</span>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <StatusBadge variant={plant.pumpStatus} />
              {/* Use Firestore doc id matching this plant */}
              <WaterPlantButton plantId={plant.id} targetDocId={plant.id} variant="inline" />
              <WaterPlantButton plantId={plant.id} targetDocId={plant.id} command="scan" label="Scan Plants" variant="inline" />
              <WaterPlantButton plantId={plant.id} targetDocId={plant.id} command="sensor" label="Get Data" variant="inline" />
                </div>
              </div>
            </div>
          </div>

          <div className="growth-card">
            <div className="growth-card-top">
              <span className="growth-title">Moisture data</span>
              <span className="growth-period">1 day</span>
            </div>
            <div className="growth-graph">
              <MoistureBarChart plantId={plant.id} />
            </div>
          </div>

          <div className="detail-tiles">
            <div className="detail-tile"><span className="tile-label">Soil health</span><span className="tile-value">Dry</span></div>
            <div className="detail-tile"><span className="tile-label">Fertilization</span><span className="tile-value">Balanced</span></div>
          </div>

          
        </div>
      </section>

      
    </main>
  );
}
