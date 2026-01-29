
import cv2
import cvzone
import time
import math
import argparse
from pathlib import Path
from ultralytics import YOLO
import mediapipe as mp
import numpy as np
import pygame  # For sound effects

# Add parent path to import utils
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils.paths import get_class_names, get_latest_weights
from src.utils.visualization import draw_detection_box, create_class_color_map

class FireballJutsuTrainer:
    def __init__(self, model_path, camera_index=0):
        # Initialize YOLO
        print(f"[*] Loading YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        self.class_names = get_class_names()
        self.color_map = create_class_color_map(self.class_names)
        
        # Initialize MediaPipe Face Landmarker (Tasks API)
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        model_path_mp = "models/face_landmarker.task"
        self.face_landmarker = None
        self.face_cascade = None
        
        # Try MediaPipe Face first (silently)
        try:
            if Path(model_path_mp).exists():
                base_options = python.BaseOptions(model_asset_path=model_path_mp)
                options = vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
                self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
                print("[+] Face detection: MediaPipe")
        except Exception:
            pass  # Silently fall through to Haar
        
        # Initialize MediaPipe Hands (Tasks API)
        hand_model_path = "models/hand_landmarker.task"
        self.hand_landmarker = None
        try:
            if Path(hand_model_path).exists():
                base_options = python.BaseOptions(model_asset_path=hand_model_path)
                options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
                self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
                print("[+] Hand tracking: MediaPipe")
        except Exception as e:
            print(f"[!] Hand tracking failed: {e}")
        
        # Fallback to Haar Cascade
        if self.face_landmarker is None:
            try:
                haarcascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(haarcascade_path)
                if not self.face_cascade.empty():
                    print("[+] Face detection: Haar Cascade")
                else:
                    self.face_cascade = None
                    print("[!] Face detection: Disabled (no detector available)")
            except Exception:
                print("[!] Face detection: Disabled (no detector available)")
                
        # UI State
        self.show_settings = False
        self.setting_buttons = []
        
        # Initialize Camera (lower res for better perf)
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # FPS tracking
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0
        
        # Load Assets
        self.pics_dir = Path("src/pics")
        self.fire_img = cv2.imread(str(self.pics_dir / "fire.png"), cv2.IMREAD_UNCHANGED)
        
        # Define Available Jutsu Sequences
        # Each jutsu has: sequence, effect type, and signature sound file
        self.jutsu_list = {
            "Fireball": {
                "sequence": ["horse", "snake", "ram", "monkey", "boar", "horse", "tiger"],
                "effect": "fire",
                "sound": "fireball.mp3"  # src/sounds/fireball.mp3
            },
            "Chidori": {
                "sequence": ["ox", "hare", "monkey"],
                "effect": "lightning",
                "sound": "chidori.mp3"
            },
            "Water Dragon": {
                "sequence": ["ox", "monkey", "hare", "rat", "boar", "bird", "ox", "horse", "bird"],
                "effect": "water",
                "sound": "water_dragon.mp3"
            },
            "Shadow Clone": {
                "sequence": ["ram", "snake", "tiger"],
                "effect": "clone",
                "sound": "shadow_clone.mp3"
            },
            "Phoenix Flower": {
                "sequence": ["rat", "tiger", "dog", "ox", "hare", "tiger"],
                "effect": "fire",
                "sound": "phoenix_flower.mp3"
            }
        }
        
        # Current jutsu selection
        self.jutsu_names = list(self.jutsu_list.keys())
        self.current_jutsu_idx = 0
        self.sequence = self.jutsu_list[self.jutsu_names[0]]["sequence"]
        
        # Load Icons (for all possible hand signs across all jutsu)
        self.icons = {}
        all_signs = set()
        for jutsu in self.jutsu_list.values():
            all_signs.update(jutsu["sequence"])
        
        for name in all_signs:
            # Try loading real PIC first (.jpeg), then fallback to icon (.png)
            img = None
            for ext in [".jpeg", ".jpg", ".png"]:
                icon_path = self.pics_dir / f"{name}{ext}"
                if icon_path.exists():
                     img = cv2.imread(str(icon_path))
                     break
            
            if img is not None:
                # Convert to BGRA (4 channels) for cvzone
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                self.icons[name] = img
            else:
                print(f"[!] {name} icon missing")
        
        # State
        self.current_step = 0
        self.last_sign_time = 0
        self.cooldown = 0.5 # Seconds between steps
        self.jutsu_active = False
        self.jutsu_start_time = 0
        self.jutsu_duration = 5.0 # How long fire lasts
        
        # Settings (toggleable in Settings menu)
        self.show_bounding_box = True   # Boxes: Shows detection boxes (default ON)
        self.show_face_mesh = False     # Face Mesh: Shows face wireframe (default OFF)
        self.show_detection_region = False  # Detection zone overlay
        self.show_effects = True        # Effects: Fire and future effects (default ON)
        self.show_hand_mesh = True     # Hand Mesh: Shows hand landmarks (default ON)
        
        # Advanced Volume Controls
        self.vol_master = 0.7
        self.vol_each = 1.0     # Boosted by default
        self.vol_complete = 0.7
        self.vol_signature = 0.7
        
        # Initialize Sound
        pygame.mixer.init()
        self.sounds_dir = Path("src/sounds")
        self.sound_each = None
        self.sound_complete = None  # Default completion sound (fallback)
        self.jutsu_sounds = {}  # Per-jutsu signature sounds
        self.last_hand_center = None # Track hand position for effects
        
        try:
            # Load "each" sound (for each correct sign)
            if (self.sounds_dir / "each.mp3").exists():
                self.sound_each = pygame.mixer.Sound(str(self.sounds_dir / "each.mp3"))
            
            # Load default complete sound (fallback)
            if (self.sounds_dir / "complete.mp3").exists():
                self.sound_complete = pygame.mixer.Sound(str(self.sounds_dir / "complete.mp3"))
            
            # Load per-jutsu signature sounds
            for jutsu_name, jutsu_data in self.jutsu_list.items():
                sound_file = jutsu_data.get("sound", "")
                sound_path = self.sounds_dir / sound_file
                if sound_path.exists():
                    self.jutsu_sounds[jutsu_name] = pygame.mixer.Sound(str(sound_path))
                    print(f"[+] Loaded signature sound: {sound_file}")
            
            print("[+] Sound effects loaded")
        except Exception as e:
            print(f"[!] Could not load sounds: {e}")

        # ... (rest of init) ...

    def play_sound(self, sound_type):
        """Play sound with granular volume control (Master * Specific)."""
        if sound_type == "each" and self.sound_each:
            self.sound_each.stop()
            channel = self.sound_each.play()
            if channel:
                # Effective volume = Master * Each
                channel.set_volume(self.vol_master * self.vol_each)
                
        elif sound_type == "complete":
            # 1. Play Default Complete Sound (if enabled)
            if self.sound_complete:
                self.sound_complete.stop()
                channel = self.sound_complete.play()
                if channel:
                    channel.set_volume(self.vol_master * self.vol_complete)
                    
        elif sound_type == "signature":
            # 2. Play Signature Sound (if exists)
            current_jutsu = self.jutsu_names[self.current_jutsu_idx]
            if current_jutsu in self.jutsu_sounds:
                sound = self.jutsu_sounds[current_jutsu]
                channel = sound.play()
                if channel:
                    channel.set_volume(self.vol_master * self.vol_signature)

    def detect_hands_mediapipe(self, frame):
        """Use MediaPipe to get generic hand position (wrist/palm)."""
        if not self.hand_landmarker:
            return None
            
        try:
            # MediaPipe tasks expect RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detect
            detection_result = self.hand_landmarker.detect(mp_image)
            
            if detection_result.hand_landmarks:
                # print(f"MP detected hand (Confidence: {detection_result.handedness[0][0].score:.2f})")
                # Get the first hand
                hand_landmarks = detection_result.hand_landmarks[0]
                
                # Use Wrist (0) and Middle Finger MCP (9) average for center
                wrist = hand_landmarks[0]
                middle_mcp = hand_landmarks[9]
                
                h, w = frame.shape[:2]
                cx = int((wrist.x + middle_mcp.x) / 2 * w)
                cy = int((wrist.y + middle_mcp.y) / 2 * h)
                
                # Draw Hand Mesh if enabled
                if self.show_hand_mesh:
                    # Draw joints
                    for lm in hand_landmarks:
                        px, py = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (px, py), 2, (0, 255, 255), -1)
                    
                    # Draw connections (simple approximation for now)
                    # Thumb
                    for i in range(1, 4):
                        p1 = (int(hand_landmarks[i].x * w), int(hand_landmarks[i].y * h))
                        p2 = (int(hand_landmarks[i+1].x * w), int(hand_landmarks[i+1].y * h))
                        cv2.line(frame, p1, p2, (0, 255, 255), 1)
                    # Fingers
                    for base in [5, 9, 13, 17]:
                        for i in range(base, base+3):
                            p1 = (int(hand_landmarks[i].x * w), int(hand_landmarks[i].y * h))
                            p2 = (int(hand_landmarks[i+1].x * w), int(hand_landmarks[i+1].y * h))
                            cv2.line(frame, p1, p2, (0, 255, 255), 1)
                        # Palm base to finger
                        p_wrist = (int(wrist.x * w), int(wrist.y * h))
                        p_base = (int(hand_landmarks[base].x * w), int(hand_landmarks[base].y * h))
                        cv2.line(frame, p_wrist, p_base, (0, 255, 255), 1)
                
                return (cx, cy)
            else:
                # print("MP ran but found no hands")
                pass
                
        except Exception as e:
            print(f"MP Hand Error: {e}")
            pass
            
        return None

    def detect_hands(self, frame):
        # Run YOLO with smaller inference size for speed
        results = self.model(frame, stream=True, verbose=False, imgsz=320)
        detected_class = None
        highest_conf = 0.0
        self.last_hand_center = None # Reset unless found
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = box.conf[0]
                cls = int(box.cls[0])
                current_class = self.class_names[cls]
                
                # Get Box Params
                x1, y1, x2, y2 = box.xyxy[0]
                bbox = (int(x1), int(y1), int(x2), int(y2))
                
                # Store hand center for effects
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                self.last_hand_center = (cx, cy)
                
                # Use Visualization Util
                if current_class in self.color_map:
                    color = self.color_map[current_class]
                else:
                    color = (0, 255, 0)
                
                # Only draw if bounding box visibility is enabled
                if self.show_bounding_box:
                    draw_detection_box(frame, bbox, current_class, conf, box_color=color)
                
                if conf > 0.5 and conf > highest_conf:
                    highest_conf = conf
                    detected_class = current_class
        
        # Fallback: If YOLO didn't find a hand (sign), use MediaPipe Hands
        if self.last_hand_center is None:
            mp_center = self.detect_hands_mediapipe(frame)
            if mp_center:
                self.last_hand_center = mp_center
        
        # Draw detection region if enabled
        if self.show_detection_region:
            h, w = frame.shape[:2]
            # Define a center region where detection is highlighted
            margin_x, margin_y = int(w * 0.15), int(h * 0.1)
            cv2.rectangle(frame, (margin_x, margin_y), (w - margin_x, h - margin_y), 
                         (255, 200, 0), 2)
            cv2.putText(frame, "Detection Zone", (margin_x + 5, margin_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
                    
        return frame, detected_class

    def draw_ui_panel(self, cam_width):
        """Create a separate UI panel below the camera feed."""
        panel_height = 150
        panel = np.zeros((panel_height, cam_width, 3), dtype=np.uint8)
        panel[:] = (40, 40, 40)  # Dark gray background
        
        h, w, _ = panel.shape
        
        # Settings for icons
        icon_size = 80
        gap = 20
        total_width = len(self.sequence) * (icon_size + gap) - gap
        start_x = (w - total_width) // 2
        y_pos = (h - icon_size) // 2
        
        for i, sign_name in enumerate(self.sequence):
            x = start_x + i * (icon_size + gap)
            
            if sign_name in self.icons:
                # Use INTER_AREA for high-quality image shrinking
                icon = cv2.resize(self.icons[sign_name], (icon_size, icon_size), interpolation=cv2.INTER_AREA)
                
                # State Logic
                if i < self.current_step:
                    # Completed - Grey out
                    b, g, r, a = cv2.split(icon)
                    gray = cv2.cvtColor(cv2.merge([b, g, r]), cv2.COLOR_BGR2GRAY)
                    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                    gray_bgr = (gray_bgr * 0.5).astype(np.uint8)
                    icon = cv2.merge([gray_bgr[:,:,0], gray_bgr[:,:,1], gray_bgr[:,:,2], a])
                    cv2.rectangle(panel, (x, y_pos), (x+icon_size, y_pos+icon_size), (0, 255, 0), 2)
                    
                elif i == self.current_step and not self.jutsu_active:
                    # Current target - Highlight
                    cv2.rectangle(panel, (x-5, y_pos-5), (x+icon_size+5, y_pos+icon_size+5), (0, 165, 255), 3)
                
                panel = cvzone.overlayPNG(panel, icon, [x, y_pos])
        
        # Instructions text
        if self.jutsu_active:
            cv2.putText(panel, "KATON: GOUKAKYUU NO JUTSU!", (w//2 - 220, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        else:
            target = self.sequence[self.current_step]
            cv2.putText(panel, f"Next: {target.upper()}", (w//2 - 80, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        return panel

    def render_effect(self, frame):
        face_found = False
        cx, cy = 0, 0
        
        if self.face_landmarker:
            # MediaPipe Logic
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            detection_result = self.face_landmarker.detect(mp_image)
            if detection_result.face_landmarks:
                face = detection_result.face_landmarks[0]
                h, w, c = frame.shape
                
                # Draw face mesh if enabled
                if self.show_face_mesh:
                    # MediaPipe Face Mesh Tessellation connections
                    # These are the face mesh triangulation indices for drawing the mesh
                    FACE_CONNECTIONS = [
                        # Face oval
                        (10, 338), (338, 297), (297, 332), (332, 284), (284, 251), (251, 389),
                        (389, 356), (356, 454), (454, 323), (323, 361), (361, 288), (288, 397),
                        (397, 365), (365, 379), (379, 378), (378, 400), (400, 377), (377, 152),
                        (152, 148), (148, 176), (176, 149), (149, 150), (150, 136), (136, 172),
                        (172, 58), (58, 132), (132, 93), (93, 234), (234, 127), (127, 162),
                        (162, 21), (21, 54), (54, 103), (103, 67), (67, 109), (109, 10),
                        # Left eyebrow
                        (70, 63), (63, 105), (105, 66), (66, 107), (107, 55), (55, 65),
                        (65, 52), (52, 53), (53, 46),
                        # Right eyebrow  
                        (300, 293), (293, 334), (334, 296), (296, 336), (336, 285), (285, 295),
                        (295, 282), (282, 283), (283, 276),
                        # Left eye
                        (33, 7), (7, 163), (163, 144), (144, 145), (145, 153), (153, 154),
                        (154, 155), (155, 133), (133, 173), (173, 157), (157, 158), (158, 159),
                        (159, 160), (160, 161), (161, 246), (246, 33),
                        # Right eye
                        (263, 249), (249, 390), (390, 373), (373, 374), (374, 380), (380, 381),
                        (381, 382), (382, 362), (362, 398), (398, 384), (384, 385), (385, 386),
                        (386, 387), (387, 388), (388, 466), (466, 263),
                        # Lips outer
                        (61, 146), (146, 91), (91, 181), (181, 84), (84, 17), (17, 314),
                        (314, 405), (405, 321), (321, 375), (375, 291), (291, 61),
                        # Lips inner
                        (78, 95), (95, 88), (88, 178), (178, 87), (87, 14), (14, 317),
                        (317, 402), (402, 318), (318, 324), (324, 308), (308, 78),
                        # Nose
                        (168, 6), (6, 197), (197, 195), (195, 5), (5, 4), (4, 1),
                        (1, 19), (19, 94), (94, 2), (2, 164),
                    ]
                    
                    # Draw all connections (cyan lines)
                    for start_idx, end_idx in FACE_CONNECTIONS:
                        if start_idx < len(face) and end_idx < len(face):
                            x1 = int(face[start_idx].x * w)
                            y1 = int(face[start_idx].y * h)
                            x2 = int(face[end_idx].x * w)
                            y2 = int(face[end_idx].y * h)
                            cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 0), 1)  # Cyan
                    
                    # Draw all landmark points (cyan dots)
                    for i, lm in enumerate(face):
                        px, py = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (px, py), 1, (255, 255, 0), -1)  # Cyan dots
                
                # Get mouth position for fire
                id_mouth = 13
                cx, cy = int(face[id_mouth].x * w), int(face[id_mouth].y * h)
                face_found = True
                 
        elif hasattr(self, 'face_cascade') and self.face_cascade:
            # Haar Logic (no mesh available, just face box)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            if len(faces) > 0:
                # Take largest face
                faces = sorted(faces, key=lambda b: b[2]*b[3], reverse=True)
                x, y, fw, fh = faces[0]
                
                # Draw face rectangle if mesh view enabled
                if self.show_face_mesh:
                    cv2.rectangle(frame, (x, y), (x+fw, y+fh), (0, 255, 0), 2)
                    cv2.putText(frame, "Face", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Estimate mouth position
                cx = x + fw // 2
                cy = y + fh - (fh // 4)
                face_found = True

        # Render Dynamic Effects if active
        if face_found and self.jutsu_active and self.show_effects:
            current_jutsu = self.jutsu_names[self.current_jutsu_idx]
            effect_type = self.jutsu_list[current_jutsu]["effect"]
            
            # Determine effect position
            # Default to mouth (face) position
            effect_x, effect_y = cx, cy
            
            # For hand-based jutsu, use hand position if available
            if effect_type in ["lightning", "water"] and self.last_hand_center:
                effect_x, effect_y = self.last_hand_center
            
            if effect_type == "fire":
                # Fireball always comes from mouth (face cx, cy)
                fire_w, fire_h = 250, 250
                pos = [cx - fire_w//2, cy - fire_h//2 + 50] 
                try:
                    fire_resized = cv2.resize(self.fire_img, (fire_w, fire_h), interpolation=cv2.INTER_CUBIC)
                    frame = cvzone.overlayPNG(frame, fire_resized, pos)
                except Exception:
                    pass
                    
            elif effect_type == "lightning":
                # Render Lightning on hand (or face if hand missing)
                cv2.circle(frame, (effect_x, effect_y), 80, (255, 255, 0), 3)
                cv2.putText(frame, "CHIDORI!", (effect_x-70, effect_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
                
            elif effect_type == "water":
                # Render Water on hand (or face if hand missing)
                cv2.circle(frame, (effect_x, effect_y), 100, (255, 0, 0), 4)
                cv2.putText(frame, "WATER DRAGON!", (effect_x-120, effect_y+120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                
            elif effect_type == "clone":
                # Render Clone Text around face
                cv2.putText(frame, "KAGE BUNSHIN!", (cx-120, cy-120), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 3)
                
        return frame

    def draw_settings_ui(self, frame):
        h, w, _ = frame.shape
        
        # Draw Settings Toggle Button (Top Right)
        btn_color = (100, 100, 100)
        cv2.rectangle(frame, (w-150, 10), (w-10, 50), btn_color, -1)
        cv2.putText(frame, "SETTINGS", (w-140, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        if self.show_settings:
            # Draw Overlay Menu (larger to fit all controls)
            overlay = frame.copy()
            menu_x, menu_y = w//2-200, h//2-250
            menu_w, menu_h = 400, 500
            cv2.rectangle(overlay, (menu_x, menu_y), (menu_x+menu_w, menu_y+menu_h), (30, 30, 30), -1)
            cv2.rectangle(overlay, (menu_x, menu_y), (menu_x+menu_w, menu_y+menu_h), (100, 100, 100), 2)
            frame = cv2.addWeighted(overlay, 0.9, frame, 0.1, 0)
            
            self.setting_buttons = []
            
            # Title
            cv2.putText(frame, "SETTINGS", (w//2-60, menu_y+30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # --- Toggles (Grid) ---
            t_w, t_h = 170, 30
            t_x1, t_x2 = menu_x + 20, menu_x + 210
            t_y1, t_y2, t_y3 = menu_y + 50, menu_y + 90, menu_y + 130
            
            # Row 1: Boxes, Face Mesh
            # 1. Boxes (Top Left)
            color = (0, 180, 0) if self.show_bounding_box else (80, 80, 80)
            cv2.rectangle(frame, (t_x1, t_y1), (t_x1+t_w, t_y1+t_h), color, -1)
            cv2.putText(frame, f"Boxes", (t_x1+10, t_y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            self.setting_buttons.append(("toggle_bbox", (t_x1, t_y1, t_w, t_h)))

            # 2. Face (Top Right)
            color = (0, 180, 0) if self.show_face_mesh else (80, 80, 80)
            cv2.rectangle(frame, (t_x2, t_y1), (t_x2+t_w, t_y1+t_h), color, -1)
            cv2.putText(frame, f"Face Mesh", (t_x2+10, t_y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            self.setting_buttons.append(("toggle_face", (t_x2, t_y1, t_w, t_h)))

            # Row 2: Hand Mesh, Detect Zone
            # 3. Hand Mesh (Left)
            color = (0, 180, 0) if self.show_hand_mesh else (80, 80, 80)
            cv2.rectangle(frame, (t_x1, t_y2), (t_x1+t_w, t_y2+t_h), color, -1)
            cv2.putText(frame, f"Hand Mesh", (t_x1+10, t_y2+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            self.setting_buttons.append(("toggle_hand", (t_x1, t_y2, t_w, t_h)))

            # 4. Zone (Right)
            color = (0, 180, 0) if self.show_detection_region else (80, 80, 80)
            cv2.rectangle(frame, (t_x2, t_y2), (t_x2+t_w, t_y2+t_h), color, -1)
            cv2.putText(frame, f"Detect Zone", (t_x2+10, t_y2+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            self.setting_buttons.append(("toggle_region", (t_x2, t_y2, t_w, t_h)))

            # Row 3: Effects
            # 5. Effects (Left)
            color = (0, 180, 0) if self.show_effects else (80, 80, 80)
            cv2.rectangle(frame, (t_x1, t_y3), (t_x1+t_w, t_y3+t_h), color, -1)
            cv2.putText(frame, f"Effects", (t_x1+10, t_y3+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            self.setting_buttons.append(("toggle_effects", (t_x1, t_y3, t_w, t_h)))

            # Separator (Shifted down)
            cv2.line(frame, (menu_x+20, menu_y+175), (menu_x+menu_w-20, menu_y+175), (100, 100, 100), 1)
            
            # --- Volume Sliders (x4) ---
            # Helper to draw slider
            def draw_slider(name, label, val, y_pos):
                s_x, s_w = menu_x + 100, menu_w - 120
                s_h = 20
                
                # Label
                cv2.putText(frame, label, (menu_x+20, y_pos+15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                # Track
                cv2.rectangle(frame, (s_x, y_pos), (s_x+s_w, y_pos+s_h), (60, 60, 60), -1)
                # Fill
                fill_w = int(s_w * val)
                cv2.rectangle(frame, (s_x, y_pos), (s_x+fill_w, y_pos+s_h), (0, 150, 255), -1)
                # Handle
                cv2.circle(frame, (s_x+fill_w, y_pos+10), 8, (255, 255, 255), -1)
                
                self.setting_buttons.append((name, (s_x, y_pos, s_w, s_h)))

            draw_slider("vol_master", "Master", self.vol_master, menu_y + 190)
            draw_slider("vol_each",   "Each", self.vol_each,   menu_y + 230)
            draw_slider("vol_done",   "Done", self.vol_complete, menu_y + 270)
            draw_slider("vol_sign",   "Sign", self.vol_signature, menu_y + 310)
            # Separator
            cv2.line(frame, (menu_x+20, menu_y+340), (menu_x+menu_w-20, menu_y+340), (100, 100, 100), 1)
            
            # Jutsu Selector
            by = menu_y + 360
            current_jutsu = self.jutsu_names[self.current_jutsu_idx]
            cv2.putText(frame, "Jutsu:", (menu_x+30, by+22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Left arrow
            cv2.rectangle(frame, (menu_x+100, by+5), (menu_x+130, by+30), (80, 80, 80), -1)
            cv2.putText(frame, "<", (menu_x+108, by+25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            self.setting_buttons.append(("jutsu_prev", (menu_x+100, by+5, 30, 25)))
            
            # Jutsu name
            jutsu_text = current_jutsu
            text_size = cv2.getTextSize(jutsu_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            text_x = menu_x + 140 + (menu_w - 180 - text_size[0]) // 2
            cv2.putText(frame, jutsu_text, (text_x, by+22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            
            # Right arrow
            cv2.rectangle(frame, (menu_x+menu_w-50, by+5), (menu_x+menu_w-20, by+30), (80, 80, 80), -1)
            cv2.putText(frame, ">", (menu_x+menu_w-42, by+25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            self.setting_buttons.append(("jutsu_next", (menu_x+menu_w-50, by+5, 30, 25)))
            
            # Separator
            cv2.line(frame, (menu_x+20, menu_y+400), (menu_x+menu_w-20, menu_y+400), (100, 100, 100), 1)
            
            # Reset Button
            by = menu_y + 410
            bw, bh = 150, 40
            cv2.rectangle(frame, (menu_x+20, by), (menu_x+20+bw, by+bh), (0, 100, 255), -1)
            cv2.putText(frame, "RESET", (menu_x+60, by+24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            self.setting_buttons.append(("Reset", (menu_x+20, by, bw, bh)))
            
            # Exit Button (on the right side)
            cv2.rectangle(frame, (menu_x+menu_w-20-bw, by), (menu_x+menu_w-20, by+bh), (0, 0, 200), -1)
            cv2.putText(frame, "EXIT", (menu_x+menu_w-20-bw+45, by+24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            self.setting_buttons.append(("Exit", (menu_x+menu_w-20-bw, by, bw, bh)))
            
        return frame

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            w_frame = 640  # Match camera width
            if x > w_frame - 150 and y < 60:
                self.show_settings = not self.show_settings
                return
            
            if self.show_settings:
                for btn in self.setting_buttons:
                    name, (bx, by, bw, bh) = btn
                    if bx < x < bx+bw and by < y < by+bh:
                        if name == "volume_slider":
                            # Calculate volume from click position
                            rel_x = x - bx
            if self.show_settings:
                for btn in self.setting_buttons:
                    name, (bx, by, bw, bh) = btn
                    if bx < x < bx+bw and by < y < by+bh:
                        if name.startswith("vol_"):
                            # Handle all volume sliders
                            rel_x = x - bx
                            new_vol = max(0.0, min(1.0, rel_x / bw))
                            
                            if name == "vol_master":
                                self.vol_master = new_vol
                                self._update_volume() # Update global volume immediately
                            elif name == "vol_each":
                                self.vol_each = new_vol
                            elif name == "vol_done":
                                self.vol_complete = new_vol
                            elif name == "vol_sign":
                                self.vol_signature = new_vol
                        else:
                            self.handle_setting_click(name)

    def handle_setting_click(self, name):
        print(f"[UI] Clicked {name}")
        if name == "toggle_bbox":
            self.show_bounding_box = not self.show_bounding_box
        elif name == "toggle_face":
            self.show_face_mesh = not self.show_face_mesh
        elif name == "toggle_hand":
            self.show_hand_mesh = not self.show_hand_mesh
        elif name == "toggle_region":
            self.show_detection_region = not self.show_detection_region
        elif name == "toggle_effects":
            self.show_effects = not self.show_effects
        elif name == "jutsu_prev":
            self.current_jutsu_idx = (self.current_jutsu_idx - 1) % len(self.jutsu_names)
            self._switch_jutsu()
        elif name == "jutsu_next":
            self.current_jutsu_idx = (self.current_jutsu_idx + 1) % len(self.jutsu_names)
            self._switch_jutsu()
        elif name == "Reset":
            self.current_step = 0
            self.jutsu_active = False
            self.show_settings = False
        elif name == "Exit":
            self.cap.release()
            cv2.destroyAllWindows()
            pygame.mixer.quit()
            sys.exit(0)
    
    def _switch_jutsu(self):
        """Switch to the currently selected jutsu."""
        jutsu_name = self.jutsu_names[self.current_jutsu_idx]
        self.sequence = self.jutsu_list[jutsu_name]["sequence"]
        self.current_step = 0
        self.jutsu_active = False
        print(f"[*] Switched to: {jutsu_name} ({len(self.sequence)} signs)")

    def run(self):
        print("[*] Starting Jutsu Trainer...")
        # Setup Mouse Callback
        cv2.namedWindow("Fireball Jutsu Trainer")
        cv2.setMouseCallback("Fireball Jutsu Trainer", self.mouse_callback)
        
        while True:
            ret, frame = self.cap.read()
            if not ret: break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            cam_h, cam_w = frame.shape[:2]
            
            # 1. Hand Detection & Logic (bounding boxes on camera)
            if not self.jutsu_active:
                frame, detected_class = self.detect_hands(frame)
                
                # Sequence Logic
                current_target = self.sequence[self.current_step]
                
                if detected_class == current_target:
                    current_time = time.time()
                    if current_time - self.last_sign_time > self.cooldown:
                        print(f"[+] Correct: {detected_class}")
                        self.current_step += 1
                        self.last_sign_time = current_time
                        self.play_sound("each")  # Play sound for each correct sign
                        
                        # Check Completion
                        if self.current_step >= len(self.sequence):
                            print("[!!!] JUTSU ACTIVATED [!!!]")
                            self.jutsu_active = True
                            self.jutsu_start_time = time.time()
                            self.current_step = 0 
                            self.play_sound("complete")  # Play default completion sound
                            self.signature_sound_played = False # Flag to play signature sound later
            
            # 2. Face Mesh & Fire Effect (runs always for mesh, fire only when active)
            frame = self.render_effect(frame)
            
            # Check for Delayed Signature Sound
            if self.jutsu_active and not self.signature_sound_played:
                if time.time() - self.jutsu_start_time >= 0.5:
                    self.play_sound("signature")
                    self.signature_sound_played = True
            
            # Check if jutsu duration expired
            if self.jutsu_active:
                if time.time() - self.jutsu_start_time > self.jutsu_duration:
                    self.jutsu_active = False
                    self.current_step = 0
                    print("[*] Jutsu finished.")

            # 3. Create UI Panel (separate from camera)
            ui_panel = self.draw_ui_panel(cam_w)
            
            # 4. Combine camera + UI panel vertically
            canvas = np.vstack([frame, ui_panel])
            
            # 5. Draw Settings UI on full canvas
            canvas = self.draw_settings_ui(canvas)
            
            # FPS Counter
            self.fps_frame_count += 1
            elapsed = time.time() - self.fps_start_time
            if elapsed >= 1.0:
                self.current_fps = self.fps_frame_count / elapsed
                self.fps_frame_count = 0
                self.fps_start_time = time.time()
            cv2.putText(canvas, f"FPS: {self.current_fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow("Fireball Jutsu Trainer", canvas)
            
            key = cv2.waitKey(1)
            if key == ord('q'):
                break
            elif key == ord('r'): 
                self.current_step = 0
                self.jutsu_active = False
                
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default=None, help="Path to best.pt")
    args = parser.parse_args()
    
    # Auto-find weights if not provided
    weights = args.weights
    if not weights:
        weights = get_latest_weights()
        
    if not weights:
        print("[-] No weights found. Please train model first.")
        sys.exit(1)
        
    trainer = FireballJutsuTrainer(weights)
    trainer.run()
