#!/usr/bin/env python3
"""
Jutsu Academy - Backend Server for Godot 4.5
=============================================
WebSocket server that handles:
- Webcam capture
- YOLO hand sign detection
- MediaPipe face/hand landmark tracking
- Sends frame + detection data to Godot frontend

Usage:
    python src/backend_server.py [--port 8765] [--camera 0]
"""

import asyncio
import json
import time
import base64
import argparse
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp

try:
    import websockets
except ImportError:
    print("[!] Please install websockets: pip install websockets")
    exit(1)

from ultralytics import YOLO

# Import local utils
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.paths import get_class_names, get_latest_weights
from src.jutsu_registry import OFFICIAL_JUTSUS


class JutsuBackendServer:
    """
    WebSocket server that captures frames, runs ML inference,
    and streams results to Godot frontend.
    """
    
    def __init__(self, camera_index: int = 0, model_path: str = None):
        print("[*] Initializing Jutsu Backend Server...")
        
        # ═══════════════════════════════════════════════════════════════
        # YOLO Model
        # ═══════════════════════════════════════════════════════════════
        if model_path is None:
            model_path = get_latest_weights()
        if model_path is None:
            raise RuntimeError("No YOLO weights found. Train model first.")
        
        print(f"[+] Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        self.class_names = get_class_names()
        
        # ═══════════════════════════════════════════════════════════════
        # MediaPipe Face Landmarker
        # ═══════════════════════════════════════════════════════════════
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        self.face_landmarker = None
        face_model_path = Path("models/face_landmarker.task")
        
        if face_model_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(face_model_path))
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=True,
                    output_facial_transformation_matrixes=True,
                    num_faces=1
                )
                self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
                print("[+] Face detection: MediaPipe")
            except Exception as e:
                print(f"[!] Face detection failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # MediaPipe Hand Landmarker
        # ═══════════════════════════════════════════════════════════════
        self.hand_landmarker = None
        hand_model_path = Path("models/hand_landmarker.task")
        self.last_mp_timestamp = 0
        
        if hand_model_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(hand_model_path))
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=1,
                    running_mode=vision.RunningMode.VIDEO
                )
                self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
                print("[+] Hand tracking: MediaPipe")
            except Exception as e:
                print(f"[!] Hand tracking failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # Camera
        # ═══════════════════════════════════════════════════════════════
        self.camera_index = camera_index
        self.cap = None
        self._init_camera()
        
        # ═══════════════════════════════════════════════════════════════
        # State
        # ═══════════════════════════════════════════════════════════════
        self.connected_clients = set()
        self.running = False
        
        # Settings (can be updated by Godot)
        self.settings = {
            "current_jutsu": "Fireball",
            "effects_enabled": True,
            "send_frames": True,
            "frame_quality": 30,  # JPEG quality - lower = faster transfer
            "target_fps": 30,
            "send_landmarks": False  # Don't send full landmark arrays by default
        }
        
        # FPS tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        print("[+] Backend server initialized!")
    
    def _init_camera(self):
        """Initialize or reinitialize the camera."""
        if self.cap is not None:
            self.cap.release()
        
        self.cap = cv2.VideoCapture(self.camera_index)
        # Use lower resolution for faster WebSocket transfer
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")
        
        print(f"[+] Camera {self.camera_index} opened (480x360 @ 30fps)")
    
    def _detect_hands_yolo(self, frame: np.ndarray) -> list:
        """
        Run YOLO detection on frame.
        Returns list of detections: [{"class": str, "confidence": float, "bbox": [x1,y1,x2,y2]}]
        """
        results = self.model(frame, stream=True, verbose=False, imgsz=320)
        detections = []
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                cls_idx = int(box.cls[0])
                cls_name = self.class_names[cls_idx]
                
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                detections.append({
                    "class": cls_name,
                    "confidence": round(conf, 3),
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)]
                })
        
        # Sort by confidence, return highest
        detections.sort(key=lambda x: x["confidence"], reverse=True)
        return detections
    
    def _detect_face_landmarks(self, frame: np.ndarray) -> dict | None:
        """
        Run MediaPipe face detection.
        Returns face data with key landmarks or None.
        """
        if self.face_landmarker is None:
            return None
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = self.face_landmarker.detect(mp_image)
            
            if not result.face_landmarks:
                return None
            
            face = result.face_landmarks[0]
            h, w = frame.shape[:2]
            
            # Extract key landmark positions (normalized 0-1)
            def get_pos(idx):
                lm = face[idx]
                return [round(lm.x, 4), round(lm.y, 4), round(lm.z, 4)]
            
            # Calculate head rotation for fire wind effect
            nose_x = face[1].x
            left_x = face[234].x
            right_x = face[454].x
            
            width = right_x - left_x
            head_yaw = 0.0
            if width > 0:
                rel_nose = (nose_x - left_x) / width
                head_yaw = (rel_nose - 0.5) * 2  # -1 to 1
            
            result = {
                "mouth": get_pos(13),
                "nose": get_pos(1),
                "left_eye": get_pos(468) if len(face) > 468 else get_pos(159),
                "right_eye": get_pos(473) if len(face) > 473 else get_pos(386),
                "head_yaw": round(head_yaw, 3)
            }
            
            # Only send full landmarks if explicitly requested (for mesh viz)
            if self.settings.get("send_landmarks", False):
                result["landmarks"] = [[round(lm.x, 4), round(lm.y, 4)] for lm in face]
            
            return result
            
        except Exception as e:
            print(f"[!] Face detection error: {e}")
            return None
    
    def _detect_hand_landmarks(self, frame: np.ndarray) -> dict | None:
        """
        Run MediaPipe hand detection.
        Returns hand data with landmarks or None.
        """
        if self.hand_landmarker is None:
            return None
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Monotonic timestamp for VIDEO mode
            timestamp_ms = int(time.time() * 1000)
            if timestamp_ms <= self.last_mp_timestamp:
                timestamp_ms = self.last_mp_timestamp + 1
            self.last_mp_timestamp = timestamp_ms
            
            result = self.hand_landmarker.detect_for_video(mp_image, timestamp_ms)
            
            if not result.hand_landmarks:
                return None
            
            hand = result.hand_landmarks[0]
            h, w = frame.shape[:2]
            
            # Calculate palm center (average of wrist + knuckles)
            indices = [0, 5, 9, 13, 17]
            palm_x = sum(hand[i].x for i in indices) / len(indices)
            palm_y = sum(hand[i].y for i in indices) / len(indices)
            
            # Get handedness
            handedness = "Unknown"
            if result.handedness:
                handedness = result.handedness[0][0].category_name
            
            result = {
                "palm_center": [round(palm_x, 4), round(palm_y, 4)],
                "palm_center_px": [int(palm_x * w), int(palm_y * h)],
                "handedness": handedness
            }
            
            # Only send full landmarks if explicitly requested
            if self.settings.get("send_landmarks", False):
                result["landmarks"] = [[round(lm.x, 4), round(lm.y, 4)] for lm in hand]
            
            return result
            
        except Exception as e:
            print(f"[!] Hand detection error: {e}")
            return None
    
    def _encode_frame(self, frame: np.ndarray) -> str:
        """Encode frame to base64 JPEG string."""
        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Compress to JPEG
        quality = self.settings.get("frame_quality", 70)
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        # Base64 encode
        return base64.b64encode(buffer).decode('utf-8')
    
    async def _process_frame(self) -> dict:
        """Capture and process a single frame."""
        ret, frame = self.cap.read()
        if not ret:
            return {"error": "Camera read failed"}
        
        # Run detections
        yolo_detections = self._detect_hands_yolo(frame)
        face_data = self._detect_face_landmarks(frame)
        hand_data = self._detect_hand_landmarks(frame)
        
        # Build response
        response = {
            "type": "frame_data",
            "timestamp": time.time(),
            "fps": round(self.current_fps, 1),
            "frame_size": [frame.shape[1], frame.shape[0]],
            "detections": yolo_detections,
            "face": face_data,
            "hand": hand_data
        }
        
        # Optionally include frame data
        if self.settings.get("send_frames", True):
            response["frame_base64"] = self._encode_frame(frame)
        
        return response
    
    async def _handle_client_message(self, message: str):
        """Handle incoming message from Godot client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            
            if msg_type == "settings":
                # Update settings
                for key, value in data.items():
                    if key != "type" and key in self.settings:
                        self.settings[key] = value
                        print(f"[Settings] {key} = {value}")
            
            elif msg_type == "ping":
                # Respond with pong (for latency measurement)
                return json.dumps({"type": "pong", "timestamp": time.time()})
            
            elif msg_type == "get_jutsus":
                # Send jutsu registry
                return json.dumps({
                    "type": "jutsu_registry",
                    "jutsus": OFFICIAL_JUTSUS
                })
            
        except json.JSONDecodeError:
            print(f"[!] Invalid JSON: {message[:100]}")
        
        return None
    
    async def _client_handler(self, websocket):
        """Handle a single WebSocket client connection."""
        client_id = id(websocket)
        print(f"[+] Client connected: {client_id}")
        self.connected_clients.add(websocket)
        
        try:
            # Send initial connection info
            await websocket.send(json.dumps({
                "type": "connected",
                "server_version": "1.0.0",
                "jutsus": list(OFFICIAL_JUTSUS.keys()),
                "class_names": self.class_names
            }))
            
            # Main loop: receive messages, send frames
            while True:
                try:
                    # Check for incoming messages (non-blocking)
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=0.001  # 1ms timeout - effectively non-blocking
                        )
                        response = await self._handle_client_message(message)
                        if response:
                            await websocket.send(response)
                    except asyncio.TimeoutError:
                        pass  # No message, continue
                    
                    # Process and send frame
                    frame_data = await self._process_frame()
                    await websocket.send(json.dumps(frame_data))
                    
                    # FPS tracking
                    self.fps_counter += 1
                    elapsed = time.time() - self.fps_start_time
                    if elapsed >= 1.0:
                        self.current_fps = self.fps_counter / elapsed
                        self.fps_counter = 0
                        self.fps_start_time = time.time()
                    
                    # Minimal yield to allow other tasks
                    await asyncio.sleep(0.001)
                    
                except websockets.ConnectionClosed:
                    break
                    
        except Exception as e:
            print(f"[!] Client error: {e}")
        finally:
            self.connected_clients.discard(websocket)
            print(f"[-] Client disconnected: {client_id}")
    
    async def start(self, host: str = "127.0.0.1", port: int = 8765):
        """Start the WebSocket server."""
        self.running = True
        
        print(f"\n{'═' * 50}")
        print(f"  🎮 JUTSU ACADEMY BACKEND SERVER")
        print(f"{'═' * 50}")
        print(f"  WebSocket: ws://{host}:{port}")
        print(f"  Camera:    {self.camera_index}")
        print(f"  YOLO:      {len(self.class_names)} classes")
        print(f"  Face:      {'✓' if self.face_landmarker else '✗'}")
        print(f"  Hand:      {'✓' if self.hand_landmarker else '✗'}")
        print(f"{'═' * 50}")
        print(f"  Press Ctrl+C to stop\n")
        
        async with websockets.serve(self._client_handler, host, port):
            await asyncio.Future()  # Run forever
    
    def cleanup(self):
        """Release resources."""
        if self.cap:
            self.cap.release()
        print("[*] Backend server stopped.")


async def main():
    parser = argparse.ArgumentParser(description="Jutsu Academy Backend Server")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--weights", type=str, default=None, help="YOLO weights path")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    args = parser.parse_args()
    
    server = None
    try:
        server = JutsuBackendServer(
            camera_index=args.camera,
            model_path=args.weights
        )
        await server.start(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        if server:
            server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
