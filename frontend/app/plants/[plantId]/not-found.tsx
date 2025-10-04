import Link from "next/link";

export default function PlantNotFound() {
  return (
    <main className="detail-main">
      <div className="detail-card">
        <h1>Plant not found</h1>
        <p className="secondary-text">
          We could not locate this plant in the monitoring fleet. Return to the dashboard and choose a
          plant from the list.
        </p>
        <Link href="/" className="button" style={{ width: "fit-content" }}>
          Back to dashboard
        </Link>
      </div>
    </main>
  );
}
