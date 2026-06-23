#!/usr/bin/env python3
"""
Test script to upload a fall image for detection testing.
"""

import requests
import json

def test_fall_image():
    """Test the fall detection with a sample image."""
    
    # You would need to provide the actual fall image file path
    # For now, let's create a simple test with a synthetic image
    import numpy as np
    import cv2
    
    # Create a synthetic fall image
    height, width = 480, 640
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Add background
    frame[:] = (50, 50, 50)
    
    # Simulate fallen person - horizontal ellipse on ground
    cv2.ellipse(frame, (width//2, height//2 + 50), (200, 60), 0, 0, 360, (120, 150, 200), -1)
    
    # Add some noise
    noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
    frame = cv2.add(frame, noise)
    
    # Save the image
    cv2.imwrite('/tmp/test_fall.jpg', frame)
    
    print("📸 Created test fall image: /tmp/test_fall.jpg")
    
    # Upload to detection endpoint
    with open('/tmp/test_fall.jpg', 'rb') as f:
        files = {'file': ('test_fall.jpg', f, 'image/jpeg')}
        
        try:
            print("📤 Uploading to detection endpoint...")
            response = requests.post('http://localhost:8000/detect', files=files)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Detection successful!")
                print(json.dumps(result, indent=2))
                
                if result.get('fall_detected'):
                    print("🚨 FALL DETECTED! 🚨")
                else:
                    print("📊 No fall detected - person appears to be normal")
                    
            else:
                print(f"❌ Detection failed with status {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    test_fall_image()
