#!/usr/bin/env python3
"""
Test script to simulate fall with proper immobility phase.
"""

import requests
import json
import time
import numpy as np
import cv2

def create_realistic_fall_sequence():
    """Create a sequence of frames simulating a realistic fall with immobility."""
    frames = []
    
    # Frame 1-8: Standing person (normal motion)
    for i in range(8):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)  # Background
        # Standing person - vertical ellipse with slight movement
        offset = i * 2
        cv2.ellipse(frame, (320 + offset, 240), (60, 180), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 9-12: Falling person (rapid orientation change)
    for i in range(4):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)
        # Falling person - tilted ellipse
        progress = i / 3.0
        center_x = 320 + int(progress * 100)
        center_y = 240 + int(progress * 80)
        angle = progress * 90  # Rotation to horizontal
        cv2.ellipse(frame, (center_x, center_y), (80, 120), angle, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 13-20: Fallen person on ground (IMMOBILE - no motion)
    for i in range(8):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)
        # Fallen person - horizontal ellipse, NO MOVEMENT
        cv2.ellipse(frame, (320, 290), (200, 60), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    return frames

def test_realistic_fall():
    """Test fall detection with realistic sequence including immobility."""
    
    print("🎬 Creating realistic fall sequence with immobility...")
    frames = create_realistic_fall_sequence()
    
    print(f"📸 Created {len(frames)} frames")
    print("📋 Sequence: 8 frames standing → 4 frames falling → 8 frames immobile")
    
    # Send frames with appropriate timing
    for i, frame in enumerate(frames):
        print(f"\n📤 Frame {i+1}/{len(frames)}: ", end="")
        
        # Different timing for different phases
        if i < 8:  # Standing phase
            phase = "standing"
            delay = 0.2
        elif i < 12:  # Falling phase
            phase = "falling"
            delay = 0.1
        else:  # Immobility phase
            phase = "immobile"
            delay = 0.3  # Slower to allow immobility detection
        
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
                    print(f"  ⏱️  Immobility: {immobility:.1f}s")
                
                if result.get('fall_detected'):
                    print(f"  🚨 FALL DETECTED! 🚨")
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
    test_realistic_fall()
