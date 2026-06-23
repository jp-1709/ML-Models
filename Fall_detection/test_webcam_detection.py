#!/usr/bin/env python3
"""
Test script to verify the webcam detection functionality.
Tests the browser webcam integration.
"""

import asyncio
import websockets
import json
import time
import cv2
import numpy as np
import base64

async def test_webcam_connection():
    """Test WebSocket connection to backend"""
    try:
        uri = "ws://localhost:8000/ws/video_stream"
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to video stream WebSocket")
            
            # Send a test frame
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            test_frame[:] = (100, 150, 200)  # Blue background
            
            # Add text
            cv2.putText(test_frame, "TEST FRAME", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', test_frame)
            jpg_bytes = buffer.tobytes()
            
            print("📤 Sending test frame...")
            await websocket.send(jpg_bytes)
            
            # Wait a bit
            await asyncio.sleep(1)
            
            print("✅ Test frame sent successfully")
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

async def test_alert_websocket():
    """Test alert WebSocket connection"""
    try:
        uri = "ws://localhost:8000/ws/alerts"
        print(f"Connecting to alerts WebSocket {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to alerts WebSocket")
            
            # Listen for messages
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"📨 Received: {data}")
            except asyncio.TimeoutError:
                print("⏰ No alerts received (timeout)")
            
    except Exception as e:
        print(f"❌ Alerts WebSocket test failed: {e}")

async def main():
    print("Testing Webcam Detection Integration")
    print("=" * 50)
    
    # Test video stream WebSocket
    await test_webcam_connection()
    
    print("\n" + "-" * 30)
    
    # Test alerts WebSocket
    await test_alert_websocket()
    
    print("\n" + "=" * 50)
    print("Webcam integration test completed!")

if __name__ == "__main__":
    asyncio.run(main())
