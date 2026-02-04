#!/usr/bin/env python3
"""
Test client for Jutsu Academy Backend Server.
Connects to the backend and displays received frames + detection data.

Usage:
    1. Start backend:  python src/backend_server.py
    2. Run this test:  python src/test_backend_client.py
"""

import asyncio
import json
import base64
import time

import cv2
import numpy as np

try:
    import websockets
except ImportError:
    print("[!] Please install websockets: pip install websockets")
    exit(1)


async def test_client():
    uri = "ws://127.0.0.1:8765"
    print(f"[*] Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[+] Connected to backend server!")
            
            # Receive initial connection message
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"[+] Server info: {data}")
            
            # Request jutsu registry
            await websocket.send(json.dumps({"type": "get_jutsus"}))
            
            frame_count = 0
            start_time = time.time()
            
            while True:
                try:
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    
                    if data.get("type") == "jutsu_registry":
                        print(f"[+] Received jutsu registry: {list(data['jutsus'].keys())}")
                        continue
                    
                    if data.get("type") == "frame_data":
                        frame_count += 1
                        
                        # Decode and display frame
                        if "frame_base64" in data:
                            img_data = base64.b64decode(data["frame_base64"])
                            nparr = np.frombuffer(img_data, np.uint8)
                            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            
                            # Draw detections
                            for det in data.get("detections", []):
                                x1, y1, x2, y2 = det["bbox"]
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(frame, f"{det['class']} {det['confidence']:.2f}",
                                           (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            # Draw face landmarks
                            if data.get("face"):
                                face = data["face"]
                                h, w = frame.shape[:2]
                                
                                # Draw mouth position
                                mx, my = face["mouth"][0] * w, face["mouth"][1] * h
                                cv2.circle(frame, (int(mx), int(my)), 5, (0, 0, 255), -1)
                                
                                # Show head yaw
                                cv2.putText(frame, f"Yaw: {face['head_yaw']:.2f}",
                                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                            
                            # Draw hand center
                            if data.get("hand"):
                                hand = data["hand"]
                                cx, cy = hand["palm_center_px"]
                                cv2.circle(frame, (cx, cy), 10, (255, 0, 255), -1)
                                cv2.putText(frame, hand["handedness"],
                                           (cx + 15, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                            
                            # FPS info
                            fps = data.get("fps", 0)
                            cv2.putText(frame, f"Backend FPS: {fps:.1f}",
                                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            cv2.imshow("Backend Test Client", frame)
                            
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                break
                        
                        # Print stats every second
                        elapsed = time.time() - start_time
                        if elapsed >= 1.0:
                            client_fps = frame_count / elapsed
                            det_count = len(data.get("detections", []))
                            print(f"[Stats] Client FPS: {client_fps:.1f}, Detections: {det_count}, "
                                  f"Face: {'✓' if data.get('face') else '✗'}, "
                                  f"Hand: {'✓' if data.get('hand') else '✗'}")
                            frame_count = 0
                            start_time = time.time()
                
                except websockets.ConnectionClosed:
                    print("[-] Connection closed")
                    break
                    
    except ConnectionRefusedError:
        print("[!] Could not connect to backend server.")
        print("    Make sure the backend is running: python src/backend_server.py")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    print("=" * 50)
    print("  Jutsu Academy - Backend Test Client")
    print("=" * 50)
    print("  Press 'q' in the window to quit\n")
    asyncio.run(test_client())
