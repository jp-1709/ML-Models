#!/usr/bin/env python3
"""
Final test to confirm fall detection is working properly.
"""

import requests
import json
import time
import numpy as np
import cv2

def create_fall_sequence():
    """Create a sequence that should definitely trigger fall detection."""
    frames = []
    
    # Static background
    background = np.full((480, 640, 3), (50, 50, 50), dtype=np.uint8)
    
    # Frame 1-3: Standing person (minimal movement)
    for i in range(3):
        frame = background.copy()
        cv2.ellipse(frame, (320, 240), (60, 180), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 4-6: Falling (dramatic orientation change)
    for i in range(3):
        frame = background.copy()
        angle = i * 30  # 0°, 30°, 60°
        cv2.ellipse(frame, (320, 280), (100, 80), angle, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 7-10: Fallen on ground (completely static)
    fallen_frame = background.copy()
    cv2.ellipse(fallen_frame, (320, 300), (180, 60), 0, 0, 360, (120, 150, 200), -1)
    
    for i in range(4):  # 4 identical static frames
        frames.append(fallen_frame.copy())
    
    return frames

def test_fall_detection():
    """Test with optimized sequence."""
    
    print("🎯 Testing optimized fall sequence...")
    frames = create_fall_sequence()
    
    print(f"📸 Created {len(frames)} frames")
    print("Expected: 3 standing → 3 falling → 4 static fallen")
    
    fall_detected = False
    
    for i, frame in enumerate(frames):
        print(f"\n📤 Frame {i+1}/{len(frames)}")
        
        # Encode and send
        _, buffer = cv2.imencode('.jpg', frame)
        files = {'file': (f'frame_{i}.jpg', buffer.tobytes(), 'image/jpeg')}
        
        try:
            response = requests.post('http://localhost:8000/detect', files=files, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                state = result.get('state', 'Unknown')
                c_motion = result.get('metrics', {}).get('c_motion', 0)
                sigma_theta = result.get('metrics', {}).get('sigma_theta', 0)
                
                print(f"  📊 State: {state}")
                print(f"  📈 C_motion: {c_motion:.1f}, σ_θ: {sigma_theta:.1f}")
                
                if result.get('fall_detected'):
                    print(f"  🚨🚨🚨 SUCCESS! FALL DETECTED! 🚨🚨🚨")
                    fall_detected = True
                    break
                else:
                    if state == "SHAPE_TRIGGERED":
                        print(f"  ⚠️  Shape analysis triggered")
                    elif state == "FALL_CONFIRMED":
                        print(f"  ✅ Fall confirmed!")
                        fall_detected = True
                        break
                    
            else:
                print(f"  ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        # Short delay between frames
        time.sleep(0.5)
    
    if fall_detected:
        print(f"\n✅ Fall detection is WORKING!")
    else:
        print(f"\n❌ Fall detection failed - needs further investigation")
    
    return fall_detected

if __name__ == "__main__":
    test_fall_detection()
