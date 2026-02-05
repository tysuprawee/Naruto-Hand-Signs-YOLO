import cv2
import mediapipe as mp
import numpy as np
import csv
import time
from pathlib import Path

# Setup MediaPipe
import mediapipe.python.solutions as mp_solutions
mp_hands = mp_solutions.hands
mp_drawing = mp_solutions.drawing_utils
mp_drawing_styles = mp_solutions.drawing_styles

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=1,
    min_detection_confidence=0.3,
    min_tracking_confidence=0.3
)

# Constants
DATA_FILE = "src/mediapipe_signs_db.csv"
LABELS = ["Tiger", "Ram", "Snake", "Horse", "Rat", "Boar", "Dog", "Bird", "Monkey", "Ox", "Dragon", "Hare"] 

class SignRecorder:
    def __init__(self):
        self.mode = "PREDICT" # PREDICT or RECORD
        self.current_label_idx = 0
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
                # Left Hand 0-20, Right Hand 0-20
                header = ["label"] + [f"h1_{i}_{ax}" for i in range(21) for ax in "xyz"] + \
                                     [f"h2_{i}_{ax}" for i in range(21) for ax in "xyz"]
                writer.writerow(header)
                
        # Load simple KNN classifier if data exists
        self.knn = None
        self.X = []
        self.y = []
        self._load_and_train()
    
    def _load_and_train(self):
        """Train a KNN model in memory if CSV has data."""
        try:
            with open(DATA_FILE, 'r') as f:
                reader = csv.reader(f)
                header = next(reader) # Skip header
                data = list(reader)
                
            if len(data) > 5:
                print(f"[+] Training on {len(data)} examples...")
                # Parse data
                X = []
                y = []
                for row in data:
                    y.append(row[0])
                    # Convert coords to floats
                    coords = [float(x) for x in row[1:]]
                    X.append(coords)
                
                # Using OpenCV's KNN (lightweight, no sklearn needed)
                self.knn = cv2.ml.KNearest_create()
                self.knn_labels = list(set(y))
                self.knn_labels.sort() # Ensure consistent order
                
                # Convert labels to INT for OpenCV
                y_int = [self.knn_labels.index(lbl) for lbl in y]
                
                start = time.time()
                self.knn.train(np.array(X, dtype=np.float32), cv2.ml.ROW_SAMPLE, np.array(y_int, dtype=np.int32))
                print(f"[+] Training complete ({time.time()-start:.3f}s). Classes: {self.knn_labels}")
            else:
                print("[!] Not enough data to train yet. Record some signs!")
                self.knn = None
        except Exception as e:
            print(f"[!] Error loading DB: {e}")
            self.knn = None

    def process_landmarks(self, results):
        """Convert MP results to a normalized feature vector (126 floats)."""
        if not results.multi_hand_landmarks:
            return [0.0] * 126 # Return empty vector if nothing detected
            
        # Buckets for Left and Right hand (21 * 3 = 63 values each)
        h1_data = [0.0] * 63 
        h2_data = [0.0] * 63
        
        # Sort hands by label to ensure consistency (Left hand always in h1_data, Right in h2_data)
        # MediaPipe 'Left' hand is usually the user's filtered Right hand on screen if mirrored.
        # But we will trust the label MP gives for consistency.
        
        for idx, classification in enumerate(results.multi_handedness):
            label = classification.classification[0].label
            
            # Get corresponding landmarks
            if idx >= len(results.multi_hand_landmarks): break
            landmarks = results.multi_hand_landmarks[idx]
            
            coords = []
            for lm in landmarks.landmark:
                coords.extend([lm.x, lm.y, lm.z])
                
            if label == "Left":
                h1_data = coords
            else:
                h2_data = coords
                
        return h1_data + h2_data

    def save_data(self):
        """Save buffered data to CSV."""
        if not self.data_buffer: return
        
        with open(DATA_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(self.data_buffer)
            
        print(f"[+] Saved {len(self.data_buffer)} samples for {LABELS[self.current_label_idx]}")
        self.data_buffer = []
        self._load_and_train() # Re-train instantly

    def predict(self, features):
        if not self.knn: return "Unknown"
        
        # Run inference
        sample = np.array([features], dtype=np.float32)
        ret, result, neighbours, dist = self.knn.findNearest(sample, k=3)
        
        # Distance Threshold Check
        # KNN Distance (L2 norm) tells us how "far" this pose is from known data.
        # If it's too far, it's a random hand movement, not a known sign.
        min_dist = dist[0][0]
        if min_dist > 100.0:  # Adjust this threshold if it's too strict/loose
             return f"Unknown (dist:{int(min_dist)})"
        
        idx = int(result[0][0])
        if idx < len(self.knn_labels):
            return self.knn_labels[idx]
        return "Unknown"

def main():
    cap = cv2.VideoCapture(0)
    # Windows fix
    if not cap.isOpened():
         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Revert to standard resolution for speed. High-res causes lag on CPU.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
         
    recorder = SignRecorder()
    
    print("\n" + "="*50)
    print("      MEDIAPIPE JUTSU RECORDER")
    print("="*50)
    print(" [R] - Toggle RECORDING Mode")
    print(" [SPACE] - Countdown to Auto-Record")
    print(" [N] or [1-9] - Change Label")
    print(" [Q] - Quit")
    print("="*50)

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        # Flip image for mirror effect
        image = cv2.flip(image, 1)
        h, w, _ = image.shape
        
        # Convert BGR to RGB
        image.flags.writeable = False
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        # Draw Landmarks
        image.flags.writeable = True
        
        features = recorder.process_landmarks(results)
        prediction = "Waiting..."
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())
        
        # Logic
        current_label = LABELS[recorder.current_label_idx]
        
        # Record VS Predict
        if recorder.mode == "RECORD":
            status_color = (0, 0, 255) # Red
            status_text = f"RECORDING: {current_label}"
            
            # Check key press for recording trigger
            keys = cv2.waitKey(5) & 0xFF
            
            # 1. Start Countdown
            if keys == 32 and not recorder.is_counting_down and not recorder.is_auto_recording: # SPACE
                recorder.countdown_start = time.time()
                recorder.is_counting_down = True
            
            # 2. Handle Countdown Logic
            if recorder.is_counting_down:
                elapsed = time.time() - recorder.countdown_start
                remaining = 3.0 - elapsed
                if remaining > 0:
                    # Draw Giant Countdown
                    cv2.putText(image, f"{int(remaining)+1}", (w//2 - 50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 165, 255), 10)
                    cv2.putText(image, "GET READY...", (w//2 - 150, h//2 + 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                else:
                    # Countdown finished -> Start Recording
                    recorder.is_counting_down = False
                    recorder.is_auto_recording = True
                    recorder.auto_record_start = time.time()
            
            # 3. Handle Auto-Recording Logic
            if recorder.is_auto_recording:
                elapsed = time.time() - recorder.auto_record_start
                if elapsed < 10.0: # Record for 10 seconds (approx 300 samples)
                    if features:
                         recorder.data_buffer.append([current_label] + features)
                    
                    # Blink effect
                    if int(elapsed * 10) % 2 == 0:
                        cv2.circle(image, (50, 100), 20, (0, 0, 255), -1)
                        
                    cv2.putText(image, "RECORDING!", (w//2 - 150, h//2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
                    cv2.putText(image, f"Samples: {len(recorder.data_buffer)}", (w//2 - 100, h//2 + 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
                else:
                    # Time up - Auto Save & Restart Countdown? 
                    # Let's just finish batch. User can hit Space again for next 300.
                    recorder.is_auto_recording = False
                    recorder.save_data() # Auto save every batch
                    print(f"[+] Batch complete for {current_label}. Press SPACE for next batch.")

            if keys == ord('n'):
                 recorder.current_label_idx = (recorder.current_label_idx + 1) % len(LABELS)
            elif keys >= ord('1') and keys <= ord('9'):
                 # 1 -> Index 0 (Tiger), 2 -> Index 1 (Ram)
                 idx = keys - ord('1')
                 if idx < len(LABELS):
                     recorder.current_label_idx = idx
            elif keys == ord('r'):
                 recorder.mode = "PREDICT"
                 recorder.save_data() # Autosave on toggle back
                 
        else: # PREDICT MODE
            status_color = (0, 255, 0) # Green
            status_text = "PREDICT MODE (Press R to Record)"
            
            if features:
                prediction = recorder.predict(features)
                # Show Prediction Centered
                cv2.putText(image, f"JUTSU: {prediction}", (50, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

        # Key checks
        keys = cv2.waitKey(1) & 0xFF
        if keys == ord('r'):
            recorder.mode = "RECORD"
                
        # UI Overlay
        cv2.rectangle(image, (0,0), (w, 60), (0,0,0), -1)
        cv2.putText(image, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        if keys == ord('q'):
            break

        cv2.imshow('MediaPipe Jutsu Trainer', image)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
