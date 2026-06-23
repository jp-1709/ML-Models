"""
fall_detector.py
─────────────────────────────────────────────────────────────
Central orchestrator for the multi-stage fall detection
pipeline.

Pipeline stages (matching Figure 3 of Rougier et al.):

  Stage 1 – Background subtraction → foreground mask
  Stage 2 – MHI update → C_motion
             • If C_motion < 65 % → no action (normal / no motion)
  Stage 3 – Ellipse analysis → σ_θ, σ_ρ
             • If neither threshold exceeded → no action
  Stage 4 – (Parallel) Pose estimation → fall_pose_score
  Stage 5 – Immobility confirmation over 5-second window
  Stage 6 – Alert trigger

Decision fusion (classical + pose):
    fall = (stage3_triggered) AND (
                immobility_confirmed
                OR pose_score > 0.6    # immediate confirmation via pose
           )
─────────────────────────────────────────────────────────────
"""

import time
import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

import config
from mhi_processor  import MHIProcessor
from shape_analyzer import ShapeAnalyzer, ShapeAnalysisResult
from pose_estimator import PoseEstimator, PoseResult
from alert_manager  import AlertManager


# ──────────────────────────────────────────────────────────────
# State machine
# ──────────────────────────────────────────────────────────────

class DetectorState(Enum):
    IDLE               = auto()   # no significant motion
    MOTION_DETECTED    = auto()   # C_motion > threshold; awaiting shape check
    SHAPE_TRIGGERED    = auto()   # σ_θ or σ_ρ exceeded; monitoring immobility
    FALL_CONFIRMED     = auto()   # full fall confirmed; alert fired


# ──────────────────────────────────────────────────────────────
# Per-frame result
# ──────────────────────────────────────────────────────────────

@dataclass
class FrameResult:
    annotated_frame:  np.ndarray    # BGR frame with all overlays
    state:            DetectorState
    c_motion:         float
    sigma_theta:      float
    sigma_rho:        float
    pose_score:       float
    alert_fired:      bool
    immobility_secs:  float         # how long person has been still (0 if not)


# ──────────────────────────────────────────────────────────────
# FallDetector
# ──────────────────────────────────────────────────────────────

