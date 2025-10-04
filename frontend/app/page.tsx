import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { MetricsCard } from "@/components/MetricsCard";
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

      <section className="dashboard-grid" aria-label="System summary">
        <MetricsCard
          label="Active plants"
          value={summary.activePlants.toString()}
          description="Connected to the watering network"
          trend={{ direction: "up", label: "+3 new today" }}
        />
        <MetricsCard
          label="Needs attention"
          value={summary.attentionNeeded.toString()}
          description="Review moisture or nutrient alerts"
          trend={{ direction: "steady", label: "No change" }}
          accent="amber"
        />
        <MetricsCard
          label="Average moisture"
          value={`${summary.averageMoisture}%`}
          description="Across last 24 hours"
          trend={{ direction: "up", label: "+4% vs target" }}
          accent="blue"
        />
        <MetricsCard
          label="System uptime"
          value={`${summary.uptime}%`}
          description="Fleet availability"
          trend={{ direction: "up", label: "+0.3%" }}
          accent="green"
        />
      </section>

      <section style={{ marginTop: 40, display: "grid", gap: 24, gridTemplateColumns: "1.3fr 1fr", alignItems: "start" }}>
        <div>
          <h2 className="section-title">Plant overview</h2>

          <div className="plant-grid">
            {plants.slice(0, 5).map((plant) => (
              <PlantCard key={plant.id} plant={plant} />
            ))}
            
          </div>
        </div>
        <div style={{ display: "grid", gap: 8, rowGap: 8, alignItems: "start", marginTop: 40 }}>
          <div className="card">
            <h3>Attention queue</h3>
            <p className="secondary-text">
              Plants below target moisture or flagged for maintenance.
            </p>
            <table className="table">
              <thead>
                <tr>
                  <th align="left">Plant</th>
                  <th align="left">Moisture</th>
                  <th align="left">Action</th>
                </tr>
              </thead>
              <tbody>
                {attentionPlants.map((plant) => (
                  <tr key={`${plant.id}-attention`}>
                    <td>
                      <Link href={`/plants/${plant.id}`} className="breadcrumb-link">
                        {plant.name}
                      </Link>
                    </td>
                    <td>
                      {plant.soilMoisture}% - target {plant.targetMoisture}%
                    </td>
                    <td>
                      <StatusBadge variant={plant.pumpStatus} />
                    </td>
                  </tr>
                ))}
                {attentionPlants.length === 0 && (
                  <tr>
                    <td colSpan={3}>All plants are operating within expected ranges.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3>Currently watering</h3>
            {activelyWatering.length ? (
              <table className="table">
                <thead>
                  <tr>
                    <th align="left">Plant</th>
                    <th align="left">Location</th>
                    <th align="left">Moisture</th>
                  </tr>
                </thead>
                <tbody>
                  {activelyWatering.map((plant) => (
                    <tr key={`${plant.id}-watering`}>
                      <td>
                        <Link href={`/plants/${plant.id}`} className="breadcrumb-link">
                          {plant.name}
                        </Link>
                      </td>
                      <td>{plant.location}</td>
                      <td>{plant.soilMoisture}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="secondary-text" style={{ marginTop: 16 }}>
                No plants are being watered right now.
              </p>
            )}
          </div>
          <WateringTimeline items={wateringTimeline} />
        </div>
      </section>
    </main>
  );
}
