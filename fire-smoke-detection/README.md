# 🔥 PYREGUARD — Industrial Fire & Smoke Detection System

> **YOLOv8 + HSV Colour Ensemble · CLAHE Enhanced · >95% Accuracy Target**
> Built by Senior AI/ML + Full-Stack Engineer | React · Flask · OpenCV

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOCAL LAPTOP                         REMOTE SSH SERVER             │
│                                                                     │
│  ┌────────────┐   SSH Tunnel   ┌─────────────────────────────────┐ │
│  │  Browser   │◄─────────────►│  Vite Dev Server  :3000          │ │
│  │  (webcam)  │  :3000,:5050  │  Flask API        :5050          │ │
│  └────────────┘               │                                  │ │
│       │                       │  ┌──────────────────────────┐   │ │
│  getUserMedia()               │  │  Detection Pipeline       │   │ │
│  (local camera)               │  │  1. CLAHE preprocess      │   │ │
│       │ base64 frame          │  │  2. YOLOv8l inference     │   │ │
│       └──────────────────────►│  │  3. HSV colour heuristic  │   │ │
│                               │  │  4. Ensemble fusion + NMS │   │ │
│  ◄────────────────────────────│  │  5. Temporal smoothing    │   │ │
│   annotated frame + JSON      │  └──────────────────────────┘   │ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Detection Pipeline (>95% Accuracy)

### Stage 1 — Preprocessing (CLAHE + Denoising)
- **Bilateral filter** — edge-preserving noise reduction
- **CLAHE** (Contrast Limited Adaptive Histogram Equalization) on LAB L-channel
- **Gamma correction** — improves shadow/highlight detection
- Reference: Khan et al. IEEE TII 2019

