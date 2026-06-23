"""
FireSmokeDetector — Ensemble Detection Pipeline
================================================
Stage 1 : CLAHE + bilateral denoising preprocessing
Stage 2 : YOLOv8 deep-learning inference
Stage 3 : HSV color-space fire/smoke heuristics
Stage 4 : Weighted ensemble fusion with NMS
Stage 5 : Temporal smoothing (rolling-window vote)

References:
- Khan et al. (IEEE TII 2019) — color-based fire segmentation
- YOLOv8 (Ultralytics 2023)
- IJCRT / IJFMR 2025 ensemble approaches
"""

import cv2
import time
import logging
import numpy as np
from collections import deque
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Colour Ranges (HSV) ──────────────────────────────────────────────────────
# Fire: warm reds, oranges, yellows  (Khan et al. 2019)
FIRE_LOWER_1 = np.array([0,   120,  70],  dtype=np.uint8)   # red-orange wrap-around
FIRE_UPPER_1 = np.array([18,  255, 255],  dtype=np.uint8)
FIRE_LOWER_2 = np.array([170, 120,  70],  dtype=np.uint8)   # red wrap high end
FIRE_UPPER_2 = np.array([180, 255, 255],  dtype=np.uint8)

# Smoke: near-grey, low saturation, medium–high value
SMOKE_LOWER  = np.array([0,   0,   80],  dtype=np.uint8)
SMOKE_UPPER  = np.array([180, 60, 220],  dtype=np.uint8)

# Risk thresholds (pixel-coverage %)
FIRE_RISK_LOW    = 0.005   # 0.5 %
FIRE_RISK_MED    = 0.02    # 2 %
FIRE_RISK_HIGH   = 0.06    # 6 %
SMOKE_RISK_LOW   = 0.015
SMOKE_RISK_MED   = 0.04
SMOKE_RISK_HIGH  = 0.10

# Temporal smoothing window
TEMPORAL_WINDOW = 5


