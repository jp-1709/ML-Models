#!/usr/bin/env python3
"""
Debug test to check what's happening with shape analysis.
"""

import requests
import json
import numpy as np
import cv2

def test_single_frame():
    """Test a single frame with dramatic shape change."""
    
    print("🔍 Testing single frame analysis...")
    
    # Create a dramatic fall frame
    frame = np.full((480, 640, 3), (50, 50, 50), dtype=np.uint8)
    # Very clear fallen person - horizontal ellipse
    cv2.ellipse(frame, (320, 300), (200, 60), 0, 0, 360, (120, 150, 200), -1)
    
    # Save for inspection
    cv2.imwrite('/tmp/debug_fall.jpg', frame)
    print("📸 Saved debug frame to /tmp/debug_fall.jpg")
    
    # Test detection
    _, buffer = cv2.imencode('.jpg', frame)
    files = {'file': ('debug_fall.jpg', buffer.tobytes(), 'image/jpeg')}
    
    try:
        response = requests.post('http://localhost:8000/detect', files=files, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Detection response:")
            print(json.dumps(result, indent=2))
            
            # Check key metrics
            state = result.get('state', 'Unknown')
            c_motion = result.get('metrics', {}).get('c_motion', 0)
            sigma_theta = result.get('metrics', {}).get('sigma_theta', 0)
            sigma_rho = result.get('metrics', {}).get('sigma_rho', 0)
            pose_score = result.get('confidence', 0)
            
            print(f"\n📊 Key Analysis:")
            print(f"  State: {state}")
            print(f"  C_motion: {c_motion:.1f} (threshold: {30.0})")
            print(f"  σ_θ: {sigma_theta:.1f}° (threshold: 5.0°)")
            print(f"  σ_ρ: {sigma_rho:.3f} (threshold: 0.5)")
            print(f"  Pose score: {pose_score:.3f}")
            
            # Analysis
            if c_motion > 30:
                print("  ✅ Motion detected")
            else:
                print("  ❌ No motion detected")
                
            if sigma_theta > 5.0:
                print("  ✅ Shape change detected")
            else:
                print("  ❌ No shape change detected")
                
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_single_frame()
