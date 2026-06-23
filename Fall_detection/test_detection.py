#!/usr/bin/env python3
"""
Simple test script to verify fall detection improvements.
Creates synthetic frames to test the detection pipeline.
"""

import cv2
import numpy as np
import time
import requests
import json

def create_fall_frame(width=640, height=480):
    """Create a synthetic frame simulating a fallen person"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add background
    frame[:] = (50, 50, 50)
    
    # Simulate fallen person as horizontal ellipse
    cv2.ellipse(frame, (width//2, height//2), (200, 80), 0, 0, 360, (100, 150, 200), -1)
    
    # Add some noise
    noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
    frame = cv2.add(frame, noise)
    
    return frame

def create_normal_frame(width=640, height=480):
    """Create a synthetic frame simulating a standing person"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add background
    frame[:] = (50, 50, 50)
    
    # Simulate standing person as vertical ellipse
    cv2.ellipse(frame, (width//2, height//2), (60, 200), 0, 0, 360, (100, 150, 200), -1)
    
    # Add some noise
    noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
    frame = cv2.add(frame, noise)
    
    return frame

def test_detection():
    """Test the fall detection API"""
    base_url = "http://localhost:8000"
    
    print("Testing Fall Detection System...")
    print("=" * 50)
    
    # Test 1: Normal frame
    print("\n1. Testing normal (standing) frame...")
    normal_frame = create_normal_frame()
    _, img_encoded = cv2.imencode('.jpg', normal_frame)
    
    response = requests.post(f"{base_url}/detect", 
                           files={'file': ('normal.jpg', img_encoded.tobytes(), 'image/jpeg')})
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Fall detected: {result.get('fall_detected', False)}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
    else:
        print(f"   Error: {response.status_code}")
    
    # Test 2: Fall frame
    print("\n2. Testing fall frame...")
    fall_frame = create_fall_frame()
    _, img_encoded = cv2.imencode('.jpg', fall_frame)
    
    response = requests.post(f"{base_url}/detect", 
                           files={'file': ('fall.jpg', img_encoded.tobytes(), 'image/jpeg')})
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Fall detected: {result.get('fall_detected', False)}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
    else:
        print(f"   Error: {response.status_code}")
    
    # Test 3: Check system status
    print("\n3. Checking system status...")
    response = requests.get(f"{base_url}/api/status")
    
    if response.status_code == 200:
        status = response.json()
        print(f"   System state: {status.get('state', 'unknown')}")
        print(f"   C_motion: {status.get('c_motion', 0):.1f}")
        print(f"   Sigma_theta: {status.get('sigma_theta', 0):.1f}")
        print(f"   Sigma_rho: {status.get('sigma_rho', 0):.3f}")
        print(f"   Pose score: {status.get('pose_score', 0):.2f}")
    else:
        print(f"   Error: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_detection()
