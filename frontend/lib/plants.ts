import { notFound } from "next/navigation";
import { plants } from "@/lib/mockData";

export function getPlantById(id: string) {
  return plants.find((plant) => plant.id === id);
}

export function getRequiredPlant(id: string) {
  const plant = getPlantById(id);
  if (!plant) {
    notFound();
  }
  return plant;
}

export function getPlantIds() {
  return plants.map((plant) => plant.id);
}
