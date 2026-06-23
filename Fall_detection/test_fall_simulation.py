#!/usr/bin/env python3
"""
Test script to simulate fall detection by sending sequential frames.
"""

import asyncio
import websockets
import cv2
import numpy as np
import json
import time

def create_standing_person_frame(width=640, height=480):
    """Create a frame with a standing person"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (50, 50, 50)  # Dark background
    
    # Standing person - vertical ellipse
    cv2.ellipse(frame, (width//2, height//2), (60, 180), 0, 0, 360, (120, 150, 200), -1)
    
    # Add head
    cv2.circle(frame, (width//2, height//2 - 120), 30, (100, 120, 180), -1)
    
    return frame

def create_falling_person_frame(width=640, height=480, progress=0.5):
    """Create a frame with a person in the process of falling"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (50, 50, 50)  # Dark background
    
    # Calculate falling position
    center_x = width//2 + int(progress * 100)
    center_y = height//2 + int(progress * 80)
    angle = progress * 60  # Rotate as falling
    
    # Falling person - tilted ellipse
    cv2.ellipse(frame, (center_x, center_y), (80, 120), angle, 0, 360, (120, 150, 200), -1)
    
    return frame

def create_fallen_person_frame(width=640, height=480):
    """Create a frame with a fallen person on the ground"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (50, 50, 50)  # Dark background
    
    # Fallen person - horizontal ellipse on ground
    cv2.ellipse(frame, (width//2, height//2 + 50), (180, 60), 0, 0, 360, (120, 150, 200), -1)
    
    return frame

async def simulate_fall():
    """Send sequential frames to simulate a fall"""
    uri = "ws://localhost:8000/ws/video_stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🎬 Starting fall simulation...")
            
            # Send standing frames (normal activity)
            print("🚶 Sending standing frames...")
            for i in range(10):
                frame = create_standing_person_frame()
                _, buffer = cv2.imencode('.jpg', frame)
                await websocket.send(buffer.tobytes())
                await asyncio.sleep(0.2)
            
            # Send falling frames (transition)
            print("🤸 Sending falling frames...")
            for i in range(8):
                progress = i / 7.0
                frame = create_falling_person_frame(progress=progress)
                _, buffer = cv2.imencode('.jpg', frame)
                await websocket.send(buffer.tobytes())
                await asyncio.sleep(0.3)
            
            # Send fallen frames (person on ground)
            print("😵 Sending fallen frames...")
            for i in range(12):
                frame = create_fallen_person_frame()
                _, buffer = cv2.imencode('.jpg', frame)
                await websocket.send(buffer.tobytes())
                await asyncio.sleep(0.5)
            
            print("✅ Fall simulation completed!")
            
    except Exception as e:
        print(f"❌ Simulation failed: {e}")

async def monitor_alerts():
    """Monitor alerts WebSocket during simulation"""
    uri = "ws://localhost:8000/ws/alerts"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("👂 Monitoring for fall alerts...")
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    
                    if data.get('type') == 'fall_alert':
                        print("🚨 FALL DETECTED!")
                        print(f"   Event ID: {data.get('event_id')}")
                        print(f"   C_motion: {data.get('c_motion', 0):.1f}")
                        print(f"   Sigma_theta: {data.get('sigma_theta', 0):.1f}")
                        print(f"   Sigma_rho: {data.get('sigma_rho', 0):.3f}")
                        print(f"   Pose score: {data.get('pose_score', 0):.2f}")
                        return True
                    elif data.get('type') == 'heartbeat':
                        print("💓 Heartbeat received")
                    
                except asyncio.TimeoutError:
                    print("⏰ No more alerts, simulation complete")
                    return False
                    
    except Exception as e:
        print(f"❌ Alert monitoring failed: {e}")
        return False

async def main():
    print("🎭 Fall Detection Simulation")
    print("=" * 50)
    
    # Start both tasks concurrently
    simulation_task = asyncio.create_task(simulate_fall())
    alert_task = asyncio.create_task(monitor_alerts())
    
    # Wait for both to complete
    await simulation_task
    fall_detected = await alert_task
    
    print("\n" + "=" * 50)
    if fall_detected:
        print("🎉 SUCCESS: Fall was detected!")
    else:
        print("⚠️  INFO: No fall detected (may need more sensitive thresholds)")
    print("Simulation completed!")

if __name__ == "__main__":
    asyncio.run(main())
