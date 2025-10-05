"use client";

import * as React from "react";
import { collection, limit, onSnapshot, orderBy, query, where } from "firebase/firestore";
import { db } from "@/lib/firebase/client";

type Props = {
  plantId: string;
};

export default function PlantImageFromFirestore({ plantId }: Props) {
  const [imageUrl, setImageUrl] = React.useState<string | null>(null);
  const [alt, setAlt] = React.useState<string | null>(null);

  React.useEffect(() => {
    const imagesRef = collection(db, "plant_images");
    const primary = query(
      imagesRef,
      where("plantId", "==", plantId),
      orderBy("timestamp", "desc"),
      limit(1)
    );
    const unsub = onSnapshot(
      primary,
      (snap) => {
        if (!snap.empty) {
          const d = snap.docs[0].data() as any;
          setImageUrl(d?.downloadURL || null);
          const speciesCommon = d?.species?.common as string | undefined;
          setAlt(speciesCommon ?? "Plant");
        } else {
          setImageUrl(null);
          setAlt(null);
        }
      },
      // Fallback when index is missing: grab recent docs and filter in client
      () => {
        const fallback = query(imagesRef, orderBy("timestamp", "desc"), limit(20));
        const unsub2 = onSnapshot(fallback, (snap2) => {
          const first = snap2.docs.map((d) => d.data() as any).find((d) => d?.plantId === plantId);
          if (first) {
            setImageUrl(first?.downloadURL || null);
            setAlt((first?.species?.common as string | undefined) ?? "Plant");
          }
        });
        return () => unsub2();
      }
    );
    return () => unsub();
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


