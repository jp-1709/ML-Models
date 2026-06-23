"""
FastAPI backend for fall detection service
Integrates with YOLO11 fall detector
"""

import os
import io
import base64
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import sys

# Add parent directory to path to import fall detector
sys.path.append(str(Path(__file__).parent.parent))
from fall_detector import FallDetector

# Global detector instance
detector = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the fall detector on startup"""
    global detector
    try:
        # Use the FallSafe model we downloaded
        model_path = Path(__file__).parent.parent / "model.pt"
        print(f"[INFO] Initializing fall detector with FallSafe model: {model_path}")
        detector = FallDetector(str(model_path), conf=0.1)  # Very low confidence for testing
        print("✅ Fall detector initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        detector = None
    yield

app = FastAPI(title="Fall Detection API", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DetectionResult(BaseModel):
    label: str
    confidence: float
    box: List[int]  # [x1, y1, x2, y2]

class DetectionResponse(BaseModel):
    success: bool
    detections: List[DetectionResult]
    fall_count: int
    slip_count: int
    person_count: int
    image_width: int
    image_height: int
    message: str

@app.get("/")
async def root():
    """Health check endpoint"""
    print("[DEBUG] Root endpoint accessed")
    return {"status": "healthy", "detector_loaded": detector is not None}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    print("[DEBUG] Health endpoint accessed")
    return {
        "status": "healthy" if detector else "unhealthy",
        "detector_loaded": detector is not None,
        "model_classes": list(detector.class_names.values()) if detector else []
    }

def decode_image(image_data: bytes) -> np.ndarray:
    """Decode image bytes to OpenCV format"""
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img

def encode_image_to_base64(image: np.ndarray) -> str:
    """Encode OpenCV image to base64 string"""
    _, buffer = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return img_base64

@app.post("/detect", response_model=DetectionResponse)
async def detect_falls(file: UploadFile = File(...)):
    """
    Detect falls in uploaded image
    Returns detection results and annotated image
    """
    print(f"[DEBUG] Received detection request for file: {file.filename}")
    print(f"[DEBUG] Content type: {file.content_type}")
    print(f"[DEBUG] File size: {file.size if hasattr(file, 'size') else 'Unknown'}")
    
    if not detector:
        print("[DEBUG] Detector not initialized")
        raise HTTPException(status_code=503, detail="Fall detector not initialized")
    
    if not file.content_type.startswith('image/'):
        print(f"[DEBUG] Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read and decode image
        image_data = await file.read()
        print(f"[DEBUG] Read {len(image_data)} bytes of image data")
        
        img = decode_image(image_data)
        print(f"[DEBUG] Decoded image shape: {img.shape}")
        
        # Run detection
        detections = detector.detect(img)
        print(f"[DEBUG] Found {len(detections)} detections")
        
        # Process results
        fall_count = sum(1 for d in detections if d["label"] == "fall")
        slip_count = sum(1 for d in detections if d["label"] == "slip")
        person_count = sum(1 for d in detections if d["label"] == "person")
        
        # Convert to response format
        detection_results = []
        for det in detections:
            detection_results.append(DetectionResult(
                label=det["label"],
                confidence=det["conf"],
                box=list(det["box"])
            ))
        
        # Annotate image
        annotated_img = detector.draw(img, detections)
        annotated_base64 = encode_image_to_base64(annotated_img)
        
        # Determine status message
        if fall_count > 0:
            message = f"🚨 {fall_count} fall(s) detected!"
        elif slip_count > 0:
            message = f"⚠️ {slip_count} slip(s) detected!"
        elif person_count > 0:
            message = "✅ No falls detected, people standing normally"
        else:
            message = "🔍 No persons detected"
        
        print(f"[DEBUG] Detection complete: {fall_count} falls, {slip_count} slips, {person_count} persons")
        print(f"[DEBUG] Sending response with {len(detection_results)} detections")
        
        return DetectionResponse(
            success=True,
            detections=detection_results,
            fall_count=fall_count,
            slip_count=slip_count,
            person_count=person_count,
            image_width=img.shape[1],
            image_height=img.shape[0],
            message=message
        )
        
    except Exception as e:
        print(f"[DEBUG] Detection error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@app.post("/detect-visual")
async def detect_falls_visual(file: UploadFile = File(...)):
    """
    Detect falls and return annotated image as base64
    """
    if not detector:
        raise HTTPException(status_code=503, detail="Fall detector not initialized")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        image_data = await file.read()
        img = decode_image(image_data)
        detections = detector.detect(img)
        annotated_img = detector.draw(img, detections)
        annotated_base64 = encode_image_to_base64(annotated_img)
        
        return {
            "success": True,
            "annotated_image": f"data:image/jpeg;base64,{annotated_base64}",
            "detections_count": len(detections)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@app.post("/emergency-alert")
async def emergency_alert(file: UploadFile = File(...)):
    """
    Emergency detection endpoint with higher priority
    """
    # Similar to detect but with higher sensitivity
    if not detector:
        raise HTTPException(status_code=503, detail="Fall detector not initialized")
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        image_data = await file.read()
        img = decode_image(image_data)
        
        # Use lower confidence threshold for emergency detection
        original_conf = detector.conf
        detector.conf = 0.3  # Lower threshold for emergency
        
        detections = detector.detect(img)
        
        # Restore original confidence
        detector.conf = original_conf
        
        fall_count = sum(1 for d in detections if d["label"] == "fall")
        slip_count = sum(1 for d in detections if d["label"] == "slip")
        
        # Emergency response
        is_emergency = fall_count > 0 or slip_count > 0
        
        return {
            "emergency": is_emergency,
            "fall_count": fall_count,
            "slip_count": slip_count,
            "message": "🚨 EMERGENCY: Fall detected!" if is_emergency else "✅ No emergency detected",
            "timestamp": str(np.datetime64('now'))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emergency detection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
