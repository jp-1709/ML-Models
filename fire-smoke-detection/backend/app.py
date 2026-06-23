"""
Fire & Smoke Detection API Server
==================================
Senior AI/ML Engineer Implementation
Architecture: YOLOv8 + HSV Color Ensemble + CLAHE Enhancement
Target Accuracy: >95%
"""

import os
import io
import cv2
import time
import base64
import logging
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from detector import FireSmokeDetector

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ─── App Init ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─── Detector Singleton ───────────────────────────────────────────────────────
detector = FireSmokeDetector(
    model_path=os.environ.get("MODEL_PATH", "models/fire_smoke_yolov8.pt"),
    confidence=float(os.environ.get("CONF_THRESHOLD", "0.45")),
    iou=float(os.environ.get("IOU_THRESHOLD", "0.45")),
    device=os.environ.get("DEVICE", "cpu"),
)

# ─── Stats Tracker ────────────────────────────────────────────────────────────
stats = {
    "total_frames": 0,
    "fire_detections": 0,
    "smoke_detections": 0,
    "alerts_triggered": 0,
    "session_start": time.time(),
    "last_detection_time": None,
    "fps_history": [],
}


def decode_frame(b64_data: str) -> np.ndarray:
    """Decode base64 image to OpenCV BGR frame."""
    if "," in b64_data:
        b64_data = b64_data.split(",")[1]
    img_bytes = base64.b64decode(b64_data)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


def encode_frame(frame: np.ndarray) -> str:
    """Encode OpenCV BGR frame to base64 JPEG."""
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "operational",
        "model_loaded": detector.is_loaded,
        "device": detector.device,
        "uptime_seconds": round(time.time() - stats["session_start"], 1),
    })


@app.route("/api/detect", methods=["POST"])
def detect():
    """
    Main detection endpoint.
    Accepts: { "frame": "<base64_image>", "timestamp": <ms> }
    Returns: detections, annotated frame, risk level, stats
    """
    t0 = time.time()

    try:
        body = request.get_json(force=True)
        if not body or "frame" not in body:
            return jsonify({"error": "Missing 'frame' field"}), 400

        # Decode incoming frame
        frame = decode_frame(body["frame"])
        if frame is None:
            return jsonify({"error": "Invalid image data"}), 400

        # Run detection pipeline
        result = detector.detect(frame)

        # Update global stats
        stats["total_frames"] += 1
        has_fire = any(d["class"] == "fire" for d in result["detections"])
        has_smoke = any(d["class"] == "smoke" for d in result["detections"])

        if has_fire:
            stats["fire_detections"] += 1
        if has_smoke:
            stats["smoke_detections"] += 1
        if result["alert"]:
            stats["alerts_triggered"] += 1
            stats["last_detection_time"] = time.time()

        # FPS tracking (rolling window of 30)
        elapsed = time.time() - t0
        stats["fps_history"].append(elapsed)
        if len(stats["fps_history"]) > 30:
            stats["fps_history"].pop(0)

        avg_latency = np.mean(stats["fps_history"]) if stats["fps_history"] else 0
        current_fps = round(1 / avg_latency, 1) if avg_latency > 0 else 0

        return jsonify({
            "detections": result["detections"],
            "annotated_frame": encode_frame(result["annotated_frame"]),
            "risk_level": result["risk_level"],
            "alert": result["alert"],
            "confidence_avg": result["confidence_avg"],
            "processing_ms": round((time.time() - t0) * 1000, 1),
            "fps": current_fps,
            "stats": {
                "total_frames": stats["total_frames"],
                "fire_detections": stats["fire_detections"],
                "smoke_detections": stats["smoke_detections"],
                "alerts_triggered": stats["alerts_triggered"],
                "session_minutes": round((time.time() - stats["session_start"]) / 60, 1),
                "last_detection": stats["last_detection_time"],
            }
        })

    except Exception as e:
        logger.error(f"Detection error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/reset", methods=["POST"])
def reset_stats():
    """Reset session statistics."""
    stats.update({
        "total_frames": 0,
        "fire_detections": 0,
        "smoke_detections": 0,
        "alerts_triggered": 0,
        "session_start": time.time(),
        "last_detection_time": None,
        "fps_history": [],
    })
    return jsonify({"status": "reset", "timestamp": time.time()})


@app.route("/api/model/info", methods=["GET"])
def model_info():
    """Return model metadata."""
    return jsonify(detector.get_info())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    logger.info(f"🔥 Fire & Smoke Detection API starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
