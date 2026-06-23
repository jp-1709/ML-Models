#!/usr/bin/env python3
"""
Test script to simulate fall with rapid frame sending to build motion history.
"""

import requests
import json
import time
import numpy as np
import cv2
import threading

def create_fall_sequence():
    """Create a sequence of frames simulating a fall."""
    frames = []
    
    # Frame 1-5: Standing person
    for i in range(5):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)
        # Standing person - vertical ellipse
        cv2.ellipse(frame, (320, 240), (60, 180), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 6-10: Rapid falling person
    for i in range(5):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)
        # Falling person - rapidly changing angle
        progress = i / 4.0
        angle = progress * 90  # 0 to 90 degrees
        center_x = 320 + int(progress * 50)
        center_y = 240 + int(progress * 60)
        cv2.ellipse(frame, (center_x, center_y), (80, 120), angle, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    # Frame 11-15: Fallen person on ground
    for i in range(5):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)
        # Fallen person - horizontal ellipse on ground
        cv2.ellipse(frame, (320, 290), (200, 60), 0, 0, 360, (120, 150, 200), -1)
        frames.append(frame)
    
    return frames

def send_frame(frame_data, frame_num):
    """Send a single frame to detection endpoint."""
    try:
        files = {'file': (f'frame_{frame_num}.jpg', frame_data, 'image/jpeg')}
        response = requests.post('http://localhost:8000/detect', files=files)
        
        if response.status_code == 200:
            result = response.json()
            state = result.get('state', 'Unknown')
            c_motion = result.get('metrics', {}).get('c_motion', 0)
            sigma_theta = result.get('metrics', {}).get('sigma_theta', 0)
            ellipse = result.get('ellipse')
            
            print(f"Frame {frame_num:2d}: State={state}, C_motion={c_motion:.1f}, σ_θ={sigma_theta:.1f}", end="")
            
            if ellipse:
                print(f", θ={ellipse['theta']:.1f}")
            
            if result.get('fall_detected'):
                print(f" 🚨 FALL DETECTED!")
                return True
            else:
                print()  # New line
        else:
            print(f"Frame {frame_num:2d}: ❌ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Frame {frame_num:2d}: ❌ Error {e}")
    
    return False

def test_rapid_fall():
    """Test fall detection with rapid frame sending."""
    
    print("🎬 Creating rapid fall sequence...")
    frames = create_fall_sequence()
    
    # Encode all frames to JPEG first
    encoded_frames = []
    for i, frame in enumerate(frames):
        _, buffer = cv2.imencode('.jpg', frame)
        encoded_frames.append(buffer.tobytes())
    
    print(f"📸 Created {len(frames)} frames")
    
    # Send frames very rapidly to build motion history
    fall_detected = False
    
    for i, frame_data in enumerate(encoded_frames):
        if fall_detected:
            break
            
        print(f"📤 Sending frame {i+1}/{len(frames)}", end="")
        
        # Send frame in separate thread for speed
        result = send_frame(frame_data, i+1)
        if result:
            fall_detected = True
            break
        
        # Very short delay to allow processing
        time.sleep(0.1)  # 100ms between frames
    
    print(f"\n🏁 Test completed! Fall detected: {fall_detected}")
    return fall_detected

if __name__ == "__main__":
    test_rapid_fall()
