#!/usr/bin/env python3
"""
Comprehensive fall detection test that simulates real video stream.
This test properly exercises the complete fall detection pipeline.
"""

import requests
import json
import time
import numpy as np
import cv2

def create_realistic_fall_video():
    """Create a realistic fall sequence with proper temporal progression."""
    frames = []
    
    # Background
    background = np.full((480, 640, 3), (50, 50, 50), dtype=np.uint8)
    
    print("🎬 Creating realistic fall sequence...")
    
    # Phase 1: Person standing (frames 1-10)
    print("  📹 Phase 1: Standing person...")
    for i in range(10):
        frame = background.copy()
        # Standing person with subtle swaying
        sway = int(np.sin(i * 0.3) * 5)  # Natural sway
        cv2.ellipse(frame, (320 + sway, 240), (60, 180), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Phase 2: Fall initiation (frames 11-15)
    print("  📹 Phase 2: Fall initiation...")
    for i in range(5):
        frame = background.copy()
        progress = i / 4.0
        # Person starts to fall
        center_x = 320 + int(progress * 50)
        center_y = 240 + int(progress * 100)
        angle = progress * 45  # Start tilting
        cv2.ellipse(frame, (center_x, center_y), (80, 150), angle, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Phase 3: Falling motion (frames 16-20)
    print("  📹 Phase 3: Falling motion...")
    for i in range(5):
        frame = background.copy()
        progress = i / 4.0
        # Dramatic falling motion
        center_x = 370 + int(progress * 80)
        center_y = 340 + int(progress * 40)
        angle = 45 + progress * 45  # Continue rotation to horizontal
        cv2.ellipse(frame, (center_x, center_y), (120, 100), angle, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Phase 4: On ground (frames 21-30) - CRITICAL FOR IMMOBILITY
    print("  📹 Phase 4: Person on ground (immobile)...")
    fallen_frame = background.copy()
    cv2.ellipse(fallen_frame, (450, 380), (180, 60), 90, 0, 360, (120, 150, 200), -1)
    
    for i in range(10):  # 10 IDENTICAL frames for immobility
        frames.append(fallen_frame.copy())
    
    return frames

def test_comprehensive_fall_detection():
    """Test complete fall detection with realistic timing."""
    
    frames = create_realistic_fall_video()
    print(f"📸 Created {len(frames)} frames total")
    print("⏱️  Timing: 200ms between frames (simulates 5 FPS video)")
    
    fall_detected = False
    detection_frame = None
    
    for i, frame in enumerate(frames):
        print(f"\n📤 Frame {i+1}/{len(frames)}", end="")
        
        # Show phase
        if i < 10:
            phase = "standing"
        elif i < 15:
            phase = "falling"
        elif i < 20:
            phase = "falling"
        else:
            phase = "IMMOBILE"
        
        print(f" - {phase}")
        
        # Encode frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        files = {'file': (f'frame_{i:03d}.jpg', buffer.tobytes(), 'image/jpeg')}
        
        try:
            response = requests.post('http://localhost:8000/detect', files=files, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                state = result.get('state', 'Unknown')
                c_motion = result.get('metrics', {}).get('c_motion', 0)
                sigma_theta = result.get('metrics', {}).get('sigma_theta', 0)
                sigma_rho = result.get('metrics', {}).get('sigma_rho', 0)
                immobility = result.get('metrics', {}).get('immobility_secs', 0)
                
                print(f"  📊 {state} | C:{c_motion:.0f} σθ:{sigma_theta:.1f} σρ:{sigma_rho:.3f}")
                
                if immobility > 0:
                    print(f"  ⏱️  Immobility: {immobility:.1f}s")
                
                if result.get('fall_detected'):
                    print(f"  🚨🚨🚨 FALL DETECTED! 🚨🚨🚨")
                    print(f"  📈 Detection frame: {i+1}")
                    fall_detected = True
                    detection_frame = i + 1
                    break
                else:
                    if state == "SHAPE_TRIGGERED":
                        print(f"  ⚠️  Shape analysis triggered!")
                    elif state == "FALL_CONFIRMED":
                        print(f"  ✅ Fall confirmed!")
                        fall_detected = True
                        detection_frame = i + 1
                        break
                    
            else:
                print(f"  ❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        # Realistic video timing (200ms = 5 FPS)
        time.sleep(0.2)
    
    # Results
    print(f"\n" + "="*60)
    if fall_detected:
        print(f"✅ SUCCESS: Fall detection WORKING!")
        print(f"🎯 Fall detected at frame {detection_frame}")
        print(f"📊 Detection pipeline functioning correctly")
    else:
        print(f"❌ FAILURE: Fall detection not working")
        print(f"🔍 Need to investigate shape analysis or immobility detection")
    
    print("="*60)
    return fall_detected

if __name__ == "__main__":
    test_comprehensive_fall_detection()
