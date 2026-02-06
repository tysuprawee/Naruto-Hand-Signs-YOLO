import cv2
import mediapipe as mp
import numpy as np
import csv
import time
import math
from pathlib import Path

# MediaPipe Tasks API Imports (Fix for missing mediapipe.solutions)
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Constants
DATA_FILE = "src/mediapipe_signs_db.csv"
LABELS = ["Idle", "Tiger", "Ram", "Snake", "Horse", "Rat", "Boar", "Dog", "Bird", "Monkey", "Ox", "Dragon", "Hare"] 
MODEL_PATH = "models/hand_landmarker.task"

class SignRecorder:
    def __init__(self):
        self.mode = "PREDICT" # PREDICT or RECORD
        self.current_label_idx = 1 # Start with Tiger (Index 1), Idle is 0
        self.recording_frames = 0
        self.data_buffer = []
        
        # Delayed Record State
        self.countdown_start = 0
        self.is_counting_down = False
        self.is_auto_recording = False
        self.auto_record_start = 0
        
        # Ensure database exists
        if not Path(DATA_FILE).exists():
            with open(DATA_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                # Header: label, then 42 sets of (x,y,z) coords (21 per hand * 2 hands)
                header = ["label"] + [f"h1_{i}_{ax}" for i in range(21) for ax in "xyz"] + \
                                     [f"h2_{i}_{ax}" for i in range(21) for ax in "xyz"]
                writer.writerow(header)
                
        # Load simple KNN classifier if data exists
        self.knn = None
        self.knn_labels = []
        self._load_and_train()
    
    def _load_and_train(self):
        """Train a KNN model in memory if CSV has data."""
        try:
            if not Path(DATA_FILE).exists(): return
            with open(DATA_FILE, 'r') as f:
                reader = csv.reader(f)
                header = next(reader) # Skip header
                data = list(reader)
                
            if len(data) > 5:
                print(f"[+] Training on {len(data)} examples...")
                X = []
                y = []
                for row in data:
                    y.append(row[0])
                    coords = [float(x) for x in row[1:]]
                    X.append(coords)
                
                self.knn = cv2.ml.KNearest_create()
                self.knn_labels = list(set(y))
                self.knn_labels.sort()
                
                y_int = [self.knn_labels.index(lbl) for lbl in y]
                self.knn.train(np.array(X, dtype=np.float32), cv2.ml.ROW_SAMPLE, np.array(y_int, dtype=np.int32))
                print(f"[+] Training complete. Classes: {self.knn_labels}")
            else:
                print("[!] Not enough data to train yet. Record some signs!")
                self.knn = None
        except Exception as e:
            print(f"[!] Error loading DB: {e}")
            self.knn = None

    def process_tasks_landmarks(self, hand_landmarks, handedness):
        """
        Convert MP Tasks API results to a normalized feature vector (126 floats).
        """
        if not hand_landmarks:
            return [0.0] * 126
            
        h1_data = [0.0] * 63 
        h2_data = [0.0] * 63
        
        for idx, hands_list in enumerate(handedness):
            if idx >= len(hand_landmarks): break
            
            # Tasks API label is in category_name
            label = hands_list[0].category_name # "Left" or "Right"
            landmarks = hand_landmarks[idx] 
            
            coords = self._normalize_hand(landmarks)
                
            if label == "Left":
                h1_data = coords
            else:
                h2_data = coords
                
        return h1_data + h2_data

    def _normalize_hand(self, landmarks):
        """
        Double Normalization logic for a single hand (21 landmarks).
        """
        wrist = landmarks[0]
        middle_base = landmarks[9]
        
        dist = math.sqrt(
            (wrist.x - middle_base.x)**2 + 
            (wrist.y - middle_base.y)**2 + 
            (wrist.z - middle_base.z)**2
        )
        
        if dist < 0.0001: dist = 1.0 
        
        coords = []
        for lm in landmarks:
            norm_x = (lm.x - wrist.x) / dist
            norm_y = (lm.y - wrist.y) / dist
            norm_z = (lm.z - wrist.z) / dist
            coords.extend([norm_x, norm_y, norm_z])
            
        return coords

    def save_data(self):
        """Save buffered data to CSV."""
        if not self.data_buffer: return
        
        with open(DATA_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(self.data_buffer)
            
        print(f"[+] Saved {len(self.data_buffer)} samples for {LABELS[self.current_label_idx]}")
        self.data_buffer = []
        self._load_and_train() 

    def predict(self, features):
        if not self.knn: return "Unknown"
        sample = np.array([features], dtype=np.float32)
        ret, result, neighbours, dist = self.knn.findNearest(sample, k=3)
        min_dist = dist[0][0]
        
        if min_dist > 1.8:
            return "Idle"
            
        idx = int(result[0][0])
        if idx < len(self.knn_labels):
            return self.knn_labels[idx]
        return "Unknown"

def draw_hand_landmarks(image, hand_landmarks):
    """Manual drawing of hand landmarks since mp_drawing is missing."""
    if not hand_landmarks: return
    
    h, w, _ = image.shape
    CONNECTIONS = [
        (0,1), (1,2), (2,3), (3,4), # Thumb
        (0,5), (5,6), (6,7), (7,8), # Index
        (5,9), (9,10), (10,11), (11,12), # Middle
        (9,13), (13,14), (14,15), (15,16), # Ring
        (13,17), (17,18), (18,19), (19,20), # Pinky
        (0,17) # Palm base
    ]
    
    for landmarks in hand_landmarks:
        # Draw connections
        for start_idx, end_idx in CONNECTIONS:
            p1 = landmarks[start_idx]
            p2 = landmarks[end_idx]
            px1, py1 = int(p1.x * w), int(p1.y * h)
            px2, py2 = int(p2.x * w), int(p2.y * h)
            cv2.line(image, (px1, py1), (px2, py2), (0, 255, 0), 2)
            
        # Draw points
        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(image, (cx, cy), 4, (0, 0, 255), -1)

def main():
    # Setup Tasks API Detector
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.3,
        min_hand_presence_confidence=0.3,
        min_tracking_confidence=0.3
    )
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
         
    recorder = SignRecorder()
    
    print("\n" + "="*50)
    print("      MEDIAPIPE JUTSU RECORDER (TASKS API)")
    print("="*50)
    print(" [R] - Toggle RECORDING Mode")
    print(" [SPACE] - Countdown to Auto-Record")
    print(" [[] / []] - Prev/Next Label")
    print(" [0-9] - Quick Select Label")
    print(" [Q] - Quit")
    print("="*50)

    while cap.isOpened():
        success, image = cap.read()
        if not success: continue

        image = cv2.flip(image, 1)
        h, w, _ = image.shape
        
        # Convert BGR to RGB for MediaPipe
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        
        # Detect
        detection_result = detector.detect(mp_image)
        
        features = recorder.process_tasks_landmarks(
            detection_result.hand_landmarks, 
            detection_result.handedness
        )
        
        # Draw Landmarks
        draw_hand_landmarks(image, detection_result.hand_landmarks)
        
        # Logic
        current_label = LABELS[recorder.current_label_idx]
        raw_keys = cv2.waitKey(1) & 0xFF
        
        if raw_keys == ord('n') or raw_keys == ord(']'):
             recorder.current_label_idx = (recorder.current_label_idx + 1) % len(LABELS)
        elif raw_keys == ord('p') or raw_keys == ord('['):
             recorder.current_label_idx = (recorder.current_label_idx - 1) % len(LABELS)
        elif raw_keys == ord('0'):
             recorder.current_label_idx = 0 
        elif raw_keys >= ord('1') and raw_keys <= ord('9'):
             idx = raw_keys - ord('0') 
             if idx < len(LABELS): recorder.current_label_idx = idx
        elif raw_keys == ord('r'):
             if recorder.mode == "RECORD":
                 recorder.mode = "PREDICT"
                 recorder.save_data()
             else:
                 recorder.mode = "RECORD"
        elif raw_keys == ord('q'):
             break

        # Record VS Predict
        if recorder.mode == "RECORD":
            status_color = (0, 0, 255)
            status_text = f"RECORDING: {current_label}"
            
            if raw_keys == 32 and not recorder.is_counting_down and not recorder.is_auto_recording: # SPACE
                recorder.countdown_start = time.time()
                recorder.is_counting_down = True
            
            if recorder.is_counting_down:
                elapsed = time.time() - recorder.countdown_start
                remaining = 3.0 - elapsed
                if remaining > 0:
                    cv2.putText(image, f"{int(remaining)+1}", (w//2 - 50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 165, 255), 10)
                    cv2.putText(image, "GET READY...", (w//2 - 150, h//2 + 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                else:
                    recorder.is_counting_down = False
                    recorder.is_auto_recording = True
                    recorder.auto_record_start = time.time()
            
            if recorder.is_auto_recording:
                elapsed = time.time() - recorder.auto_record_start
                if elapsed < 10.0:
                    if features:
                         recorder.data_buffer.append([current_label] + features)
                    
                    if int(elapsed * 10) % 2 == 0:
                        cv2.circle(image, (50, 100), 20, (0, 0, 255), -1)
                        
                    cv2.putText(image, "RECORDING!", (w//2 - 150, h//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
                    cv2.putText(image, f"Samples: {len(recorder.data_buffer)}", (w//2 - 100, h//2 + 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
                else:
                    recorder.is_auto_recording = False
                    recorder.save_data()
                    print(f"[+] Batch complete for {current_label}. Press SPACE for next batch.")

        else: # PREDICT MODE
            status_color = (0, 255, 0)
            status_text = "PREDICT MODE (Press R to Record)"
            
            if features:
                prediction = recorder.predict(features)
                cv2.putText(image, f"JUTSU: {prediction}", (50, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

        # UI Overlay
        cv2.rectangle(image, (0,0), (w, 60), (0,0,0), -1)
        cv2.putText(image, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        sidebar_x = w - 180
        cv2.rectangle(image, (sidebar_x - 10, 70), (w - 5, 70 + (len(LABELS) * 25) + 10), (0,0,0), 1)
        for i, lbl in enumerate(LABELS):
            color = (255, 255, 255)
            if i == recorder.current_label_idx:
                color = (0, 255, 255)
                cv2.rectangle(image, (sidebar_x - 5, 75 + i*25), (w - 10, 100 + i*25), (50, 50, 50), -1)
            cv2.putText(image, f"[{i}] {lbl}", (sidebar_x, 95 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        cv2.imshow('MediaPipe Jutsu Trainer', image)

    detector.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
