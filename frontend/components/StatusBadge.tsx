import clsx from "clsx";
import type { PlantHealth } from "@/types/plant";

type AdditionalVariant = "scheduled" | "watering" | "idle";

type StatusBadgeProps = {
  variant: PlantHealth | AdditionalVariant;
  children?: React.ReactNode;
};

const LABELS: Record<PlantHealth | AdditionalVariant, string> = {
  healthy: "Healthy",
  warning: "Needs Attention",
  critical: "Critical",
  scheduled: "Scheduled",
  watering: "Watering",
  idle: "Idle"
};

export function StatusBadge({ variant, children }: StatusBadgeProps) {
  return (
    <span className={clsx("badge", `badge--${variant}`)}>
      {children ?? LABELS[variant]}
    </span>
  );
}
