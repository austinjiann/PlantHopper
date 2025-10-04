interface TimelineItem {
  plantId: string;
  plantName: string;
  time: string;
  action: string;
}

interface WateringTimelineProps {
  items: TimelineItem[];
}

export function WateringTimeline({ items }: WateringTimelineProps) {
  return (
    <div className="card">
      <h3>Upcoming automation</h3>
      <p className="secondary-text">Confirm the next queued actions for the watering robots.</p>
      <div className="timeline">
        {items.map((item) => (
          <div key={item.plantId} className="timeline-item">
            <div className="timeline-plant">
              <span style={{ fontSize: "1.2rem" }}>🤖</span>
              <div>
                <div>{item.plantName}</div>
                <p className="secondary-text" style={{ fontSize: "0.8rem" }}>{item.action}</p>
              </div>
            </div>
            <span className="timeline-time">{item.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
