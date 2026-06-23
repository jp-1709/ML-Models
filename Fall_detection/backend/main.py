"""
main.py
─────────────────────────────────────────────────────────────
FastAPI application – the backend entry point.

Endpoints
─────────
GET  /                          Health check
GET  /video_feed                MJPEG stream of annotated frames
GET  /api/status                Current detector state + metrics
GET  /api/events                Paginated event log
POST /api/reset                 Clear event log & reset detector
WS   /ws/alerts                 WebSocket: push alert JSON on fall

Architecture
────────────
A single background thread runs the OpenCV capture loop.
The MJPEG endpoint is a streaming generator that reads the
latest JPEG from a shared buffer (thread-safe via threading.Lock).
WebSocket clients subscribe and receive a JSON push whenever
AlertManager fires an alert.
─────────────────────────────────────────────────────────────
"""

import asyncio
import io
import json
import logging
import threading
import time
import queue
from typing import Any, Dict, List, Set

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

import config
from alert_manager import AlertManager, FallEvent
from fall_detector import FallDetector

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("fall-detector")

# ──────────────────────────────────────────────────────────────
# Global shared state
# ──────────────────────────────────────────────────────────────

# Latest JPEG bytes (protected by _frame_lock)
_latest_frame_bytes: bytes = b""
_frame_lock = threading.Lock()

# Latest metrics dict (for /api/status)
_latest_metrics: Dict[str, Any] = {}
_metrics_lock = threading.Lock()

# Queue to offload heavy processing from WebSocket handler to capture thread
_frame_queue = queue.Queue(maxsize=2)

# WebSocket connection registry
_ws_clients: Set[WebSocket] = set()
_ws_processed_clients: Set[WebSocket] = set()
_ws_lock = asyncio.Lock()

# Asyncio event loop reference (set after app start)
_loop: asyncio.AbstractEventLoop = None  # type: ignore

# Alert / Detector instances
_alert_manager: AlertManager = None   # type: ignore
_fall_detector: FallDetector = None   # type: ignore

# Camera / capture thread
_capture_thread: threading.Thread = None   # type: ignore
_stop_event = threading.Event()


# ──────────────────────────────────────────────────────────────
# Alert callback → WebSocket push
# ──────────────────────────────────────────────────────────────

def _on_alert(event: FallEvent) -> None:
    """Called from the capture thread when a fall is confirmed."""
    payload = json.dumps({"type": "fall_alert", **event.to_dict()})
    log.warning("🚨 Fall detected!  Event #%d", event.event_id)

    if _loop is not None and not _loop.is_closed():
        asyncio.run_coroutine_threadsafe(
            _broadcast_ws(payload), _loop
        )


def _broadcast_processed_frames(jpg_bytes: bytes) -> None:
    """Broadcast processed frame bytes to all connected WebSocket clients."""
    if _loop is not None and not _loop.is_closed():
        asyncio.run_coroutine_threadsafe(
            _broadcast_processed_frames_async(jpg_bytes), _loop
        )

async def _broadcast_processed_frames_async(jpg_bytes: bytes) -> None:
    """Async version of processed frame broadcasting."""
    async with _ws_lock:
        dead: List[WebSocket] = []
        for ws in _ws_processed_clients:
            try:
                await ws.send_bytes(jpg_bytes)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_processed_clients.discard(ws)

async def _broadcast_ws(message: str) -> None:
    """Broadcast a JSON string to all connected WebSocket clients."""
    async with _ws_lock:
        dead: List[WebSocket] = []
        for ws in _ws_clients:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_clients.discard(ws)


# ──────────────────────────────────────────────────────────────
# Capture / detection loop (runs in a daemon thread)
# ──────────────────────────────────────────────────────────────

def _open_capture() -> cv2.VideoCapture:
    source = config.CAMERA_INDEX
    cap = cv2.VideoCapture(source)
    return cap


