#!/usr/bin/env python3
"""
Test script to simulate fall with slower frame sending to build motion history.
"""

import requests
import json
import time
import numpy as np
import cv2

def create_fall_sequence():
    """Create a sequence of frames simulating a fall."""
    frames = []
    
    # Frame 1-8: Standing person (build motion history)
    for i in range(8):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)
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
        angle = progress * 90  # Full rotation to horizontal
        cv2.ellipse(frame, (center_x, center_y), (80, 120), angle, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 13-20: Fallen person on ground (immobile)
    for i in range(8):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)
        # Fallen person - horizontal ellipse on ground
        cv2.ellipse(frame, (320, 290), (200, 60), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    return frames

def test_slow_fall():
    """Test fall detection with slower frame sending."""
    
    print("🎬 Creating realistic fall sequence...")
    frames = create_fall_sequence()
    
    print(f"📸 Created {len(frames)} frames")
    
    # Send frames slowly to build motion history
    for i, frame in enumerate(frames):
        print(f"📤 Sending frame {i+1}/{len(frames)}")
        
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
                ellipse = result.get('ellipse')
                
                print(f"  📊 State: {state}, C_motion: {c_motion:.1f}, σ_θ: {sigma_theta:.1f}")
                
                if ellipse:
                    print(f"  ⭕ Ellipse: a={ellipse['a']:.0f}, b={ellipse['b']:.0f}, θ={ellipse['theta']:.1f}")
                
                if result.get('fall_detected'):
                    print(f"  🚨 FALL DETECTED! 🚨")
                    print(f"  📈 Metrics: {json.dumps(result.get('metrics', {}), indent=6)}")
                    return True
                else:
                    print(f"  ✅ No fall detected")
                    
            else:
                print(f"  ❌ Detection failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Upload failed: {e}")
        
        # Longer delay to allow motion history to build
        time.sleep(0.8)  # 800ms between frames
    
    print("\n🏁 Test completed!")
    return False

if __name__ == "__main__":
    test_slow_fall()
