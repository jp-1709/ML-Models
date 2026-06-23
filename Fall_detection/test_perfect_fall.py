#!/usr/bin/env python3
"""
Test script to simulate fall with proper static immobility phase.
"""

import requests
import json
import time
import numpy as np
import cv2

def create_perfect_fall_sequence():
    """Create a sequence with truly static immobility phase."""
    frames = []
    
    # Create a static background that will be consistent
    background = np.full((480, 640, 3), (50, 50, 50), dtype=np.uint8)
    
    # Frame 1-5: Standing person (build motion history)
    for i in range(5):
        frame = background.copy()
        # Standing person - vertical ellipse with slight movement
        offset = i * 3
        cv2.ellipse(frame, (320 + offset, 240), (60, 180), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 6-9: Falling person (rapid orientation change)
    for i in range(4):
        frame = background.copy()
        # Falling person - tilted ellipse
        progress = i / 3.0
        center_x = 320 + int(progress * 100)
        center_y = 240 + int(progress * 80)
        angle = progress * 90  # Rotation to horizontal
        cv2.ellipse(frame, (center_x, center_y), (80, 120), angle, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 10-16: Fallen person on ground (TRULY STATIC)
    fallen_frame = background.copy()
    cv2.ellipse(fallen_frame, (320, 290), (200, 60), 0, 0, 360, (120, 150, 200), -1)
    
    for i in range(7):  # 7 identical frames for immobility
        frames.append(fallen_frame.copy())
    
    return frames

def test_perfect_fall():
    """Test fall detection with perfect sequence."""
    
    print("🎬 Creating perfect fall sequence with static immobility...")
    frames = create_perfect_fall_sequence()
    
    print(f"📸 Created {len(frames)} frames")
    print("📋 Sequence: 5 frames standing → 4 frames falling → 7 frames STATIC")
    
    # Send frames with appropriate timing
    for i, frame in enumerate(frames):
        print(f"\n📤 Frame {i+1}/{len(frames)}: ", end="")
        
        if i < 5:  # Standing phase
            phase = "standing"
            delay = 0.2
        elif i < 9:  # Falling phase
            phase = "falling"
            delay = 0.1
        else:  # Static immobility phase
            phase = "STATIC"
            delay = 0.4  # Longer to allow immobility detection
        
        print(f"{phase}")
        
        # Encode frame to JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        
        # Upload to detection endpoint
        files = {'file': (f'frame_{i}.jpg', buffer.tobytes(), 'image/jpeg')}
        
        try:
            response = requests.post('http://localhost:8000/detect', files=files)
            
            if response.status_code == 200:
                result = response.json()
                state = result.get('state', 'Unknown')
                c_motion = result.get('metrics', {}).get('c_motion', 0)
                sigma_theta = result.get('metrics', {}).get('sigma_theta', 0)
                pose_score = result.get('confidence', 0)
                immobility = result.get('metrics', {}).get('immobility_secs', 0)
                
                print(f"  📊 State: {state}, C_motion: {c_motion:.1f}, σ_θ: {sigma_theta:.1f}, Pose: {pose_score:.2f}")
                
                if immobility > 0:
                    print(f"  ⏱️  Immobility: {immobility:.1f}s ⭐")
                
                if result.get('fall_detected'):
                    print(f"  🚨🚨🚨 FALL DETECTED! 🚨🚨🚨")
                    print(f"  📈 Final metrics: C_motion={c_motion:.1f}, σ_θ={sigma_theta:.1f}, Pose={pose_score:.2f}")
                    return True
                else:
                    if state == "SHAPE_TRIGGERED":
                        print(f"  ⚠️  Shape triggered - waiting for immobility...")
                    elif state == "MOTION_DETECTED":
                        print(f"  🏃 Motion detected")
                    elif state == "IDLE":
                        print(f"  😴 Idle")
                    
            else:
                print(f"  ❌ Detection failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Upload failed: {e}")
        
        # Phase-appropriate delay
        time.sleep(delay)
    
    print("\n🏁 Test completed - No fall detected")
    return False

if __name__ == "__main__":
    test_perfect_fall()