def _capture_loop() -> None:
    """
    Opens the camera, processes frames, and updates the shared
    JPEG buffer.  Runs until _stop_event is set.
    """
    global _latest_frame_bytes, _latest_metrics

    if config.CAMERA_INDEX == "browser":
        log.info("CAMERA_INDEX is 'browser'. Waiting for frontend WebSocket stream.")
        _serve_no_camera_frame()
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.STREAM_JPEG_QUALITY]
        while not _stop_event.is_set():
            try:
                frame = _frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            result = _fall_detector.process_frame(frame)
            _, jpg = cv2.imencode(".jpg", result.annotated_frame, encode_params)
            with _frame_lock:
                _latest_frame_bytes = jpg.tobytes()

            # ── Broadcast processed frame to WebSocket clients ───────
            _broadcast_processed_frames(jpg.tobytes())

            metrics = {
                **_fall_detector.metrics,
                "state":        result.state.name,
                "alert_active": _alert_manager.alert_active,
                "alert_status": _alert_manager.get_status(),
            }
            with _metrics_lock:
                _latest_metrics = metrics
        return

    cap = _open_capture()
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          config.TARGET_FPS)

    if not cap.isOpened():
        log.error("Cannot open camera source %s", str(config.CAMERA_INDEX))
        _serve_no_camera_frame()

        while not _stop_event.is_set():
            time.sleep(1.0)
            cap = _open_capture()
            if cap.isOpened():
                log.info("Camera source opened on retry: %s", str(config.CAMERA_INDEX))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
                cap.set(cv2.CAP_PROP_FPS,          config.TARGET_FPS)
                break
            _serve_no_camera_frame()

        if not cap.isOpened():
            return

    log.info("Camera opened: %dx%d @ %d fps",
             config.FRAME_WIDTH, config.FRAME_HEIGHT, config.TARGET_FPS)

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.STREAM_JPEG_QUALITY]

    while not _stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            log.warning("Frame grab failed – retrying …")
            time.sleep(0.05)
            continue

        # ── Run detector ───────────────────────────────────────
        result = _fall_detector.process_frame(frame)

        # ── Encode annotated frame to JPEG ─────────────────────
        _, jpg = cv2.imencode(".jpg", result.annotated_frame, encode_params)
        jpg_bytes = jpg.tobytes()

        with _frame_lock:
            _latest_frame_bytes = jpg_bytes

        # ── Broadcast processed frame to WebSocket clients ───────
        _broadcast_processed_frames(jpg_bytes)

        # ── Update metrics snapshot ────────────────────────────
        metrics = {
            **_fall_detector.metrics,
            "state":        result.state.name,
            "alert_active": _alert_manager.alert_active,
            "alert_status": _alert_manager.get_status(),
        }
        with _metrics_lock:
            _latest_metrics = metrics

    cap.release()
    log.info("Capture loop exited.")


