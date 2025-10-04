import { formatDistanceToNow } from "date-fns";
import { MetricsCard } from "@/components/MetricsCard";
import { PlantCard } from "@/components/PlantCard";
import { WateringTimeline } from "@/components/WateringTimeline";
import { HealthDistribution } from "@/components/HealthDistribution";
import { StatusBadge } from "@/components/StatusBadge";
import { plants, summary, wateringTimeline, healthDistribution } from "@/lib/mockData";

export default function DashboardPage() {
  const attentionPlants = plants.filter((plant) => plant.health !== "healthy");
  const activelyWatering = plants.filter((plant) => plant.pumpStatus === "watering");

  return (
    <main>
      <header className="header">
        <div className="header-row">
          <div className="header-title">
            <h1>Plant Hopper Control</h1>
            <StatusBadge variant="scheduled">Robots online</StatusBadge>
          </div>
          <div className="header-actions">
            <button className="button">
              <span aria-hidden>📥</span>
              Sync devices
            </button>
            <button className="button button--primary">
              <span aria-hidden>➕</span>
              Register plant
            </button>
          </div>
        </div>
        <div className="filter-bar">
          <input placeholder="Search by plant name, species, or location" />
          <select className="filter-select" defaultValue="all">
            <option value="all">Health: All</option>
            <option value="healthy">Healthy</option>
            <option value="warning">Needs attention</option>
            <option value="critical">Critical</option>
          </select>
          <select className="filter-select" defaultValue="all">
            <option value="all">Zones: All areas</option>
            <option value="atrium">Atrium</option>
            <option value="lab">Labs</option>
            <option value="studio">Studios</option>
          </select>
        </div>
        <p className="secondary-text">
          Last synced {formatDistanceToNow(new Date(summary.lastSync), { addSuffix: true })}
        </p>
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

      <section style={{ marginTop: 40, display: "grid", gap: 24, gridTemplateColumns: "1.3fr 1fr" }}>
        <div>
          <h2 className="section-title">Plant overview</h2>
          <p className="secondary-text">
            Monitor current moisture, upcoming watering, and environment metrics for each plant.
          </p>
          <div className="plant-grid">
            {plants.map((plant) => (
              <PlantCard key={plant.id} plant={plant} />
            ))}
          </div>
        </div>
        <div style={{ display: "grid", gap: 24 }}>
          <HealthDistribution {...healthDistribution} />
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
                    <td>{plant.name}</td>
                    <td>
                      {plant.soilMoisture}% • target {plant.targetMoisture}%
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
                      <td>{plant.name}</td>
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