### Stage 2 — YOLOv8l Deep Learning
- Base: `yolov8l.pt` (large variant, best accuracy/speed balance)
- Fine-tuned on Roboflow [fire-smoke-det v6](https://universe.roboflow.com/reyzi916/fire-smoke-det/dataset/6)
- Training augmentations: mosaic, mixup, copy-paste, HSV jitter, affine transforms
- Input: 640×640 · Confidence: 0.45 · IoU NMS: 0.45

### Stage 3 — HSV Colour Heuristics
- **Fire** — warm reds/oranges (Hue 0–18° + 170–180°, high saturation/value)
- **Smoke** — near-grey (low saturation, mid-high value), morphologically filtered
- Morphological opening/closing removes noise, gap-fills regions

### Stage 4 — Weighted Ensemble Fusion
- YOLO + HSV agreement → confidence boost (×1.15, capped 0.99)
- **Soft-NMS** — suppresses duplicates while preserving secondary detections
- Sources tagged: `yolo`, `hsv`, `ens` (both agree)

### Stage 5 — Temporal Smoothing
- Rolling window (5 frames) majority-vote
- Eliminates single-frame false positives
- Fire/smoke confirmed independently

---

## Quick Start

### Prerequisites

| Tool       | Version  | Notes                        |
|------------|----------|------------------------------|
| Python     | ≥ 3.10   | For Flask backend            |
| Node.js    | ≥ 18     | For React frontend           |
| OpenSSH    | any      | For tunnel from local laptop |

---

### 1. Clone & Navigate

```bash
git clone <your-repo>
cd fire-smoke-detection
```

### 2. Start on Remote Server

```bash
bash start.sh
```

This will:
- Create Python venv, install deps
- Start Flask API on `:5050`
- Install npm packages, start Vite on `:3000`

### 3. SSH Tunnel from Local Laptop

Open a terminal on **your local laptop** and run:

```bash
ssh -L 3000:localhost:3000 -L 5050:localhost:5050 user@YOUR_SERVER_IP
```

> Keep this terminal open while using the app.

### 4. Open in Local Browser

```
http://localhost:3000
```

Click **START DETECTION** — your **local laptop webcam** will activate.

---

## Train Custom Model (Recommended for >95%)

### Option A — With Roboflow API Key

```bash
cd backend
source .venv/bin/activate

# Get your API key from https://app.roboflow.com
python train.py \
  --api-key YOUR_ROBOFLOW_API_KEY \
  --epochs 100 \
  --batch 16 \
  --device 0       # GPU (or 'cpu')
```

### Option B — Manual Download

1. Download dataset from [Roboflow Universe](https://universe.roboflow.com/reyzi916/fire-smoke-det/dataset/6) in **YOLOv8 format**
2. Extract to `backend/datasets/`
3. Train:

```bash
python train.py --data datasets/fire-smoke-det-6/data.yaml --epochs 100
```

Best weights are automatically copied to `backend/models/fire_smoke_yolov8.pt`.

### Validate

```bash
python train.py --data datasets/fire-smoke-det-6/data.yaml --validate
```

---

## Docker Compose (Production)

```bash
# On remote server
docker compose up --build -d

# SSH tunnel from local laptop
ssh -L 3000:localhost:3000 -L 5050:localhost:5050 user@SERVER_IP

# Open http://localhost:3000
```

---

## API Reference

### `GET /api/health`
```json
{
  "status": "operational",
  "model_loaded": true,
  "device": "cpu",
  "uptime_seconds": 120.5
}
```

### `POST /api/detect`
**Request:**
```json
{
  "frame": "data:image/jpeg;base64,...",
  "timestamp": 1700000000000
}
```
**Response:**
```json
{
  "detections": [
    {
      "class": "fire",
      "confidence": 0.92,
      "bbox": [120, 80, 340, 260],
      "source": "ens",
      "ensemble": true
    }
  ],
  "annotated_frame": "data:image/jpeg;base64,...",
  "risk_level": "HIGH",
  "alert": true,
  "confidence_avg": 0.92,
  "processing_ms": 45.2,
  "fps": 8.5,
  "stats": { ... }
}
```

### `POST /api/stats/reset`
Resets session statistics counters.

### `GET /api/model/info`
Returns model metadata and pipeline info.

---

## Risk Levels

| Level    | Condition                               | Action                  |
|----------|-----------------------------------------|-------------------------|
| CRITICAL | Fire detected, confidence ≥ 75%         | Immediate evacuation    |
| HIGH     | Fire detected, confidence ≥ 50%         | Evacuate area           |
| MEDIUM   | Fire or smoke (conf ≥ 65%)             | Investigate immediately |
| LOW      | Trace smoke detected                    | Monitor closely         |
| CLEAR    | No threats                              | Normal operation        |

---

## Performance Targets

| Metric      | Target    | Method                               |
|-------------|-----------|--------------------------------------|
| mAP50       | > 0.95    | YOLOv8l fine-tuned                   |
| Precision   | > 0.93    | Ensemble + temporal smoothing        |
| Recall      | > 0.94    | HSV heuristics cover YOLO misses     |
| Latency     | < 100 ms  | CPU; < 30 ms on GPU                  |
| False pos.  | < 2%      | Temporal majority vote (5 frames)    |

---

## Project Structure

```
fire-smoke-detection/
├── backend/
│   ├── app.py              ← Flask API server
│   ├── detector.py         ← Full detection pipeline
│   ├── train.py            ← YOLOv8 training script
│   ├── requirements.txt
│   ├── Dockerfile.backend
│   └── models/             ← Place fire_smoke_yolov8.pt here
├── frontend/
│   ├── src/
│   │   ├── App.jsx         ← Root component
│   │   ├── App.css         ← Industrial light-mode styles
│   │   ├── components/
│   │   │   ├── DetectionCanvas.jsx  ← Video + bounding box overlay
│   │   │   ├── AlertPanel.jsx       ← Threat status + event log
│   │   │   ├── StatsGrid.jsx        ← Session metrics
│   │   │   ├── StatusBar.jsx        ← API/model/camera health
│   │   │   └── ControlPanel.jsx     ← Start/stop/reset
│   │   └── hooks/
│   │       ├── useCamera.js         ← WebRTC local camera
│   │       └── useDetection.js      ← API communication
│   ├── vite.config.js      ← Dev server + SSH proxy config
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docker-compose.yml
├── start.sh               ← One-command startup
├── stop.sh
└── README.md
```

---

## References

- Khan, M. et al. (2019). [Deeplab-based Fire Detection](https://khan-muhammad.github.io/public/papers/IEEE_TII_Fire_2019.pdf). *IEEE TII*
- IJCRT (2017). [Fire Detection using Image Processing](https://ijcrt.org/papers/IJPUB1704001.pdf)
- IJFMR (2025). [AI-Powered Fire & Smoke Detection](https://www.ijfmr.com/papers/2025/4/48942.pdf)
- [TalhaKarakoyunlu/Fire-and-Smoke-Detection](https://github.com/TalhaKarakoyunlu/Fire-and-Smoke-Detection) — GitHub reference
- [Roboflow fire-smoke-det v6 Dataset](https://universe.roboflow.com/reyzi916/fire-smoke-det/dataset/6)
- Ultralytics YOLOv8 Documentation

---

*PYREGUARD v2.0 — Built with precision for industrial safety applications*
