import clsx from "clsx";

interface MetricsCardProps {
  label: string;
  value: string;
  description?: string;
  trend?: {
    label: string;
    direction: "up" | "down" | "steady";
  };
  accent?: "green" | "blue" | "amber" | "red";
}

const accentClass: Record<NonNullable<MetricsCardProps["accent"]>, string> = {
  green: "transparent",
  blue: "transparent",
  amber: "transparent",
  red: "transparent"
};

export function MetricsCard({ label, value, description, trend, accent = "green" }: MetricsCardProps) {
  return (
    <div className="card" style={{ position: "relative" }}>
      <div style={{ position: "relative" }}>
        <p className="secondary-text" style={{ marginBottom: 6 }}>{label}</p>
        <h3 style={{ fontSize: "1.9rem", margin: "0 0 8px" }}>{value}</h3>
        {description && <p style={{ fontSize: "0.85rem" }}>{description}</p>}
        {trend && (
          <p
            className={clsx("secondary-text")}
            style={{
              display: "inline-flex",
              gap: 6,
              alignItems: "center",
              marginTop: 12,
              fontWeight: 600,
              color: trend.label.toLowerCase() === "live"
                ? "#16a34a"
                : trend.direction === "up"
                ? "var(--accent)"
                : trend.direction === "down"
                ? "#f87272"
                : "var(--text-muted)"
            }}
          >
            {trend.label}
          </p>
        )}
      </div>
    </div>
  );
}
