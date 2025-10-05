"use client";

import * as React from "react";
import { collection, limit, onSnapshot, orderBy, query } from "firebase/firestore";
import { db } from "@/lib/firebase/client";

type Props = {
  plantId: string;
  species: string;
  soilMoisture: number;
  wateringFrequency: string;
};

export default function CareTips({ plantId, species, soilMoisture, wateringFrequency }: Props) {
  const [tips, setTips] = React.useState<string[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  const lastTimestampRef = React.useRef<number | null>(null);
  const [latestImageUrl, setLatestImageUrl] = React.useState<string | null>(null);

  const shortenTip = (t: string, maxWords = 8) => {
    const cleaned = (t || "").replace(/^[-•*]\s*/, "").trim();
    const words = cleaned.split(/\s+/);
    return words.slice(0, maxWords).join(" ");
  };

  // Rotating fallback pairs of similar lengths; deterministic per day and plant
  const FALLBACK_SETS: string[][] = [
    ["Water only when topsoil dry", "Bright indirect light; rotate pot"],
    ["Let soil dry between waterings", "Keep in bright indirect light"],
    ["Check topsoil before watering", "Turn pot weekly for even growth"],
    ["Avoid soggy soil; good drainage", "Wipe leaves; remove dead growth"],
    ["Use room‑temp water; mornings", "Keep away from drafts or vents"],
  ];

  const pickFallbackPair = React.useCallback(() => {
    const day = Math.floor(Date.now() / 86400000); // rotate daily
    let sum = 0; for (let i = 0; i < plantId.length; i++) sum += plantId.charCodeAt(i);
    const idx = (day + sum) % FALLBACK_SETS.length;
    return FALLBACK_SETS[idx].map((t) => shortenTip(t));
  }, [plantId]);

  const fetchTips = React.useCallback(async (latestImageUrl?: string | null) => {
    setLoading(true);
    try {
      if (latestImageUrl) {
        // lightweight client log so we can verify calls in the browser
        console.debug("CareTips: requesting tips for", plantId, latestImageUrl);
      }
      const res = await fetch("/api/care-tips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plantId, species, soilMoisture, wateringFrequency, imageUrl: latestImageUrl ?? undefined })
      });
      const data = await res.json();
      if (Array.isArray(data?.tips) && data.tips.length > 0) {
        // show only first 2 care tips and shorten to a single concise line
        setTips(data.tips.slice(0, 2).map((t: string) => shortenTip(t)));
      } else {
        // Fallback: rotate among concise pairs
        setTips(pickFallbackPair());
      }
    } catch {
      setTips(pickFallbackPair());
    } finally {
      setLoading(false);
    }
  }, [plantId, species, soilMoisture, wateringFrequency, pickFallbackPair]);

  React.useEffect(() => {
    const sources = [
      collection(db, "preprocessed_plant_photos"),
      collection(db, "plant_images"),
      collection(db, "preprocessed_plant_pictures")
    ];
    const unsubs = sources.map((ref) =>
      onSnapshot(query(ref, orderBy("timestamp", "desc"), limit(20)), (snap) => {
        const rows = snap.docs.map((d) => d.data() as any).filter((r) => r?.plantId === plantId);
        if (!rows.length) return;
        const newest = rows.sort((a: any, b: any) => {
          const ta: any = a?.timestamp; const da = ta?.toDate ? ta.toDate() : ta?.seconds ? new Date(ta.seconds * 1000) : 0;
          const tb: any = b?.timestamp; const dbb = tb?.toDate ? tb.toDate() : tb?.seconds ? new Date(tb.seconds * 1000) : 0;
          return (dbb as any) - (da as any);
        })[0];
        const ts: any = newest?.timestamp; const d = ts?.toDate ? ts.toDate() : ts?.seconds ? new Date(ts.seconds * 1000) : null;
        const ms = d?.getTime?.() ?? null;
        const latestUrl: string | null = newest?.downloadURL ?? null;
        if (ms && latestUrl && (lastTimestampRef.current === null || ms > lastTimestampRef.current || latestUrl !== latestImageUrl)) {
          lastTimestampRef.current = ms;
          setLatestImageUrl(latestUrl);
          fetchTips(latestUrl);
        }
      })
    );
    return () => unsubs.forEach((u) => u());
  }, [plantId, fetchTips]);

  // Only show care tips when a Firebase image exists
  if (!latestImageUrl) return null;

  if (loading && tips === null) {
    return (
      <div className="care-tips" aria-live="polite">
        <div className="care-tips__title">Care tips</div>
        <div className="care-tips__loading" />
      </div>
    );
  }

  if (!tips || tips.length === 0) return null;

  return (
    <div className="care-tips">
      <div className="care-tips__title">Care tips</div>
      <ul className="care-tips__list">
        {tips.map((t, i) => (
          <li key={i}>{t}</li>
        ))}
      </ul>
    </div>
  );
}