class FallDetector:
    """
    Processes one BGR frame at a time and returns a FrameResult.

    Instantiate once, call process_frame() in your capture loop.
    """

    def __init__(self, alert_manager: AlertManager) -> None:
        self._alert_mgr = alert_manager

        # ── Sub-modules ─────────────────────────────────────────
        self._bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=config.MOG2_HISTORY,
            varThreshold=config.MOG2_VAR_THRESHOLD,
            detectShadows=config.MOG2_DETECT_SHADOWS,
        )
        self._mhi     = MHIProcessor()
        self._shape   = ShapeAnalyzer()
        self._pose    = PoseEstimator()

        # ── State ────────────────────────────────────────────────
        self._state: DetectorState = DetectorState.IDLE
        self._shape_trigger_ts: float = 0.0    # when shape threshold fired
        self._immobility_start: float = 0.0    # when we first detected stillness
        self._still_acc: float  = 0.0          # cumulative immobility seconds

        # Immobility verification: store (ts, c_motion, cx, cy, a, b, theta)
        self._immob_buf: deque = deque(maxlen=int(
            config.IMMOBILITY_WINDOW_SECONDS * config.TARGET_FPS
        ))

        # Latest metrics (exposed via property)
        self._c_motion:    float = 0.0
        self._sigma_theta: float = 0.0
        self._sigma_rho:   float = 0.0
        self._pose_score:  float = 0.0

        # Counters
        self._frame_count: int = 0

    # ──────────────────────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────────────────────

    def process_frame(self, frame: np.ndarray) -> FrameResult:
        """
        Run the full fall detection pipeline on one BGR frame.

        Parameters
        ----------
        frame : np.ndarray  (H, W, 3)  BGR input frame

        Returns
        -------
        FrameResult with annotated frame and all metrics.
        """
        self._frame_count += 1
        self._alert_mgr.tick()

        # ── Stage 1: Foreground segmentation ──────────────────
        fg_mask = self._get_foreground(frame)

        # ── Stage 2: MHI + C_motion ───────────────────────────
        mhi_vis, c_motion = self._mhi.update(frame, fg_mask)
        self._c_motion = c_motion

        # ── Stage 3: Ellipse / shape analysis ─────────────────
        shape_result: ShapeAnalysisResult = self._shape.analyze(fg_mask)
        self._sigma_theta = shape_result.sigma_theta
        self._sigma_rho   = shape_result.sigma_rho

        # ── Stage 4: Pose estimation ───────────────────────────
        pose_result: PoseResult = self._pose.process(frame)
        self._pose_score = pose_result.fall_pose_score

        # ── Stage 5 & 6: State machine ────────────────────────
        alert_fired = False
        immobility_secs = 0.0
        alert_fired, immobility_secs = self._update_state(
            c_motion, shape_result, pose_result
        )

        # ── Build annotated frame ──────────────────────────────
        annotated = self._annotate(
            frame, fg_mask, mhi_vis, shape_result, pose_result,
            c_motion, alert_fired, immobility_secs,
        )

        return FrameResult(
            annotated_frame=annotated,
            state=self._state,
            c_motion=c_motion,
            sigma_theta=self._sigma_theta,
            sigma_rho=self._sigma_rho,
            pose_score=self._pose_score,
            alert_fired=alert_fired,
            immobility_secs=immobility_secs,
        )

    # ──────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────

    @property
    def state(self) -> DetectorState:
        return self._state

    @property
    def metrics(self) -> Dict[str, float]:
        return {
            "c_motion":    round(self._c_motion, 1),
            "sigma_theta": round(self._sigma_theta, 2),
            "sigma_rho":   round(self._sigma_rho, 3),
            "pose_score":  round(self._pose_score, 3),
            "frame_count": self._frame_count,
        }

    # ──────────────────────────────────────────────────────────
    # State machine implementation
    # ──────────────────────────────────────────────────────────

    def _update_state(
        self,
        c_motion:     float,
        shape_result: ShapeAnalysisResult,
        pose_result:  PoseResult,
    ) -> Tuple[bool, float]:
        """
        Advance the state machine and return (alert_fired, immobility_secs).
        """
        now = time.monotonic()
        alert_fired = False
        immobility_secs = 0.0

        # ── Record immobility buffer ───────────────────────────
        e = shape_result.ellipse
        self._immob_buf.append((
            now,
            c_motion,
            e.cx if e else 0,
            e.cy if e else 0,
            e.a  if e else 0,
            e.b  if e else 0,
            e.theta if e else 0,
        ))

        if self._state == DetectorState.IDLE:
            if c_motion >= config.MHI_MOTION_THRESHOLD:
                self._state = DetectorState.MOTION_DETECTED

        elif self._state == DetectorState.MOTION_DETECTED:
            if c_motion < config.MHI_MOTION_THRESHOLD:
                # Motion dropped; reset
                self._state = DetectorState.IDLE
            elif shape_result.fall_shape:
                # Shape threshold triggered
                self._state = DetectorState.SHAPE_TRIGGERED
                self._shape_trigger_ts = now
                self._immobility_start = 0.0

        elif self._state == DetectorState.SHAPE_TRIGGERED:
            elapsed = now - self._shape_trigger_ts

            # ── Pose fast-path: skip immobility wait ──────────
            if (pose_result.available
                    and pose_result.fall_pose_score > 0.45
                    and c_motion < config.IMMOBILITY_CMOTION_MAX):
                alert_fired = self._fire_alert(c_motion, shape_result, pose_result)
                self._state = DetectorState.FALL_CONFIRMED
                return alert_fired, immobility_secs

            # ── Classical immobility check ────────────────────
            if elapsed <= config.IMMOBILITY_WINDOW_SECONDS:
                imm_ok = self._check_immobility()
                print(f"🔍 DEBUG: Immobility check result: {imm_ok}, elapsed: {elapsed:.2f}s")
                if imm_ok:
                    if self._immobility_start == 0.0:
                        self._immobility_start = now
                    immobility_secs = now - self._immobility_start
                    print(f"🔍 DEBUG: Immobility timer: {immobility_secs:.2f}s")
                else:
                    self._immobility_start = 0.0

                if immobility_secs >= 1.5:
                    print(f"🔍 DEBUG: TRIGGERING FALL ALERT!")
                    alert_fired = self._fire_alert(c_motion, shape_result, pose_result)
                    self._state = DetectorState.FALL_CONFIRMED
            else:
                # Window expired without immobility confirmation → false positive
                print(f"🔍 DEBUG: Window expired, resetting to IDLE")
                self._state = DetectorState.IDLE

        elif self._state == DetectorState.FALL_CONFIRMED:
            immobility_secs = max(0.0, now - self._immobility_start) if self._immobility_start else 0.0
            # Return to IDLE after cooldown
            if c_motion > config.MHI_MOTION_THRESHOLD:
                self._state = DetectorState.IDLE

        return alert_fired, immobility_secs

    def _check_immobility(self) -> bool:
        """
        Evaluate §4.4 criteria over the _immob_buf window.
        Returns True if the ellipse qualifies as stationary.
        """
        if len(self._immob_buf) < 3:
            return False

        buf = list(self._immob_buf)
        c_motions = [r[1] for r in buf]
        cxs       = [r[2] for r in buf]
        cys       = [r[3] for r in buf]
        axs       = [r[4] for r in buf]
        bys       = [r[5] for r in buf]
        thetas    = [r[6] for r in buf]

        import numpy as np
        ok_cmotion = all(c < config.IMMOBILITY_CMOTION_MAX for c in c_motions[-3:])
        ok_cx      = np.std(cxs)     < config.IMMOBILITY_CENTROID_PX
        ok_cy      = np.std(cys)     < config.IMMOBILITY_CENTROID_PX
        ok_a       = np.std(axs)     < config.IMMOBILITY_AXIS_PX
        ok_b       = np.std(bys)     < config.IMMOBILITY_AXIS_PX
        ok_theta   = np.std(thetas)  < config.IMMOBILITY_THETA_DEG

        return ok_cmotion and ok_cx and ok_cy and ok_a and ok_b and ok_theta

    def _fire_alert(
        self,
        c_motion:     float,
        shape_result: ShapeAnalysisResult,
        pose_result:  PoseResult,
    ) -> bool:
        return self._alert_mgr.trigger(
            c_motion    = c_motion,
            sigma_theta = shape_result.sigma_theta,
            sigma_rho   = shape_result.sigma_rho,
            pose_score  = pose_result.fall_pose_score if pose_result.available else 0.0,
        )

    # ──────────────────────────────────────────────────────────
    # Foreground segmentation
    # ──────────────────────────────────────────────────────────

    def _get_foreground(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply MOG2 background subtraction and morphological
        clean-up to produce a clean foreground mask.
        """
        fg = self._bg_sub.apply(frame)

        # Remove shadows (MOG2 marks them as 127)
        _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)

        # Morphological clean-up: close small holes, remove speckles
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel, iterations=2)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  kernel, iterations=1)

        return fg

    # ──────────────────────────────────────────────────────────
    # Annotation / visualisation
    # ──────────────────────────────────────────────────────────

    _STATE_COLORS = {
        DetectorState.IDLE:            (100, 200, 100),   # green
        DetectorState.MOTION_DETECTED: (0,   200, 255),   # yellow-ish
        DetectorState.SHAPE_TRIGGERED: (0,   140, 255),   # orange
        DetectorState.FALL_CONFIRMED:  (0,    0,  255),   # red
    }

    _STATE_LABELS = {
        DetectorState.IDLE:            "Normal Activity",
        DetectorState.MOTION_DETECTED: "Motion Detected",
        DetectorState.SHAPE_TRIGGERED: "Analyzing Shape…",
        DetectorState.FALL_CONFIRMED:  "⚠ FALL DETECTED",
    }

    def _annotate(
        self,
        frame:          np.ndarray,
        fg_mask:        np.ndarray,
        mhi_vis:        np.ndarray,
        shape_result:   ShapeAnalysisResult,
        pose_result:    PoseResult,
        c_motion:       float,
        alert_fired:    bool,
        immobility_secs: float,
    ) -> np.ndarray:
        """
        Compose a single annotated BGR frame for streaming.
        Overlays: ellipse, status banner, metric text, MHI mini-view.
        """
        # Use pose-annotated frame if available
        if pose_result.available and pose_result.annotated_frame is not None:
            out = pose_result.annotated_frame.copy()
        else:
            out = frame.copy()

        h, w = out.shape[:2]
        color = self._STATE_COLORS[self._state]
        label = self._STATE_LABELS[self._state]

        # ── Ellipse overlay ────────────────────────────────────
        ellipse_color = (0, 0, 255) if self._state == DetectorState.FALL_CONFIRMED else (0, 255, 0)
        self._shape.draw_ellipse(out, color=ellipse_color, thickness=2)

        # ── Foreground outline ─────────────────────────────────
        fg_colored = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR)
        fg_colored[:, :, 0] = 0  # Zero out blue channel → green-ish silhouette
        out = cv2.addWeighted(out, 1.0, fg_colored, 0.15, 0)

        # ── Status banner (top) ────────────────────────────────
        cv2.rectangle(out, (0, 0), (w, 44), (20, 20, 20), -1)
        cv2.putText(out, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # ── Metric HUD (bottom-left) ───────────────────────────
        metrics = [
            f"C_motion: {c_motion:.1f}%",
            f"sigma_theta: {shape_result.sigma_theta:.1f}deg",
            f"sigma_rho: {shape_result.sigma_rho:.3f}",
            f"Pose score: {self._pose_score:.2f}",
        ]
        y0 = h - 10 - len(metrics) * 18
        cv2.rectangle(out, (0, y0 - 6), (220, h), (20, 20, 20), -1)
        for i, txt in enumerate(metrics):
            cv2.putText(out, txt, (6, y0 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

        # ── MHI mini thumbnail (bottom-right) ─────────────────
        thumb_w, thumb_h = 120, 90
        if mhi_vis is not None:
            thumb = cv2.resize(mhi_vis, (thumb_w, thumb_h))
            x1 = w - thumb_w - 4
            y1 = h - thumb_h - 4
            out[y1:y1+thumb_h, x1:x1+thumb_w] = thumb
            cv2.rectangle(out,
                          (x1 - 1, y1 - 1),
                          (x1 + thumb_w, y1 + thumb_h),
                          (80, 80, 80), 1)
            cv2.putText(out, "MHI", (x1 + 3, y1 + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

        # ── Red flash overlay on fall ──────────────────────────
        if self._alert_mgr.alert_active:
            overlay = out.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 200), -1)
            out = cv2.addWeighted(out, 0.82, overlay, 0.18, 0)
            # Bold alert text
            cv2.putText(out, "FALL ALERT", (w // 2 - 100, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)

        # ── Border colour tracks state ─────────────────────────
        cv2.rectangle(out, (0, 0), (w - 1, h - 1), color, 3)

        return out