def _serve_no_camera_frame() -> None:
    """
    If camera cannot be opened, push a synthetic error frame
    into the buffer so the MJPEG endpoint still responds.
    """
    frame = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
    cv2.putText(
        frame,
        "Camera not available",
        (40, config.FRAME_HEIGHT // 2),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 80, 255), 2,
    )
    _, jpg = cv2.imencode(".jpg", frame)
    with _frame_lock:
        global _latest_frame_bytes
        _latest_frame_bytes = jpg.tobytes()


# ──────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Fall Detection API",
    description="Real-time fall detection with MHI + ellipse + pose estimation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────
# Lifecycle
# ──────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event() -> None:
    global _alert_manager, _fall_detector, _capture_thread, _loop

    _loop = asyncio.get_running_loop()

    _alert_manager = AlertManager(on_alert=_on_alert)
    _fall_detector = FallDetector(_alert_manager)

    _stop_event.clear()
    _capture_thread = threading.Thread(
        target=_capture_loop, daemon=True, name="CaptureThread"
    )
    _capture_thread.start()
    log.info("Fall Detection backend started.")


def get_camera_devices() -> Dict[str, Any]:
    """Detect available OpenCV video capture devices."""
    available_cameras = []
    try:
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                fps = cap.get(cv2.CAP_PROP_FPS) or 0

                available_cameras.append({
                    "id": i,
                    "name": f"Camera {i}",
                    "resolution": f"{width}x{height}",
                    "fps": fps if fps > 0 else "Unknown",
                })
                cap.release()
    except Exception as e:
        log.error("Camera detection error: %s", str(e))
        return {"success": False, "error": str(e)}

    return {"success": True, "cameras": available_cameras}


@app.on_event("shutdown")
async def shutdown_event() -> None:
    _stop_event.set()
    if _capture_thread:
        _capture_thread.join(timeout=3)
    if _fall_detector:
        _fall_detector._pose.close()
    log.info("Fall Detection backend stopped.")


# ──────────────────────────────────────────────────────────────
# HTTP endpoints
# ──────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def root() -> Dict[str, str]:
    return {"status": "ok", "service": "fall-detection-api"}


async def _mjpeg_generator():
    """Async generator that yields MJPEG boundary-framed JPEG data."""
    boundary = b"--frame\r\n"
    header   = b"Content-Type: image/jpeg\r\n\r\n"
    while True:
        with _frame_lock:
            data = _latest_frame_bytes

        if data:
            yield boundary + header + data + b"\r\n"
        else:
            await asyncio.sleep(0.01)

        # ~30 fps max for MJPEG consumers
        await asyncio.sleep(1 / 30)


# Global detector instance to maintain state across API calls
_global_detector = None

@app.post("/detect", tags=["api"])
async def detect_fall(file: UploadFile = File(...)) -> JSONResponse:
    """
    Analyze a single image for fall detection.
    Returns detection results and metrics.
    """
    global _global_detector
    
    if _fall_detector is None:
        return JSONResponse(
            content={"error": "Detector not initialized"}, 
            status_code=503
        )
    
    # Use global detector for state continuity
    if _global_detector is None:
        _global_detector = _fall_detector
    
    try:
        # Read image bytes
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return JSONResponse(
                content={"error": "Invalid image format"}, 
                status_code=400
            )
        
        # Resize frame to expected dimensions
        frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))
        
        # Process frame with stateful detector
        result = _global_detector.process_frame(frame)
        
        # Create simple response without complex FrameResult access
        detections = []
        
        # Add person detection if motion detected
        if result.c_motion > 30:
            detections.append({
                "box": [100, 100, 540, 380],  # Default box
                "label": "person",
                "confidence": 0.8
            })
        
        # Add fall detection if state indicates fall
        if str(result.state.name) == "FALL_CONFIRMED":
            detections.append({
                "box": [100, 100, 540, 380],  # Default box
                "label": "fall",
                "confidence": max(0.8, result.pose_score)
            })
        
        # Return simple response like helmet detection
        return JSONResponse(content={
            "detections": detections,
            "helmet_count": 0,
            "no_helmet_count": 1 if str(result.state.name) == "FALL_CONFIRMED" else 0,
            "person_count": 1 if result.c_motion > 30 else 0,
            "fall_detected": str(result.state.name) == "FALL_CONFIRMED",
            "confidence": result.pose_score,
            "state": str(result.state.name),
            "metrics": {
                "c_motion": result.c_motion,
                "sigma_theta": result.sigma_theta,
                "sigma_rho": result.sigma_rho,
                "pose_score": result.pose_score,
                "immobility_secs": result.immobility_secs
            }
        })
        
    except Exception as e:
        log.error(f"Detection error: {str(e)}")
        return JSONResponse(
            content={"error": f"Detection failed: {str(e)}"}, 
            status_code=500
        )

@app.get("/video_feed", tags=["stream"])
async def video_feed() -> StreamingResponse:
    """MJPEG stream of the annotated camera feed."""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/status", tags=["api"])
