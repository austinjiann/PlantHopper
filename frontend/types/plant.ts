export type PlantHealth = "healthy" | "warning" | "critical";

export interface Plant {
  id: string;
  name: string;
  species: string;
  location: string;
  soilMoisture: number; // percentage
  targetMoisture: number; // percentage
  lightExposure: "low" | "medium" | "high";
  lastWatered: string; // ISO date string
  nextWatering: string; // ISO date string
  health: PlantHealth;
  pumpStatus: "idle" | "watering" | "scheduled";
  temperature: number; // in Celsius
  humidity: number; // percentage
  moistureHistory: number[]; // latest to oldest
}
