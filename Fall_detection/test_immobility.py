#!/usr/bin/env python3
"""
Quick test to verify immobility timing is working.
"""

import requests
import json
import time
import numpy as np
import cv2

def test_immobility_timing():
    """Test if immobility timer accumulates properly."""
    
    print("🕐 Testing immobility timing...")
    
    # Create sequence with guaranteed immobility
    background = np.full((480, 640, 3), (50, 50, 50), dtype=np.uint8)
    
    frames = []
    
    # Frame 1-3: Build motion history
    for i in range(3):
        frame = background.copy()
        cv2.ellipse(frame, (320, 240), (60, 180), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 4: Trigger shape change
    frame = background.copy()
    cv2.ellipse(frame, (320, 300), (180, 60), 90, 0, 360, (120, 150, 200), -1)
    frames.append(frame)
    
    # Frame 5-8: Complete immobility (identical frames)
    static_frame = background.copy()
    cv2.ellipse(static_frame, (320, 300), (180, 60), 90, 0, 360, (120, 150, 200), -1)
    
    for i in range(4):  # 4 identical static frames
        frames.append(static_frame.copy())
    
    print(f"📸 Created {len(frames)} frames")
    print("Expected: 3 moving → 1 shape change → 4 static (should trigger fall)")
    
    for i, frame in enumerate(frames):
        print(f"\n📤 Frame {i+1}/{len(frames)}")
        
        _, buffer = cv2.imencode('.jpg', frame)
        files = {'file': (f'frame_{i}.jpg', buffer.tobytes(), 'image/jpeg')}
        
        try:
            response = requests.post('http://localhost:8000/detect', files=files, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                state = result.get('state', 'Unknown')
                c_motion = result.get('metrics', {}).get('c_motion', 0)
                sigma_theta = result.get('metrics', {}).get('sigma_theta', 0)
                immobility = result.get('metrics', {}).get('immobility_secs', 0)
                
                print(f"  📊 {state} | C:{c_motion:.0f} σθ:{sigma_theta:.1f} immob:{immobility:.1f}s")
                
                if result.get('fall_detected'):
                    print(f"  🚨 FALL DETECTED at frame {i+1}!")
                    return True
                    
            else:
                print(f"  ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        # Longer delay to let immobility timer accumulate
        time.sleep(0.8)
    
    print(f"\n❌ Immobility timing test failed")
    return False

if __name__ == "__main__":
    test_immobility_timing()
