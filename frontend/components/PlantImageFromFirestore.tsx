"use client";

import * as React from "react";
import { collection, limit, onSnapshot, orderBy, query } from "firebase/firestore";
import { db } from "@/lib/firebase/client";

type Props = {
  plantId: string;
};

export default function PlantImageFromFirestore({ plantId }: Props) {
  const [imageUrl, setImageUrl] = React.useState<string | null>(null);
  const [alt, setAlt] = React.useState<string | null>(null);
  const latestTsRef = React.useRef<number>(0);

  React.useEffect(() => {
    latestTsRef.current = 0; // reset when plant changes
    // Strategy: avoid composite index by reading recent docs and filtering client-side.
    const sources = [
      collection(db, "preprocessed_plant_photos"),
      collection(db, "plant_images"),
      collection(db, "preprocessed_plant_pictures")
    ];

    const unsubs = sources.map((ref) =>
      onSnapshot(query(ref, orderBy("timestamp", "desc"), limit(20)), (snap) => {
        const rows = snap.docs.map((d) => d.data() as any).filter((r) => r?.plantId === plantId);
        if (!rows.length) return;
        // Choose newest by timestamp
        const pick = rows
          .map((r) => ({
            url: r?.downloadURL as string | undefined,
            ts: (() => {
              const t: any = r?.timestamp;
              const date = t?.toDate ? t.toDate() : t?.seconds ? new Date(t.seconds * 1000) : null;
              return date?.getTime?.() ?? 0;
            })()
          }))
          .sort((a, b) => b.ts - a.ts)[0];
        if (pick?.url && pick.ts > latestTsRef.current) {
          latestTsRef.current = pick.ts;
          // Add cache-busting param so repeated path like plant1.jpg refreshes when updated
          const bust = pick.url + (pick.url.includes("?") ? "&" : "?") + "ts=" + pick.ts;
          setImageUrl(bust);
          setAlt("Plant");
        }
      })
    );
    return () => unsubs.forEach((u) => u());
  }, [plantId]);

  const fallbackSrc = `/${plantId}.png`;
  const displayAlt = alt ?? "Plant";

  return (
    <div className="detail-image-shell">
      <div className="detail-image-frame">
        <img src={imageUrl ?? fallbackSrc} alt={displayAlt} className="detail-plant-image" />
      </div>
    </div>
  );
}


