"use client";

import * as React from "react";

type Props = {
  plantId: string;
};

export function PlantThumb({ plantId }: Props) {
  const src = `/${plantId}.png`;

  return (
    <div className="plant-image-thumb" style={{ border: "none", background: "transparent", overflow: "hidden" }}>
      <img
        src={src}
        alt="Plant"
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block", borderRadius: 12 }}
      />
    </div>
  );
}


