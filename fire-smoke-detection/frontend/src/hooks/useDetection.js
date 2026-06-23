import { useState, useCallback, useEffect, useRef } from "react";

/**
 * useDetection — API communication hook
 * ======================================
 * Sends captured frames to the Flask detection API and manages state.
 * Polls /api/health every 5 seconds.
 */
export default function useDetection({ apiUrl, sensitivity }) {
  const [detectionResult, setDetectionResult] = useState(null);
  const [stats,           setStats]           = useState(null);
  const [health,          setHealth]          = useState(null);
  const inFlightRef = useRef(false);   // prevent overlapping requests

  // Health polling
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/health`, {
          signal: AbortSignal.timeout(3000),
        });
        if (res.ok) setHealth(await res.json());
        else        setHealth(null);
      } catch {
        setHealth(null);
      }
    };
    poll();
    const timer = setInterval(poll, 5000);
    return () => clearInterval(timer);
  }, [apiUrl]);

  const sendFrame = useCallback(
    async (dataUrl) => {
      if (inFlightRef.current) return;   // skip if previous request still pending
      inFlightRef.current = true;

      try {
        const res = await fetch(`${apiUrl}/api/detect`, {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({
            frame:      dataUrl,
            timestamp:  Date.now(),
            sensitivity,
          }),
          signal: AbortSignal.timeout(5000),
        });

        if (!res.ok) {
          console.warn(`Detection API ${res.status}`);
          return;
        }

        const data = await res.json();
        setDetectionResult(data);
        if (data.stats) setStats(data.stats);
      } catch (err) {
        if (err.name !== "AbortError") {
          console.error("Detection request failed:", err);
        }
      } finally {
        inFlightRef.current = false;
      }
    },
    [apiUrl, sensitivity]
  );

  const resetStats = useCallback(async () => {
    try {
      await fetch(`${apiUrl}/api/stats/reset`, { method: "POST" });
      setStats(null);
      setDetectionResult(null);
    } catch (err) {
      console.error("Reset failed:", err);
    }
  }, [apiUrl]);

  return { detectionResult, stats, health, sendFrame, resetStats };
}
