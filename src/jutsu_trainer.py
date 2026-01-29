
import cv2
import cvzone
import time
import math
import argparse
from pathlib import Path
from ultralytics import YOLO
import mediapipe as mp
import numpy as np

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
        
        # Initialize MediaPipe Face Mesh (for mouth detection)
        import mediapipe as mp
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(max_num_faces=1)
        
        # Initialize Camera
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(3, 1280) # Width
        self.cap.set(4, 720)  # Height
        
        # Load Assets
        self.pics_dir = Path("src/pics")
        self.fire_img = cv2.imread(str(self.pics_dir / "fire.png"), cv2.IMREAD_UNCHANGED)
        
        # Define the Jutsu Sequence
        self.sequence = ["horse", "snake", "ram", "monkey", "boar", "horse", "tiger"]
        
        # Load Icons
        self.icons = {}
        for name in set(self.sequence):
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
        
    def detect_hands(self, frame):
        # Run YOLO
        results = self.model(frame, stream=True, verbose=False)
        detected_class = None
        highest_conf = 0.0
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = box.conf[0]
                cls = int(box.cls[0])
                current_class = self.class_names[cls]
                
                # Get Box Params
                x1, y1, x2, y2 = box.xyxy[0]
                bbox = (int(x1), int(y1), int(x2), int(y2))
                
                # Use Visualization Util
                if current_class in self.color_map:
                    color = self.color_map[current_class]
                else:
                    color = (0, 255, 0)
                    
                draw_detection_box(frame, bbox, current_class, conf, box_color=color)
                
                if conf > 0.5 and conf > highest_conf:
                    highest_conf = conf
                    detected_class = current_class
                    
        return frame, detected_class

    def draw_guide_ui(self, frame):
        h, w, _ = frame.shape
        
        # Settings for icons
        icon_size = 80
        gap = 20
        total_width = len(self.sequence) * (icon_size + gap) - gap
        start_x = (w - total_width) // 2
        y_pos = h - icon_size - 40
        
        for i, sign_name in enumerate(self.sequence):
            x = start_x + i * (icon_size + gap)
            
            if sign_name in self.icons:
                icon = cv2.resize(self.icons[sign_name], (icon_size, icon_size))
                
                # State Logic
                # If completed (i < current_step): Grey out
                if i < self.current_step:
                    # Separate Alpha channel
                    b, g, r, a = cv2.split(icon)
                    
                    # Convert BGR to Gray
                    gray = cv2.cvtColor(cv2.merge([b, g, r]), cv2.COLOR_BGR2GRAY)
                    
                    # Darken and convert back to 3 channels
                    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                    gray_bgr = (gray_bgr * 0.5).astype(np.uint8)
                    
                    # Merge back with original alpha
                    icon = cv2.merge([gray_bgr[:,:,0], gray_bgr[:,:,1], gray_bgr[:,:,2], a])
                    
                    # Add Checkmark
                    cv2.rectangle(frame, (x, y_pos), (x+icon_size, y_pos+icon_size), (0, 255, 0), 2)
                    
                elif i == self.current_step and not self.jutsu_active:
                    # Current target - Highlight Box
                     cv2.rectangle(frame, (x-5, y_pos-5), (x+icon_size+5, y_pos+icon_size+5), (0, 165, 255), 3)
                
                frame = cvzone.overlayPNG(frame, icon, [x, y_pos])
                
        # Instructions
        if self.jutsu_active:
             cvzone.putTextRect(frame, "KATON: GOUKAKYUU NO JUTSU!", (w//2 - 200, 100), scale=2, thickness=2, colorR=(0, 0, 255))
        else:
             target = self.sequence[self.current_step]
             cvzone.putTextRect(frame, f"Next: {target.upper()}", (w//2 - 100, y_pos - 30), scale=1.5, thickness=2)

        return frame

    def render_fire(self, frame):
        # Convert to RGB for MediaPipe
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(img_rgb)
        
        if results.multi_face_landmarks:
            face = results.multi_face_landmarks[0]
            
            # Mouth Landmarks (Upper and Lower lip centers approx)
            # 13 is upper lip, 14 is lower lip
            # We can use 13 as the emitter point
            id_mouth = 13
            
            h, w, c = frame.shape
            cx, cy = int(face.landmark[id_mouth].x * w), int(face.landmark[id_mouth].y * h)
            
            # Overlay Fire
            # Calculate size based on face depth (optional, fixed for now)
            fire_w, fire_h = 250, 250
            pos = [cx - fire_w//2, cy - fire_h//2 + 50] # Offset slightly down? Actually fire should come OUT.
            # Let's align it so the start of the fire is at the mouth
            
            # Assuming fire.png is a circle/ball, center it on mouth
            
            try:
                # Resize fire if needed
                fire_resized = cv2.resize(self.fire_img, (fire_w, fire_h))
                frame = cvzone.overlayPNG(frame, fire_resized, pos)
            except Exception as e:
                pass # Depending on proximity to edge, cvzone might error
                
        return frame

    def run(self):
        print("[*] Starting Jutsu Trainer...")
        while True:
            ret, frame = self.cap.read()
            if not ret: break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            
            # 1. Hand Detection & Logic
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
                        
                        # Check Completion
                        if self.current_step >= len(self.sequence):
                            print("[!!!] JUTSU ACTIVATED [!!!]")
                            self.jutsu_active = True
                            self.jutsu_start_time = time.time()
                            self.current_step = 0 # Reset or hold?
            
            # 2. Draw UI
            frame = self.draw_guide_ui(frame)
            
            # 3. Fire Effect (if active)
            if self.jutsu_active:
                frame = self.render_fire(frame)
                
                # Check duration
                if time.time() - self.jutsu_start_time > self.jutsu_duration:
                    self.jutsu_active = False
                    self.current_step = 0
                    print("[*] Jutsu finished.")
            
            cv2.imshow("Fireball Jutsu Trainer", frame)
            
            key = cv2.waitKey(1)
            if key == ord('q'):
                break
            elif key == ord('r'): # Reset
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
