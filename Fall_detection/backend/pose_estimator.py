"""
pose_estimator.py
─────────────────────────────────────────────────────────────
Optional pose-estimation layer using YOLOv8 Pose.

This module enhances the classical MHI+ellipse pipeline with
skeleton-based cues derived from Ultralytics YOLOv8:

  • Head position (nose landmark) relative to frame height
    → if head_y / frame_height > HEAD_FLOOR_RATIO the person
      is likely lying down / on the ground.
  • Torso angle (shoulder–hip vector) relative to vertical
    → large angle (> ~45°) suggests a horizontal posture.
  • Shoulder & hip y-positions to compute a fall-pose score.

These signals are combined with C_motion and σ_θ/σ_ρ in the
main FallDetector for a more robust multi-cue decision.
─────────────────────────────────────────────────────────────
"""

import math
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

import config

try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False


# ──────────────────────────────────────────────────────────────
# Data container
# ──────────────────────────────────────────────────────────────

@dataclass
class PoseResult:
    """Pose-derived fall indicators."""
    available:          bool   # False if YOLO is not installed
    head_floor_ratio:   float  # nose_y / frame_height  (1.0 = bottom)
    torso_angle_deg:    float  # angle of shoulder→hip vector from vertical
    fall_pose_score:    float  # [0, 1] composite score; > 0.6 → suspicious
    landmarks_detected: bool
    annotated_frame:    Optional[np.ndarray]  # BGR frame with skeleton drawn


# ──────────────────────────────────────────────────────────────
# PoseEstimator
# ──────────────────────────────────────────────────────────────

class PoseEstimator:
    """
    Wraps YOLOv8 Pose for real-time skeleton extraction.

    Usage
    -----
    estimator = PoseEstimator()
    result = estimator.process(frame)
    if result.fall_pose_score > 0.6:
        ...
    """

    # YOLOv8 COCO Keypoint Indices
    _NOSE           = 0
    _LEFT_SHOULDER  = 5
    _RIGHT_SHOULDER = 6
    _LEFT_HIP       = 11
    _RIGHT_HIP      = 12

    def __init__(self) -> None:
        self._enabled = config.USE_POSE_ESTIMATION and _YOLO_AVAILABLE
        self._model   = None

        if self._enabled:
            # Load the YOLOv8nano pose model (will download weights if missing)
            self._model = YOLO('yolov8n-pose.pt')

    def process(self, frame: np.ndarray) -> PoseResult:
        """
        Run YOLOv8 pose estimation on *frame* (BGR, HxW×3).

        Returns a PoseResult. If YOLO is not available or disabled,
        returns a zeroed result with available=False.
        """
        h, w = frame.shape[:2]

        if not self._enabled or self._model is None:
            return PoseResult(
                available=False,
                head_floor_ratio=0.0,
                torso_angle_deg=0.0,
                fall_pose_score=0.0,
                landmarks_detected=False,
                annotated_frame=None,
            )

        # Run inference (disable verbose to avoid console spam)
        results = self._model(frame, verbose=False)
        annotated = frame.copy()

        if not results or len(results) == 0:
            return PoseResult(
                available=True,
                head_floor_ratio=0.0,
                torso_angle_deg=0.0,
                fall_pose_score=0.0,
                landmarks_detected=False,
                annotated_frame=annotated,
            )

        result = results[0]
        
        # Draw bounding boxes and skeletons using ultralytics built-in plotter
        annotated = result.plot()

        if result.keypoints is None or len(result.keypoints.xy) == 0:
            return PoseResult(
                available=True,
                head_floor_ratio=0.0,
                torso_angle_deg=0.0,
                fall_pose_score=0.0,
                landmarks_detected=False,
                annotated_frame=annotated,
            )

        # Grab keypoints of the first detected person (or the highest confidence one)
        # shape is (17, 2)
        kpts = result.keypoints.xy[0].cpu().numpy()
        conf = result.keypoints.conf[0].cpu().numpy() if result.keypoints.conf is not None else np.ones(17)

        def is_valid(idx):
            """Check if keypoint is detected with sufficient confidence."""
            return conf[idx] > 0.3 and (kpts[idx][0] > 0 or kpts[idx][1] > 0)

        # ── Head floor ratio ──────────────────────────────────
        nose_y = 0.0
        if is_valid(self._NOSE):
            nose_y = kpts[self._NOSE][1] / h

        # ── Torso angle ───────────────────────────────────────
        torso_angle_deg = 0.0
        if (is_valid(self._LEFT_SHOULDER) and is_valid(self._RIGHT_SHOULDER) and
            is_valid(self._LEFT_HIP) and is_valid(self._RIGHT_HIP)):
            
            mid_shoulder = (
                (kpts[self._LEFT_SHOULDER][0] + kpts[self._RIGHT_SHOULDER][0]) / 2,
                (kpts[self._LEFT_SHOULDER][1] + kpts[self._RIGHT_SHOULDER][1]) / 2,
            )
            mid_hip = (
                (kpts[self._LEFT_HIP][0] + kpts[self._RIGHT_HIP][0]) / 2,
                (kpts[self._LEFT_HIP][1] + kpts[self._RIGHT_HIP][1]) / 2,
            )
            dx = mid_hip[0] - mid_shoulder[0]
            dy = mid_hip[1] - mid_shoulder[1]
            torso_angle_deg = abs(math.degrees(math.atan2(dx, dy + 1e-9)))

        # ── Fall pose score ───────────────────────────────────
        # Weighted heuristic: horizontal torso + head near floor
        torso_score = min(torso_angle_deg / 75.0, 1.0)  # Lower angle threshold
        head_score  = max(0.0, (nose_y - 0.4) / 0.6)   # Lower floor threshold

        fall_pose_score = 0.5 * torso_score + 0.5 * head_score  # Equal weighting

        # ── Annotate debug text ───────────────────────────────
        cv2.putText(
            annotated,
            f"Pose score: {fall_pose_score:.2f}  torso: {torso_angle_deg:.0f} deg",
            (8, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 200, 255),
            1,
        )

        return PoseResult(
            available=True,
            head_floor_ratio=nose_y,
            torso_angle_deg=torso_angle_deg,
            fall_pose_score=fall_pose_score,
            landmarks_detected=True,
            annotated_frame=annotated,
        )

    def close(self) -> None:
        """Release YOLOv8 resources (if any)."""
        pass
