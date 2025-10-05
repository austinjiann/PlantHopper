import type { Plant } from "@/types/plant";

export const plants: Plant[] = [
  {
    id: "plant1",
    name: "Aurora",
    species: "Phalaenopsis Orchid",
    location: "Atrium North",
    soilMoisture: 68,
    targetMoisture: 65,
    lightExposure: "medium",
    lastWatered: "2025-10-02T20:30:00Z",
    nextWatering: "2025-10-04T09:00:00Z",
    health: "healthy",
    pumpStatus: "scheduled",
    temperature: 23,
    humidity: 56,
    moistureHistory: [65, 63, 60, 58, 57, 60, 62],
    wateringFrequency: "Every 7-10 days"
  },
  {
    id: "plant2",
    name: "Cascade",
    species: "Boston Fern",
    location: "Lab South",
    soilMoisture: 52,
    targetMoisture: 70,
    lightExposure: "low",
    lastWatered: "2025-10-03T04:15:00Z",
    nextWatering: "2025-10-03T21:30:00Z",
    health: "warning",
    pumpStatus: "watering",
    temperature: 22,
    humidity: 68,
    moistureHistory: [48, 45, 42, 52, 55, 57, 59],
    wateringFrequency: "Every 2-3 days"
  },
  {
    id: "plant3",
    name: "Atlas",
    species: "Ficus Lyrata",
    location: "Conference Hub",
    soilMoisture: 77,
    targetMoisture: 60,
    lightExposure: "high",
    lastWatered: "2025-10-01T18:00:00Z",
    nextWatering: "2025-10-05T08:00:00Z",
    health: "healthy",
    pumpStatus: "idle",
    temperature: 25,
    humidity: 49,
    moistureHistory: [80, 78, 76, 75, 70, 68, 65],
    wateringFrequency: "Weekly"
  },
  {
    id: "plant4",
    name: "Nova",
    species: "Haworthia",
    location: "Robotics Garage",
    soilMoisture: 34,
    targetMoisture: 40,
    lightExposure: "high",
    lastWatered: "2025-09-28T10:45:00Z",
    nextWatering: "2025-10-06T11:30:00Z",
    health: "healthy",
    pumpStatus: "scheduled",
    temperature: 26,
    humidity: 35,
    moistureHistory: [32, 35, 40, 45, 38, 34, 33],
    wateringFrequency: "Every 2 weeks"
  },
  {
    id: "plant5",
    name: "Ripple",
    species: "Monstera Deliciosa",
    location: "Design Studio",
    soilMoisture: 44,
    targetMoisture: 55,
    lightExposure: "medium",
    lastWatered: "2025-10-03T01:20:00Z",
    nextWatering: "2025-10-03T23:00:00Z",
    health: "warning",
    pumpStatus: "watering",
    temperature: 24,
    humidity: 60,
    moistureHistory: [40, 42, 39, 38, 44, 48, 52],
    wateringFrequency: "Every 5-7 days"
  }
];

export const summary = {
  activePlants: 28,
  attentionNeeded: 4,
  averageMoisture: 63,
  uptime: 99.4,
  lastSync: "2025-10-03T21:45:00Z"
};

export const wateringTimeline = [
  { plantId: "plant2", plantName: "Cascade", time: "in 45 min", action: "Auto-adjust watering cycle" },
  { plantId: "plant5", plantName: "Ripple", time: "in 2 hrs", action: "Nutrient dose" },
  { plantId: "plant1", plantName: "Aurora", time: "Tomorrow 09:00", action: "Standard watering" }
];

export const healthDistribution = {
  healthy: 22,
  warning: 5,
  critical: 1
};
