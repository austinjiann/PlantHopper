"use client";

import * as React from "react";
import { collection, limit, onSnapshot, orderBy, query, where } from "firebase/firestore";
import { db } from "@/lib/firebase/client";

type Props = {
  plantId: string;
};

export function PlantThumb({ plantId }: Props) {
  const [url, setUrl] = React.useState<string | null>(null);

  React.useEffect(() => {
    const imagesRef = collection(db, "plant_images");
    const primary = query(imagesRef, where("plantId", "==", plantId), orderBy("timestamp", "desc"), limit(1));

    // First try the indexed query
    const unsub = onSnapshot(
      primary,
      (snap) => {
        if (!snap.empty) {
          setUrl((snap.docs[0].data() as any)?.downloadURL || null);
        } else {
          setUrl(null);
        }
      },
      // If index is missing, fall back to orderBy only and filter client-side
      () => {
        const fallback = query(imagesRef, orderBy("timestamp", "desc"), limit(20));
        const unsub2 = onSnapshot(fallback, (snap2) => {
          const first = snap2.docs.map((d) => d.data() as any).find((d) => d?.plantId === plantId);
          setUrl(first?.downloadURL || null);
        });
        // Replace unsub with fallback unsubscriber
        return () => unsub2();
      }
    );
    return () => unsub();
  }, [plantId]);

  const fallbackSrc = `/${plantId}.png`;

  return (
    <div className="plant-image-thumb" style={{ border: "none", background: "transparent", overflow: "hidden" }}>
      <img
        src={url ?? fallbackSrc}
        alt="Plant"
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", borderRadius: 12 }}
      />
    </div>
  );
}


