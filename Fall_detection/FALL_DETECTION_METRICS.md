# Fall Detection Metrics and Thresholds Guide

## 🎯 **When Fall Detection Triggers**

The system detects a **FALL** when **ALL** these conditions are met:

### 1️⃣ **Motion Detection** (Stage 1)
- **Metric**: `C_motion` (Motion History Index)
- **Threshold**: `> 50.0%`
- **Purpose**: Detect significant movement to start analysis

### 2️⃣ **Shape Analysis** (Stage 2) 
- **Metric**: `σ_θ` (sigma_theta) - Orientation standard deviation
- **Threshold**: `> 5.0°`
- **Metric**: `σ_ρ` (sigma_rho) - Aspect ratio standard deviation  
- **Threshold**: `> 0.5`
- **Purpose**: Detect dramatic body orientation changes

### 3️⃣ **Immobility Confirmation** (Stage 3)
- **Metric**: `C_motion` must be `< 30.0%` for 3 consecutive frames
- **Metric**: Ellipse centroid stability `σ_x̄, σ_ȳ < 15.0 pixels`
- **Metric**: Ellipse axis stability `σ_a, σ_b < 10.0 pixels`
- **Metric**: Orientation stability `σ_θ < 20.0°`
- **Time Requirement**: `≥ 1.5 seconds` of continuous immobility
- **Purpose**: Confirm person stays still after fall (post-fall immobility)

---

## 📊 **Real-time Detection States**

| State | Conditions | What It Means |
|--------|-------------|----------------|
| **IDLE** | C_motion ≤ 50.0% | No significant motion |
| **MOTION_DETECTED** | C_motion > 50.0% | Motion detected, monitoring for shape changes |
| **SHAPE_TRIGGERED** | σ_θ > 5.0° OR σ_ρ > 0.5 | Dramatic shape change detected, waiting for immobility |
| **FALL_CONFIRMED** | Shape triggered + 1.5s immobility | **🚨 FALL DETECTED!** |

---

## 🔍 **How Metrics Are Calculated**

### **C_motion (Motion History Index)**
```
C_motion = (Motion Pixels / Total Foreground Pixels) × 100
```
- Measures percentage of foreground pixels with recent motion
- Computed from Motion History Image (MHI) over 500ms window
- Higher values = more movement

### **σ_θ (Sigma Theta - Orientation Deviation)**
```
σ_θ = std(θ₁, θ₂, ..., θₙ) over 1.0 second window
```
- θ = ellipse orientation angle (-90° to +90°)
- Standard deviation over rolling 1-second window
- High σ_θ = rapid orientation changes (falling motion)

### **σ_ρ (Sigma Rho - Aspect Ratio Deviation)**
```
σ_ρ = std(ρ₁, ρ₂, ..., ρₙ) over 1.0 second window  
```
- ρ = a/b (major/minor axis ratio)
- Measures changes in body shape (standing → fallen)
- High σ_ρ = dramatic shape deformation

---

## 📈 **Example Fall Detection Sequence**

```
Frame 1-5:   C_motion=0%, σ_θ=0°, σ_ρ=0.0    → IDLE
Frame 6-10:  C_motion=100%, σ_θ=0°, σ_ρ=0.0  → MOTION_DETECTED  
Frame 11-15: C_motion=100%, σ_θ=25°, σ_ρ=0.8 → SHAPE_TRIGGERED
Frame 16-20: C_motion=0%, σ_θ=2°, σ_ρ=0.1   → IMMOBILITY (1.5s later)
Result:     🚨 FALL_CONFIRMED! 🚨
```

---

## ⚙️ **Current Threshold Values**

```python
# Motion Detection
MHI_MOTION_THRESHOLD = 50.0%     # Minimum motion to start shape analysis

# Shape Analysis  
SIGMA_THETA_THRESHOLD = 5.0°      # Orientation change sensitivity
SIGMA_RHO_THRESHOLD = 0.5          # Shape change sensitivity
SHAPE_WINDOW_SECONDS = 1.0s        # Time window for σ calculations

# Immobility Confirmation
IMMOBILITY_WINDOW_SECONDS = 2.0s   # Max time to confirm fall
IMMOBILITY_CMOTION_MAX = 30.0%      # Max motion for "unmoving" frame
IMMOBILITY_CENTROID_PX = 15.0px    # Position stability tolerance
IMMOBILITY_AXIS_PX = 10.0px        # Shape size stability tolerance  
IMMOBILITY_THETA_DEG = 20.0°       # Orientation stability tolerance
```

---

## 🎯 **For Testing Purposes**

To trigger fall detection in your tests:

1. **Create motion** (C_motion > 50%)
2. **Add rapid orientation changes** (σ_θ > 5.0°)  
3. **Follow with 1.5+ seconds of stillness** (C_motion < 30%)

**Perfect test sequence:**
- 3-5 frames: Standing with slight movement
- 3-4 frames: Dramatic falling motion (orientation changes)
- 5+ frames: Completely static fallen position

The system will show: `IDLE → MOTION_DETECTED → SHAPE_TRIGGERED → FALL_CONFIRMED`
