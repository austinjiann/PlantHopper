"use client";

import { useState } from "react";
import { doc, updateDoc } from "firebase/firestore";
import { db } from "@/lib/firebase/client";

interface WaterPlantButtonProps {
  plantId: string;
  variant?: "default" | "inline";
  targetDocId?: string; // optional override for Firestore doc id (e.g., "plant1")
  command?: string; // defaults to "water"
  label?: string; // defaults to "Water Plant"
}

type FeedbackState = {
  status: "success" | "error";
  message: string;
};

export function WaterPlantButton({ plantId, variant = "default", targetDocId, command = "water", label }: WaterPlantButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const handleWaterPlant = async () => {
    setIsSubmitting(true);
    setFeedback(null);

    try {
      const docId = targetDocId ?? plantId;
      const plantRef = doc(db, "plants", docId);
      await updateDoc(plantRef, { command });
      const successText = command === "water" ? "Watering command sent!" : "Command sent!";
      setFeedback({ status: "success", message: successText });
    } catch (error) {
      console.error("Failed to send watering command", error);
      setFeedback({ status: "error", message: "Could not send watering command. Try again." });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={variant === "inline" ? undefined : "water-action"}>
      <button
        type="button"
        className={variant === "inline" ? "water-button water-button--inline" : "water-button"}
        onClick={handleWaterPlant}
        disabled={isSubmitting}
        aria-label={command === "water" ? "Send watering command" : `Send ${command} command`}
      >
        {isSubmitting ? (
          <>
            <span className="water-button__spinner" aria-hidden />
            {command === "water" ? "Watering..." : "Sending..."}
          </>
        ) : (
          label ?? (command === "water" ? "Water Plant" : "Send Command")
        )}
      </button>
      {variant !== "inline" && (
        <div className="water-feedback" aria-live="polite" role="status">
          {feedback && (
            <span className={feedback.status === "success" ? "water-feedback__message water-feedback__message--success" : "water-feedback__message water-feedback__message--error"}>
              {feedback.message}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
