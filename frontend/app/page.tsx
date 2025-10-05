import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { MetricsCard } from "@/components/MetricsCard";
import { DashboardSummary } from "@/components/DashboardSummary";
import { PlantCard } from "@/components/PlantCard";
import { WateringTimeline } from "@/components/WateringTimeline";
import { StatusBadge } from "@/components/StatusBadge";
import { plants, summary, wateringTimeline } from "@/lib/mockData";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";

export default function DashboardPage() {
  const attentionPlants = plants.filter((plant) => plant.health !== "healthy");
  const activelyWatering = plants.filter((plant) => plant.pumpStatus === "watering");

  return (
    <main>
      <header className="header">
        <div className="header-row">
          <div className="header-title">
            <h1>Plant Hopper</h1>
          </div>

        </div>
        

      </header>

      <DashboardSummary />

      <section style={{ marginTop: 40 }}>
        <h2 className="section-title">Plant Overview</h2>
        <div className="plant-grid plant-grid--wide">
          {plants.slice(0, 6).map((plant) => (
            <PlantCard key={plant.id} plant={plant} />
          ))}
        </div>
      </section>
    </main>
  );
}
