from src.jutsu_trainer import FireballJutsuTrainer
from src.utils.paths import get_latest_weights
from src.jutsu_academy.network_manager import NetworkManager
import cv2
import time
import numpy as np
import threading

class GameSession(FireballJutsuTrainer):
    def __init__(self, mode="practice", room_id=None, camera_index=0, username="Ninja", parent_app=None):
        # Auto-find weights
        weights = get_latest_weights()
        if not weights:
            raise FileNotFoundError("No model weights found!")
            
        super().__init__(model_path=weights, camera_index=camera_index)
        
        self.mode = mode
        self.room_id = room_id
        self.camera_index = camera_index # Track current camera
        self.username = username
        self.parent_app = parent_app
        
        # Challenge Mode State
        self.waiting_for_start = True
        self.start_time = None
        self.game_finished = False
        self.final_time = 0.0
        
        # Multiplayer Setup
        self.network = None
        self.is_my_turn = True
        self.enemy_hp = 100
        self.my_hp = 100
        self.enemy_last_photo = None # To show kill cam
        self.game_over = False

        if self.mode == "multiplayer" or self.mode == "challenge":
            try:
                self.network = NetworkManager()
                if self.mode == "multiplayer":
                    # Simple turn logic: Host goes first
                    # self.network.connect(room_id) # Old connect
                    # if self.network.is_host:
                    #     self.is_my_turn = True
                    # else:
                    #     self.is_my_turn = False
                    
                    # New join_room logic
                    host_status = self.network.join_room(room_id)
                    self.is_my_turn = (host_status == "host")
                    if self.is_my_turn:
                        print(f"[*] Hosted room: {room_id}")
                    else:
                        print(f"[*] Joined room: {room_id}")
            except Exception as e:
                print(f"[!] Network Error: {e}")
                self.mode = "practice" # Fallback
        
        # UI Overrides
        self.window_name = f"Jutsu Academy - {self.mode.upper()}"

    def process_frame(self):
        """Run one iteration of the game loop and return the frame."""
        ret, frame = self.cap.read()
        if not ret: return None
        
        # Flip frame
        frame = cv2.flip(frame, 1)
        cam_h, cam_w = frame.shape[:2]

        if self.mode == "challenge":
            if self.waiting_for_start:
                # Dim background slightly
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (cam_w, cam_h), (0,0,0), -1)
                frame = cv2.addWeighted(overlay, 0.4, frame, 0.6, 0)
                
                # Draw Text
                text = "PRESS [SPACE] TO START"
                font_scale = 1.5
                thickness = 3
                (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                x = (cam_w - w) // 2
                y = (cam_h + h) // 2
                
                # Shadow
                cv2.putText(frame, text, (x+2, y+2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0,0,0), thickness)
                # Text
                cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)
                
                # Don't update timer or detect hands yet
                should_detect = False
                
            elif self.start_time is None:
                # First frame after start
                self.start_time = time.time()

        # 1. Network / Game Over Check
        if self.mode == "multiplayer":
            self.update_network_state()
            if self.game_over:
                return self.render_game_over()
        
        if self.mode == "challenge" and self.game_finished:
            return self.render_challenge_complete()
        
        # --- TURN / DETECTION LOGIC ---
        should_detect = True
        if self.mode == "multiplayer" and not self.is_my_turn:
            should_detect = False
        
        # 2. Hand Detection
        if not self.jutsu_active and should_detect and not self.game_finished:
            frame, detected_class = self.detect_hands(frame)
            
            # --- CHALLENGE: Check if match target ---
            # For challenge, we might cycle through ALL jutsus? 
            # For v1, let's just stick to the current selected jutsu repeatedly or just one big jutsu?
            # Let's say Challenge = "Perform the current Jutsu 3 times fast!"
            # Or simplified: Just perform the selected Jutsu once for time.
            
            if self.current_step < len(self.sequence):
                current_target = self.sequence[self.current_step]
                
                if detected_class == current_target:
                    current_time = time.time()
                    if current_time - self.last_sign_time > self.cooldown:
                        print(f"[+] Correct: {detected_class}")
                        self.current_step += 1
                        self.last_sign_time = current_time
                        self.play_sound("each")
                        
                        # Check Completion
                        if self.current_step >= len(self.sequence):
                            self.activate_jutsu_effect(frame)
                            
                            if self.mode == "challenge":
                                self.finish_challenge()

        elif not should_detect and self.mode == "multiplayer":
                cv2.putText(frame, "OPPONENT'S TURN...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        else:
            mp_center = self.detect_hands_mediapipe(frame)
            if mp_center:
                self.last_hand_center = mp_center
        
        # 3. Render Effects
        frame = self.render_effect(frame)
        self.handle_audio_fx()
        self.handle_jutsu_duration()

        # 5. UI Panels
        if self.mode == "multiplayer":
            ui_panel = self.draw_multiplayer_ui(cam_w)
        else:
            ui_panel = self.draw_ui_panel(cam_w)
            
        # Draw Timer for Challenge
        if self.mode == "challenge" and self.start_time and not self.game_finished:
            elapsed = time.time() - self.start_time
            cv2.putText(frame, f"TIME: {elapsed:.2f}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
        
        # Stack UI
        try:
           canvas = np.vstack([frame, ui_panel])
        except:
           canvas = frame # Fallback
           
        return canvas

    def start_challenge(self):
        if self.mode == "challenge" and self.waiting_for_start:
            self.waiting_for_start = False
            self.play_sound("each") # Sound cue
        print("[!!!] JUTSU ACTIVATED [!!!]")
        self.jutsu_active = True
        self.jutsu_start_time = time.time()
        self.current_step = 0 
        self.play_sound("complete")
        self.signature_sound_played = False
        
        if self.mode == "multiplayer":
             self.send_attack(frame) # Send capture

    def finish_challenge(self):
        self.final_time = time.time() - self.start_time
        self.game_finished = True
        
        # Get Jutsu Name for Category
        try:
            jutsu_name = self.get_current_jutsu_name()
        except:
            jutsu_name = "Training"
            
        print(f"[🏆] Challenge Finished! Time: {self.final_time:.2f}s ({jutsu_name})")
        
        # Submit Score
        if self.network:
            threading.Thread(target=self.network.submit_score, args=(self.username, self.final_time, jutsu_name)).start()

    def render_challenge_complete(self):
        img = np.zeros((630, 640, 3), dtype=np.uint8)
        cv2.putText(img, "CHALLENGE COMPLETE!", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
        cv2.putText(img, f"TIME: {self.final_time:.2f}s", (180, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
        cv2.putText(img, "Score Submitted!", (200, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
        return img

    def handle_audio_fx(self):
         if self.jutsu_active and not self.signature_sound_played:
            if time.time() - self.jutsu_start_time >= 0.5:
                self.play_sound("signature")
                self.signature_sound_played = True
                
    def handle_jutsu_duration(self):
         if self.jutsu_active:
            if time.time() - self.jutsu_start_time > self.jutsu_duration:
                self.jutsu_active = False
                self.current_step = 0

    def render_game_over(self):
        img = np.zeros((630, 640, 3), dtype=np.uint8) # Match canvas size roughly
        text = "YOU WIN" if self.my_hp > 0 else "YOU DIED"
        color = (0, 255, 0) if self.my_hp > 0 else (0, 0, 255)
        cv2.putText(img, text, (200, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 4)
        return img

    def run(self):
        # Legacy method - kept for backward compatibility if needed, but not used by main.py anymore
        pass
        
    def switch_camera(self, new_index):
        """Hot-swap camera in-game."""
        print(f"[*] Switching camera to {new_index}...")
        self.cap.release()
        self.cap = cv2.VideoCapture(new_index)
        
        # Restore settings
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.camera_index = new_index

    def update_network_state(self):
        """Check for incoming attacks"""
        msg = self.network.receive()
        if msg:
            if msg["type"] == "attack":
                print("TOOK DAMAGE!")
                self.my_hp -= 20
                self.is_my_turn = True # Now it's my turn
                # Show kill cam (msg['image']) logic here

    def send_attack(self, frame):
        """Upload frame and notify enemy"""
        print("SENDING ATTACK!")
        self.network.send_attack(frame)
        self.is_my_turn = False # End turn

    # ... (existing code)

    def draw_settings_ui(self, frame):
        # Override: Disable the old pixel-based settings UI
        return frame

    def next_jutsu(self):
        self.current_jutsu_idx = (self.current_jutsu_idx + 1) % len(self.jutsu_names)
        self._switch_jutsu()

    def prev_jutsu(self):
        self.current_jutsu_idx = (self.current_jutsu_idx - 1) % len(self.jutsu_names)
        self._switch_jutsu()
        
    def get_current_jutsu_name(self):
        if 0 <= self.current_jutsu_idx < len(self.jutsu_names):
            return self.jutsu_names[self.current_jutsu_idx].upper()
        return "UNKNOWN"

    def draw_ui_panel(self, cam_width):
        """Create a separate UI panel with dynamic icon scaling."""
        panel_height = 150
        panel = np.zeros((panel_height, cam_width, 3), dtype=np.uint8)
        panel[:] = (40, 40, 40)  # Dark gray background
        
        h, w, _ = panel.shape
        
        # Calculate fit
        base_icon_size = 80
        gap = 20
        num_icons = len(self.sequence)
        
        # Max width available with some padding
        max_w = w - 40
        req_w = num_icons * (base_icon_size + gap) - gap
        
        # Scale down if needed
        scale = 1.0
        if req_w > max_w:
            scale = max_w / req_w
            
        icon_size = int(base_icon_size * scale)
        actual_gap = int(gap * scale)
        
        total_width = num_icons * (icon_size + actual_gap) - actual_gap
        start_x = (w - total_width) // 2
        y_pos = (h - icon_size) // 2
        
        for i, sign_name in enumerate(self.sequence):
            x = start_x + i * (icon_size + actual_gap)
            
            if sign_name in self.icons:
                # Resize icon
                icon = cv2.resize(self.icons[sign_name], (icon_size, icon_size), interpolation=cv2.INTER_AREA)
                
                # State Logic
                if i < self.current_step:
                    # Completed - Grey out
                    b, g, r, a = cv2.split(icon)
                    gray = cv2.cvtColor(cv2.merge([b, g, r]), cv2.COLOR_BGR2GRAY)
                    gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                    gray_bgr = (gray_bgr * 0.5).astype(np.uint8)
                    icon = cv2.merge([gray_bgr[:,:,0], gray_bgr[:,:,1], gray_bgr[:,:,2], a])
                    cv2.rectangle(panel, (x, y_pos), (x+icon_size, y_pos+icon_size), (0, 255, 0), max(1, int(2*scale)))
                    
                elif i == self.current_step and not self.jutsu_active:
                    # Current - Highlight
                    cv2.rectangle(panel, (x-int(5*scale), y_pos-int(5*scale)), 
                                  (x+icon_size+int(5*scale), y_pos+icon_size+int(5*scale)), 
                                  (0, 165, 255), max(2, int(3*scale)))
                
                # Overlay
                try:
                    # Check bounds before overlaying to avoid crashes
                    if x >= 0 and y_pos >= 0 and x+icon_size <= w and y_pos+icon_size <= h:
                        # Simple alpha blending helper since cvzone might be finicky with dynamic sizes
                        # But we installed cvzone, assume it works or use our own
                        from cvzone import overlayPNG
                        panel = overlayPNG(panel, icon, [x, y_pos])
                except:
                    pass

        # Text
        if self.jutsu_active:
            current_jutsu = self.jutsu_names[self.current_jutsu_idx]
            display_text = self.jutsu_list[current_jutsu].get("display_text", current_jutsu.upper())
            text_scale = 0.9 * scale
            text_size = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, text_scale, 2)[0]
            text_x = (w - text_size[0]) // 2
            cv2.putText(panel, display_text, (text_x, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, text_scale, (0, 0, 255), 2)
        else:
            target = self.sequence[self.current_step]
            text = f"Next: {target.upper()}"
            text_scale = 0.8 * scale
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, text_scale, 2)[0]
            cv2.putText(panel, text, ((w - text_size[0])//2, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 255), 2)

        return panel

    def draw_game_over(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        text = "YOU WIN" if self.my_hp > 0 else "YOU DIED"
        color = (0, 255, 0) if self.my_hp > 0 else (0, 0, 255)
        cv2.putText(img, text, (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 4)
        cv2.imshow(self.window_name, img)

