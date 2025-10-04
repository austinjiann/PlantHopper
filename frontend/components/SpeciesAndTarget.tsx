"use client";

import * as React from "react";
import { collection, limit, onSnapshot, orderBy, query, where } from "firebase/firestore";
import { db } from "@/lib/firebase/client";

type Props = {
  plantId: string;
  fallbackTarget: number;
};

export default function SpeciesAndTarget({ plantId, fallbackTarget }: Props) {
  const [speciesCommon, setSpeciesCommon] = React.useState<string | null>(null);
  const [speciesScientific, setSpeciesScientific] = React.useState<string | null>(null);
  const [target, setTarget] = React.useState<number | null>(null);

  React.useEffect(() => {
    const imagesRef = collection(db, "plant_images");
    const q = query(
      imagesRef,
      where("plantId", "==", plantId),
      orderBy("timestamp", "desc"),
      limit(1)
    );
    const unsub = onSnapshot(q, (snap) => {
      if (!snap.empty) {
        const d = snap.docs[0].data() as any;
        setSpeciesCommon(d?.species?.common ?? null);
        setSpeciesScientific(d?.species?.scientific ?? null);
        setTarget(typeof d?.targetMoisture === "number" ? d.targetMoisture : null);
      } else {
        setSpeciesCommon(null);
        setSpeciesScientific(null);
        setTarget(null);
      }
    });
    return () => unsub();
  }, [plantId]);

  return (
    <>
      {speciesCommon && (
        <div className="species-info">
          <div className="species-common">{speciesCommon}</div>
          {speciesScientific && <div className="species-scientific">{speciesScientific}</div>}
        </div>
      )}
      <div className="detail-hero-metric">
        <span className="metric-label">Target</span>
        <span className="metric-value">{(target ?? fallbackTarget)}%</span>
      </div>
    </>
  );
}