class FireSmokeDetector:
    """
    Ensemble fire & smoke detector combining:
      - YOLOv8 (deep learning)
      - HSV colour-space heuristics (classical CV)
      - CLAHE contrast enhancement
      - Temporal majority-vote smoothing
    """

    def __init__(
        self,
        model_path: str = "models/fire_smoke_yolov8.pt",
        confidence: float = 0.45,
        iou: float = 0.45,
        device: str = "cpu",
    ):
        self.confidence  = confidence
        self.iou         = iou
        self.device      = device
        self.model_path  = model_path
        self.is_loaded   = False
        self.model       = None
        self.class_names = {0: "fire", 1: "smoke"}

        # CLAHE for contrast enhancement
        self.clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

        # Temporal smoothing buffers
        self._fire_hist  = deque(maxlen=TEMPORAL_WINDOW)
        self._smoke_hist = deque(maxlen=TEMPORAL_WINDOW)

        self._load_model()

    # ─── Model Loading ────────────────────────────────────────────────────────

    def _load_model(self):
        """Load YOLOv8 — falls back to base pretrained if custom weights absent."""
        try:
            from ultralytics import YOLO
            if Path(self.model_path).exists():
                logger.info(f"Loading custom weights: {self.model_path}")
                self.model = YOLO(self.model_path)
            else:
                logger.warning(
                    f"Custom weights not found at '{self.model_path}'. "
                    "Loading YOLOv8l pretrained. Run train.py to fine-tune."
                )
                self.model = YOLO("yolov8l.pt")
                # Override class names for display (model still uses COCO indices
                # until fine-tuned; colour heuristics compensate)
                self.class_names = {
                    c: n for c, n in enumerate(self.model.names.values())
                }
            self.is_loaded = True
            logger.info("✅ YOLOv8 model loaded")
        except ImportError:
            logger.error("ultralytics not installed — YOLO inference disabled")
        except Exception as e:
            logger.error(f"Model load failed: {e}", exc_info=True)

    # ─── Preprocessing ────────────────────────────────────────────────────────

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        Stage 1 preprocessing pipeline:
          1. Bilateral filter (edge-preserving denoise)
          2. CLAHE on L-channel in LAB space
          3. Mild gamma correction
        """
        # Denoise (preserves edges needed for YOLO)
        denoised = cv2.bilateralFilter(frame, d=9, sigmaColor=75, sigmaSpace=75)

        # CLAHE on luminance
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_clahe = self.clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge([l_clahe, a, b]), cv2.COLOR_LAB2BGR)

        # Gamma correction (gamma=0.8 brightens shadows slightly)
        inv_gamma = 1.0 / 0.85
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)],
                         dtype=np.uint8)
        return cv2.LUT(enhanced, table)

    # ─── Stage 2: YOLO Inference ──────────────────────────────────────────────

    def _yolo_detect(self, frame: np.ndarray) -> List[Dict]:
        """Run YOLOv8 inference and return normalised detections."""
        if not self.is_loaded or self.model is None:
            return []
        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence,
                iou=self.iou,
                device=self.device,
                verbose=False,
                imgsz=640,
            )
        except Exception as e:
            logger.error(f"YOLO inference error: {e}")
            return []

        detections = []
        h, w = frame.shape[:2]
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id  = int(box.cls.item())
                conf    = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # Map to fire/smoke if custom model loaded
                raw_name = self.model.names[cls_id].lower()
                if "fire" in raw_name:
                    cls_name = "fire"
                elif "smoke" in raw_name:
                    cls_name = "smoke"
                else:
                    continue   # skip unrelated COCO classes

                detections.append({
                    "class":      cls_name,
                    "confidence": round(conf, 3),
                    "bbox":       [int(x1), int(y1), int(x2), int(y2)],
                    "source":     "yolo",
                })
        return detections

    # ─── Stage 3: HSV Colour Heuristics ──────────────────────────────────────

    def _hsv_detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Colour-space fire & smoke detection (Khan et al. IEEE TII 2019).
        Returns pixel-coverage detections as bounding rectangles.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, w = frame.shape[:2]
        total_px = h * w
        detections = []

        # ── Fire mask ────────────────────────────────────────────────────────
        fire_mask  = cv2.inRange(hsv, FIRE_LOWER_1, FIRE_UPPER_1)
        fire_mask |= cv2.inRange(hsv, FIRE_LOWER_2, FIRE_UPPER_2)
        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_OPEN,  kernel, iterations=2)
        fire_mask = cv2.morphologyEx(fire_mask, cv2.MORPH_CLOSE, kernel, iterations=3)

        fire_contours, _ = cv2.findContours(
            fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for cnt in fire_contours:
            area = cv2.contourArea(cnt)
            if area < 400:   # skip tiny noise regions
                continue
            coverage = area / total_px
            if coverage < FIRE_RISK_LOW:
                continue
            x, y, cw, ch = cv2.boundingRect(cnt)
            conf = min(0.50 + coverage * 5, 0.92)   # heuristic confidence
            detections.append({
                "class":      "fire",
                "confidence": round(conf, 3),
                "bbox":       [x, y, x + cw, y + ch],
                "source":     "hsv",
                "coverage":   round(coverage, 4),
            })

        # ── Smoke mask ────────────────────────────────────────────────────────
        smoke_mask = cv2.inRange(hsv, SMOKE_LOWER, SMOKE_UPPER)
        # Exclude fire pixels from smoke mask
        smoke_mask = cv2.bitwise_and(smoke_mask, cv2.bitwise_not(fire_mask))
        smoke_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        smoke_mask = cv2.morphologyEx(smoke_mask, cv2.MORPH_OPEN,  smoke_kernel)
        smoke_mask = cv2.morphologyEx(smoke_mask, cv2.MORPH_CLOSE, smoke_kernel, iterations=4)

        smoke_contours, _ = cv2.findContours(
            smoke_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for cnt in smoke_contours:
            area = cv2.contourArea(cnt)
            if area < 800:
                continue
            coverage = area / total_px
            if coverage < SMOKE_RISK_LOW:
                continue
            x, y, cw, ch = cv2.boundingRect(cnt)
            conf = min(0.45 + coverage * 3, 0.88)
            detections.append({
                "class":      "smoke",
                "confidence": round(conf, 3),
                "bbox":       [x, y, x + cw, y + ch],
                "source":     "hsv",
                "coverage":   round(coverage, 4),
            })

        return detections

    # ─── Stage 4: Ensemble Fusion + NMS ──────────────────────────────────────

    def _fuse(
        self,
        yolo_dets: List[Dict],
        hsv_dets:  List[Dict],
        frame_shape: Tuple[int, int],
    ) -> List[Dict]:
        """
        Merge YOLO and HSV detections:
        - If both agree on a region → boost confidence
        - Apply soft-NMS to suppress duplicates
        - Retain only fire/smoke classes
        """
        all_dets = yolo_dets + hsv_dets
        if not all_dets:
            return []

        # Separate by class
        fused = []
        for cls in ("fire", "smoke"):
            cls_dets = [d for d in all_dets if d["class"] == cls]
            if not cls_dets:
                continue

            # Check for YOLO + HSV agreement → boost
            yolo_cls = [d for d in cls_dets if d["source"] == "yolo"]
            hsv_cls  = [d for d in cls_dets if d["source"] == "hsv"]

            for det in yolo_cls:
                # Does any HSV bbox overlap significantly?
                overlap = False
                for h in hsv_cls:
                    if self._iou_pair(det["bbox"], h["bbox"]) > 0.25:
                        overlap = True
                        break
                if overlap:
                    det = dict(det)
                    det["confidence"] = min(det["confidence"] * 1.15, 0.99)
                    det["ensemble"]   = True
                fused.append(det)

            # Add non-overlapping HSV detections not covered by YOLO
            for h in hsv_cls:
                covered = any(
                    self._iou_pair(h["bbox"], y["bbox"]) > 0.3
                    for y in yolo_cls
                )
                if not covered:
                    fused.append(h)

        # Soft-NMS per class
        final = []
        for cls in ("fire", "smoke"):
            cls_dets = [d for d in fused if d["class"] == cls]
            final.extend(self._soft_nms(cls_dets))

        return final

    @staticmethod
    def _iou_pair(b1, b2) -> float:
        x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
        x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        if inter == 0:
            return 0.0
        a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        return inter / (a1 + a2 - inter + 1e-6)

    @staticmethod
    def _soft_nms(dets: List[Dict], iou_thresh: float = 0.45) -> List[Dict]:
        if not dets:
            return []
        dets = sorted(dets, key=lambda d: d["confidence"], reverse=True)
        keep = []
        while dets:
            best = dets.pop(0)
            keep.append(best)
            new_dets = []
            for d in dets:
                iou = FireSmokeDetector._iou_pair(best["bbox"], d["bbox"])
                if iou < iou_thresh:
                    new_dets.append(d)
                else:
                    # Soft suppress — reduce confidence instead of discard
                    d = dict(d)
                    d["confidence"] *= (1 - iou)
                    if d["confidence"] > 0.25:
                        new_dets.append(d)
            dets = sorted(new_dets, key=lambda d: d["confidence"], reverse=True)
        return keep

    # ─── Stage 5: Temporal Smoothing ─────────────────────────────────────────

    def _temporal_smooth(self, has_fire: bool, has_smoke: bool):
        """
        Rolling-window majority vote — prevents single-frame false positives.
        """
        self._fire_hist.append(int(has_fire))
        self._smoke_hist.append(int(has_smoke))

        fire_vote  = sum(self._fire_hist)  >= max(1, len(self._fire_hist)  // 2 + 1)
        smoke_vote = sum(self._smoke_hist) >= max(1, len(self._smoke_hist) // 2 + 1)
        return fire_vote, smoke_vote

    # ─── Risk Classifier ─────────────────────────────────────────────────────

    @staticmethod
    def _risk_level(detections: List[Dict]) -> str:
        has_fire  = any(d["class"] == "fire"  for d in detections)
        has_smoke = any(d["class"] == "smoke" for d in detections)
        max_conf  = max((d["confidence"] for d in detections), default=0)

        if has_fire and max_conf >= 0.75:
            return "CRITICAL"
        if has_fire and max_conf >= 0.50:
            return "HIGH"
        if has_fire or (has_smoke and max_conf >= 0.65):
            return "MEDIUM"
        if has_smoke:
            return "LOW"
        return "CLEAR"

    # ─── Annotation ──────────────────────────────────────────────────────────

    def _annotate(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Draw bounding boxes with class/confidence labels."""
        annotated = frame.copy()
        COLOURS = {
            "fire":  (0,   80, 255),   # BGR deep orange-red
            "smoke": (130, 130, 130),  # grey
        }
        for det in detections:
            cls   = det["class"]
            conf  = det["confidence"]
            x1, y1, x2, y2 = det["bbox"]
            colour = COLOURS.get(cls, (0, 255, 0))

            # Box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), colour, 2)

            # Label background
            label = f"{cls.upper()}  {conf:.0%}"
            (tw, th), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
            )
            cv2.rectangle(
                annotated,
                (x1, y1 - th - baseline - 6),
                (x1 + tw + 6, y1),
                colour, -1
            )
            cv2.putText(
                annotated, label,
                (x1 + 3, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 2, cv2.LINE_AA
            )

            # Source badge (small)
            src = det.get("source", "")
            if det.get("ensemble"):
                src = "ens"
            cv2.putText(
                annotated, src,
                (x1 + 3, y2 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                colour, 1, cv2.LINE_AA
            )

        # Risk banner
        risk = self._risk_level(detections)
        risk_colours = {
            "CRITICAL": (0,   0, 220),
            "HIGH":     (0,  60, 200),
            "MEDIUM":   (0, 130, 230),
            "LOW":      (0, 180, 100),
            "CLEAR":    (70, 70, 70),
        }
        cv2.rectangle(annotated, (0, 0), (frame.shape[1], 32),
                      risk_colours.get(risk, (70, 70, 70)), -1)
        cv2.putText(
            annotated, f"RISK: {risk}",
            (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
            (255, 255, 255), 2, cv2.LINE_AA
        )
        return annotated

    # ─── Public API ──────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Full pipeline:  preprocess → YOLO → HSV → fuse → temporal → annotate
        """
        preprocessed = self._preprocess(frame)

        yolo_dets = self._yolo_detect(preprocessed)
        hsv_dets  = self._hsv_detect(preprocessed)

        fused = self._fuse(yolo_dets, hsv_dets, frame.shape[:2])

        has_fire  = any(d["class"] == "fire"  for d in fused)
        has_smoke = any(d["class"] == "smoke" for d in fused)

        fire_confirmed, smoke_confirmed = self._temporal_smooth(has_fire, has_smoke)

        # Filter to only temporally confirmed classes
        final = [
            d for d in fused
            if (d["class"] == "fire"  and fire_confirmed)
            or (d["class"] == "smoke" and smoke_confirmed)
        ]

        risk = self._risk_level(final)
        alert = risk in ("HIGH", "CRITICAL")

        conf_avg = (
            round(np.mean([d["confidence"] for d in final]), 3)
            if final else 0.0
        )

        annotated = self._annotate(frame, final)

        return {
            "detections":     final,
            "annotated_frame": annotated,
            "risk_level":     risk,
            "alert":          alert,
            "confidence_avg": conf_avg,
        }

    def get_info(self) -> Dict[str, Any]:
        return {
            "model_path":    self.model_path,
            "model_loaded":  self.is_loaded,
            "device":        self.device,
            "confidence":    self.confidence,
            "iou":           self.iou,
            "pipeline":      ["CLAHE+denoise", "YOLOv8", "HSV-colour", "ensemble-NMS", "temporal-vote"],
            "classes":       list(self.class_names.values()),
            "temporal_win":  TEMPORAL_WINDOW,
        }
