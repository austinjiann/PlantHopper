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
  green: "linear-gradient(135deg, rgba(52, 211, 153, 0.2), rgba(16, 185, 129, 0.45))",
  blue: "linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.45))",
  amber: "linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(217, 119, 6, 0.35))",
  red: "linear-gradient(135deg, rgba(248, 113, 113, 0.2), rgba(220, 38, 38, 0.4))"
};

export function MetricsCard({ label, value, description, trend, accent = "green" }: MetricsCardProps) {
  return (
    <div className="card" style={{ position: "relative", overflow: "hidden" }}>
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: "-40% 40% 50% -28%",
          background: accentClass[accent],
          filter: "blur(60px)",
          opacity: 0.6
        }}
      />
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
              color:
                trend.direction === "up"
                  ? "var(--accent)"
                  : trend.direction === "down"
                  ? "#f87272"
                  : "var(--text-muted)"
            }}
          >
            <span aria-hidden>
              {trend.direction === "up" ? "▲" : trend.direction === "down" ? "▼" : "■"}
            </span>
            {trend.label}
          </p>
        )}
      </div>
    </div>
  );
}
