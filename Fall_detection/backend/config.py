"""
config.py
─────────────────────────────────────────────────────────────
Central configuration for the Fall Detection System.
All thresholds are derived from Rougier et al. (2007) and
tuned with guidance from modern pose-based literature.
─────────────────────────────────────────────────────────────
"""

from typing import Union


# ──────────────────────────────────────────────────────────────
# VIDEO CAPTURE
# ──────────────────────────────────────────────────────────────
CAMERA_INDEX: Union[int, str] = "browser"        # "browser" for browser webcam, 0 for first camera
# For testing with video file, set to path like "/path/to/video.mp4"
# Or for IP cam, set to "rtsp://username:password@ip:port/stream"
FRAME_WIDTH:  int = 640
FRAME_HEIGHT: int = 480
TARGET_FPS:   int = 15         # Frames per second used for timing calculations


# ──────────────────────────────────────────────────────────────
# MOTION HISTORY IMAGE  (Section 2 of paper)
# ──────────────────────────────────────────────────────────────
MHI_DURATION_MS:        int   = 500    # τ window in milliseconds (paper: 500ms)
MHI_MOTION_THRESHOLD:   float = 50.0  # C_motion % to trigger shape analysis - more realistic
MHI_DIFF_THRESHOLD:     int   = 30    # pixel-difference threshold for D(x,y,t)


# ──────────────────────────────────────────────────────────────
# SHAPE / ELLIPSE ANALYSIS  (Section 3 & 4.3 of paper)
# ──────────────────────────────────────────────────────────────
SHAPE_WINDOW_SECONDS:   float = 1.0   # duration over which σθ, σρ are computed
SIGMA_THETA_THRESHOLD:  float = 5.0   # orientation std-dev threshold (degrees) - very sensitive
SIGMA_RHO_THRESHOLD:    float = 0.5   # ratio (a/b) std-dev threshold - very sensitive
MIN_BLOB_AREA:          int   = 1500  # ignore foreground blobs smaller than this


# ──────────────────────────────────────────────────────────────
# IMMOBILITY CONFIRMATION  (Section 4.4 of paper)
# ──────────────────────────────────────────────────────────────
IMMOBILITY_WINDOW_SECONDS: float = 2.0  # look-ahead after suspected fall - increased for reliable detection
IMMOBILITY_CMOTION_MAX:    float = 30.0   # max C_motion for "unmoving" frame - realistic threshold
IMMOBILITY_CENTROID_PX:    float = 15.0   # σ_x̄, σ_ȳ pixel tolerance - realistic for person movement
IMMOBILITY_AXIS_PX:        float = 10.0   # σ_a, σ_b pixel tolerance - realistic for ellipse variations
IMMOBILITY_THETA_DEG:      float = 20.0   # σ_θ degree tolerance - realistic for orientation stability


# ──────────────────────────────────────────────────────────────
# POSE ESTIMATION (MediaPipe enhancement)
# ──────────────────────────────────────────────────────────────
USE_POSE_ESTIMATION:    bool  = True   # toggle MediaPipe overlay
POSE_DETECTION_CONF:    float = 0.5
POSE_TRACKING_CONF:     float = 0.5

# Head-to-hip height ratio: if head Y is close to floor Y → reinforces fall
POSE_HEAD_FLOOR_RATIO:  float = 0.75  # head_y / frame_height > threshold → low


# ──────────────────────────────────────────────────────────────
# BACKGROUND SUBTRACTION
# ──────────────────────────────────────────────────────────────
MOG2_HISTORY:        int   = 120     # Reduced for faster adaptation
MOG2_VAR_THRESHOLD:  int   = 25      # Reduced for sensitivity
MOG2_DETECT_SHADOWS: bool  = False    # Disable shadow detection


# ──────────────────────────────────────────────────────────────
# ALERT / COOLDOWN
# ──────────────────────────────────────────────────────────────
ALERT_COOLDOWN_SECONDS: float = 10.0   # minimum gap between successive alerts


# ──────────────────────────────────────────────────────────────
# STREAMING
# ──────────────────────────────────────────────────────────────
STREAM_JPEG_QUALITY: int = 75   # 0–100; lower = smaller payload, faster stream
CORS_ORIGINS: list   = ["*"]