async def get_status() -> JSONResponse:
    """
    Returns the current detector state and live metrics.
    Poll this at ~1 Hz to drive dashboard gauges.
    """
    with _metrics_lock:
        data = dict(_latest_metrics)
    return JSONResponse(content=data)


@app.get("/api/events", tags=["api"])
async def get_events(limit: int = 20) -> JSONResponse:
    """Returns the most recent `limit` fall events (newest first)."""
    events = _alert_manager.get_log()[:limit] if _alert_manager else []
    return JSONResponse(content={"events": events, "total": len(events)})


@app.get("/api/cameras", tags=["api"])
async def get_cameras() -> JSONResponse:
    """Returns list of available camera devices."""
    return JSONResponse(content=get_camera_devices())

@app.post("/api/reset", tags=["api"])
async def reset_system() -> JSONResponse:
    """
    Clears the event log and resets detector state.
    Useful for testing / after a false positive.
    """
    global _alert_manager, _fall_detector

    _stop_event.set()
    if _capture_thread:
        _capture_thread.join(timeout=2)

    _alert_manager = AlertManager(on_alert=_on_alert)
    _fall_detector = FallDetector(_alert_manager)

    _stop_event.clear()
    t = threading.Thread(target=_capture_loop, daemon=True, name="CaptureThread")
    t.start()

    return JSONResponse(content={"status": "reset complete"})


# ──────────────────────────────────────────────────────────────
# WebSocket endpoint
# ──────────────────────────────────────────────────────────────

@app.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket) -> None:
    """
    WebSocket endpoint.  Connected clients receive a JSON push
    every time a fall is detected.

    Message schema:
    {
      "type": "fall_alert",
      "event_id": 1,
      "timestamp": 1700000000.0,
      "iso_time": "2024-11-14 12:00:00",
      "c_motion": 86.5,
      "sigma_theta": 19.2,
      "sigma_rho": 0.64,
      "pose_score": 0.73,
      "method": "classical+pose"
    }
    """
    await ws.accept()
    async with _ws_lock:
        _ws_clients.add(ws)
    log.info("WS client connected. Total: %d", len(_ws_clients))

    try:
        # Keep the connection alive; we only push, never pull.
        while True:
            # Send periodic heartbeat so clients know we're alive
            await asyncio.sleep(5)
            try:
                await ws.send_text(json.dumps({"type": "heartbeat"}))
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        async with _ws_lock:
            _ws_clients.discard(ws)
        log.info("WS client disconnected. Total: %d", len(_ws_clients))

@app.websocket("/ws/processed_frames")
async def websocket_processed_frames(ws: WebSocket) -> None:
    """
    WebSocket endpoint to stream processed frames with AI annotations.
    """
    await ws.accept()
    log.info("Processed frames client connected.")
    
    async with _ws_lock:
        _ws_processed_clients.add(ws)
    
    try:
        while True:
            # Send periodic heartbeat
            await asyncio.sleep(5)
            try:
                await ws.send_text(json.dumps({"type": "heartbeat"}))
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        async with _ws_lock:
            _ws_processed_clients.discard(ws)
        log.info("Processed frames client disconnected.")

@app.websocket("/ws/video_stream")
async def websocket_video_stream(ws: WebSocket) -> None:
    """
    WebSocket endpoint to receive raw JPEG frames from the browser's webcam.
    """
    await ws.accept()
    log.info("Browser video stream connected.")
    try:
        while True:
            bytes_data = await ws.receive_bytes()
            nparr = np.frombuffer(bytes_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None and _fall_detector is not None:
                try:
                    _frame_queue.put(frame, block=False)
                except queue.Full:
                    pass  # drop frame if falling behind

    except WebSocketDisconnect:
        log.info("Browser video stream disconnected.")


# ──────────────────────────────────────────────────────────────
# Dev runner
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
