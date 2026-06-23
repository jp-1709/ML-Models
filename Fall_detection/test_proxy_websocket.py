#!/usr/bin/env python3
"""
Test script to verify proxied WebSocket connections through frontend.
"""

import asyncio
import websockets
import json

async def test_proxied_websockets():
    """Test WebSocket connections through the frontend proxy"""
    
    print("Testing Proxied WebSocket Connections")
    print("=" * 50)
    
    # Test video stream through proxy
    try:
        uri = "ws://localhost:3000/backend-ws/video_stream"
        print(f"Connecting to proxied video stream: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to proxied video stream WebSocket")
            
            # Send a simple test frame
            test_frame = b"test_frame_data"
            await websocket.send(test_frame)
            print("📤 Sent test frame through proxy")
            
    except Exception as e:
        print(f"❌ Proxied video stream failed: {e}")
    
    print("\n" + "-" * 30)
    
    # Test alerts through proxy
    try:
        uri = "ws://localhost:3000/backend-ws/alerts"
        print(f"Connecting to proxied alerts: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to proxied alerts WebSocket")
            
            # Listen for heartbeat
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                data = json.loads(message)
                print(f"📨 Received through proxy: {data}")
            except asyncio.TimeoutError:
                print("⏰ No alerts received (timeout)")
            
    except Exception as e:
        print(f"❌ Proxied alerts failed: {e}")
    
    print("\n" + "=" * 50)
    print("Proxy WebSocket test completed!")

if __name__ == "__main__":
    asyncio.run(test_proxied_websockets())
