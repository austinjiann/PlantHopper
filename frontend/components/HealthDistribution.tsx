interface HealthDistributionProps {
  healthy: number;
  warning: number;
  critical: number;
}

export function HealthDistribution({ healthy, warning, critical }: HealthDistributionProps) {
  const total = healthy + warning + critical;
  const toPercent = (value: number) => Math.round((value / total) * 100);

  return (
    <div className="card">
      <h3>Plant health</h3>
      <p className="secondary-text">Monitor the overall wellness of the collection.</p>
      <div className="health-distribution">
        <div className="health-ring">{toPercent(healthy)}%</div>
        <div style={{ display: "grid", gap: 8 }}>
          <p style={{ margin: 0 }}>Healthy: {healthy}</p>
          <p style={{ margin: 0 }}>Needs attention: {warning}</p>
          <p style={{ margin: 0 }}>Critical: {critical}</p>
        </div>
      </div>
    </div>
  );
}
