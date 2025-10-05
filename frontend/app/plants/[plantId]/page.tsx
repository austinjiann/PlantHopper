import Link from "next/link";
import dynamic from "next/dynamic";
import { format, formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/StatusBadge";
import { WaterPlantButton } from "@/components/WaterPlantButton";
import { wateringTimeline } from "@/lib/mockData";
import { getPlantIds, getRequiredPlant } from "@/lib/plants";
import { MoistureBarChart } from "@/components/MoistureBarChart";
const CareTips = dynamic(() => import("@/components/CareTips"), { ssr: false });
const PlantImageFromFirestore = dynamic(
  () => import("@/components/PlantImageFromFirestore"),
  { ssr: false }
);
const SpeciesAndTarget = dynamic(
  () => import("@/components/SpeciesAndTarget"),
  { ssr: false }
);

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
        {/* Left column: image + care tips stacked */}
        <div className="detail-left">
          <PlantImageFromFirestore plantId={plant.id} />
          <CareTips plantId={plant.id} species={plant.species} soilMoisture={plant.soilMoisture} wateringFrequency={plant.wateringFrequency} />
        </div>

        {/* Right-side stacked content: title + metric chips + cards */}
        <div className="detail-side">
          <div className="detail-hero-body">
            <div className="detail-hero-top">
              <StatusBadge variant={plant.health} />
              <span className="detail-id">#{plant.id}</span>
            </div>
            <h1>{plant.name}</h1>
            <div className="detail-hero-metrics">
              <div className="detail-hero-metric"><span className="metric-label">Soil moisture</span><span className="metric-value">{plant.soilMoisture}%</span></div>
              <SpeciesAndTarget plantId={plant.id} fallbackTarget={plant.targetMoisture} />
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
            <div className="detail-tile"><span className="tile-label">Watering frequency</span><span className="tile-value tile-value--small">{plant.wateringFrequency}</span></div>
          </div>

        </div>
      </section>

      
    </main>
  );
}
