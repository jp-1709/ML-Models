import { useRef, useState, useCallback } from "react";

/**
 * useCamera — WebRTC hook
 * ========================
 * Captures video from the LOCAL browser's camera (laptop webcam).
 * This works even when the React app is served from a remote SSH server,
 * because getUserMedia() is always executed in the LOCAL browser context.
 *
 * SSH setup:
 *   ssh -L 3000:localhost:3000 -L 5050:localhost:5050 user@server
 *   Then open http://localhost:3000 in your LOCAL browser.
 *
 * The browser will prompt for camera permissions on the LOCAL machine.
 */
export default function useCamera() {
  const videoRef  = useRef(null);
  const streamRef = useRef(null);

  const [cameraError,  setCameraError]  = useState(null);
  const [cameraActive, setCameraActive] = useState(false);

  const startCamera = useCallback(async () => {
    setCameraError(null);
    try {
      const constraints = {
        video: {
          width:     { ideal: 1280 },
          height:    { ideal: 720 },
          frameRate: { ideal: 30 },
          // Prefer front-facing on mobile; rear on desktop has better scene coverage
          facingMode: "environment",
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setCameraActive(true);
    } catch (err) {
      const msg =
        err.name === "NotAllowedError"
          ? "Camera permission denied. Allow access in browser settings."
          : err.name === "NotFoundError"
          ? "No camera device found on this machine."
          : err.name === "NotReadableError"
          ? "Camera is in use by another application."
          : `Camera error: ${err.message}`;

      setCameraError(msg);
      setCameraActive(false);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  }, []);

  return { videoRef, startCamera, stopCamera, cameraError, cameraActive };
}
