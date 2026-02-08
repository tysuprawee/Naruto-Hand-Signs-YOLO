from src.jutsu_academy.main_pygame_shared import *
from src.jutsu_academy.effects import EffectContext


class GameplayMixin:
    def start_game(self, mode, initial_jutsu_idx=0):
        """Start the game with specified mode."""
        self.game_mode = mode
        self.loading_message = "Initializing..."
        self.state = GameState.LOADING
        
        # Render loading screen immediately
        self._render_loading()
        pygame.display.flip()
        
        # Load models if not loaded
        self.loading_message = "Loading AI models..."
        self._render_loading()
        pygame.display.flip()
        
        if not self._load_ml_models():
            self.state = GameState.MENU
            return
        
        # Start camera
        self.loading_message = "Starting camera..."
        self._render_loading()
        pygame.display.flip()
        
        if not self._start_camera():
            print("[-] Failed to open camera!")
            # Show dedicated error modal
            self.error_title = "Camera Error"
            self.error_message = "Could not access camera.\nPlease check if OBS, Discord, or another app is using it."
            self.state = GameState.ERROR_MODAL 
            return
        
        # Reset state
        self.loading_message = "Ready!"
        self._render_loading()
        pygame.display.flip()
        
        if len(self.jutsu_names) > 0:
            self.current_jutsu_idx = max(0, min(int(initial_jutsu_idx), len(self.jutsu_names) - 1))
        else:
            self.current_jutsu_idx = 0
        self.sequence = self.jutsu_list[self.jutsu_names[self.current_jutsu_idx]]["sequence"]
        self.current_step = 0
        self.sequence_run_start = None
        self.combo_triggered_steps = set()
        self.combo_clone_hold = False
        self.combo_chidori_triple = False
        self.combo_rasengan_triple = False
        self.jutsu_active = False
        self.fire_particles.emitting = False
        self.pending_sounds = []
        self.pending_effects = []
        self.effect_orchestrator.reset()
        
        # Challenge Mode Init
        self.challenge_state = "waiting"
        self.challenge_start_time = 0
        self.challenge_final_time = 0
        self.challenge_rank_info = ""
        self.challenge_submitting = False
        self.submission_complete = False
        
        self.state = GameState.PLAYING

    def _render_loading(self):
        """Render loading screen."""
        if hasattr(self, 'bg_image') and self.bg_image:
             self.screen.blit(self.bg_image, (0, 0))
             # Very dark overlay for loading state
             overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, 220)) 
             self.screen.blit(overlay, (0, 0))
        else:
             self.screen.fill(COLORS["bg_dark"])
        
        # Loading text
        title = self.fonts["title_md"].render("LOADING", True, COLORS["accent"])
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
        self.screen.blit(title, title_rect)
        
        # Status message
        msg = getattr(self, 'loading_message', 'Please wait...')
        status = self.fonts["body"].render(msg, True, COLORS["text"])
        status_rect = status.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(status, status_rect)
        
        # Simple spinner animation (dots)
        dots = "." * (int(time.time() * 2) % 4)
        dots_surf = self.fonts["body"].render(dots, True, COLORS["text_dim"])
        self.screen.blit(dots_surf, (status_rect.right + 5, status_rect.y))

    def _draw_text_center(self, text, y_offset=0, color=(255, 255, 255)):
        """Helper to draw centered text."""
        surf = self.fonts["title_md"].render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + y_offset))
        self.screen.blit(surf, rect)

    def stop_game(self, return_to_library=False):
        """Stop the game and return to menu."""
        self._stop_camera()
        self.fire_particles.emitting = False
        self.jutsu_active = False
        self.sequence_run_start = None
        self.combo_clone_hold = False
        self.combo_chidori_triple = False
        self.combo_rasengan_triple = False
        self.pending_sounds = []
        self.pending_effects = []
        self.effect_orchestrator.on_jutsu_end(EffectContext())
        clone_effect = self.effect_orchestrator.effects.get("clone")
        if clone_effect:
            clone_effect.on_jutsu_end(EffectContext())
        self.effect_orchestrator.reset()
        self.current_video = None
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        if return_to_library:
            self.library_mode = "freeplay" if self.game_mode == "practice" else "challenge"
            self.state = GameState.JUTSU_LIBRARY
        else:
            self.state = GameState.MENU

    def switch_jutsu(self, direction):
        """Switch to next/prev jutsu."""
        self.effect_orchestrator.on_jutsu_end(EffectContext())
        clone_effect = self.effect_orchestrator.effects.get("clone")
        if clone_effect:
            clone_effect.on_jutsu_end(EffectContext())
        self.effect_orchestrator.reset()
        self.current_jutsu_idx = (self.current_jutsu_idx + direction) % len(self.jutsu_names)
        name = self.jutsu_names[self.current_jutsu_idx]
        self.sequence = self.jutsu_list[name]["sequence"]
        self.current_step = 0
        self.sequence_run_start = None
        self.combo_triggered_steps = set()
        self.combo_clone_hold = False
        self.combo_chidori_triple = False
        self.combo_rasengan_triple = False
        self.jutsu_active = False
        self.fire_particles.emitting = False
        self.pending_sounds = []
        self.pending_effects = []

    def detect_and_process(self, frame):
        """Run detection and check sequence."""
        if self.model is None:
            return frame, None
        
        results = self.model(frame, stream=True, verbose=False, imgsz=320)
        detected_class = None
        highest_conf = 0.0
        self.hand_pos = None # Reset
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                cls_name = self.class_names[cls]
                
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                if conf > 0.5 and conf > highest_conf:
                    highest_conf = conf
                    detected_class = cls_name
                    # Store center
                    self.hand_pos = ((x1 + x2) // 2, (y1 + y2) // 2)
                
                # Draw bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{cls_name} {conf:.2f}", (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return frame, detected_class

    def detect_hands(self, frame):
        """Detect hand landmarks for skeleton visualization and tracking."""
        if not self.hand_landmarker:
            return
            
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            
            # Using current clock time for timestamp (MS)
            timestamp = int(time.time() * 1000)
            result = self.hand_landmarker.detect_for_video(mp_image, timestamp)
            
            if result.hand_landmarks:
                self.hand_lost_frames = 0
                h, w = frame.shape[:2]

                # Build candidates for each detected hand, then choose one consistently.
                candidates = []
                indices = [0, 5, 9, 13, 17]

                for hand_idx, landmarks in enumerate(result.hand_landmarks):
                    base_x = sum(landmarks[i].x for i in indices) / len(indices)
                    base_y = sum(landmarks[i].y for i in indices) / len(indices)

                    def to_vec(hand_landmarks, idx):
                        lm = hand_landmarks[idx]
                        return np.array([lm.x, lm.y, lm.z])

                    v1 = to_vec(landmarks, 5) - to_vec(landmarks, 0)
                    v2 = to_vec(landmarks, 17) - to_vec(landmarks, 0)
                    normal = np.cross(v1, v2)
                    mag = np.linalg.norm(normal)
                    if mag > 1e-6:
                        normal /= mag

                    offset_strength = 0.25
                    hand_label = "Unknown"
                    if result.handedness and hand_idx < len(result.handedness):
                        hand_label = result.handedness[hand_idx][0].category_name
                        if hand_label == "Left":
                            offset_strength = -0.25

                    target_x = (base_x + normal[0] * offset_strength) * w
                    target_y = (base_y + normal[1] * offset_strength) * h

                    palm_span = float(np.linalg.norm(
                        np.array([landmarks[5].x, landmarks[5].y]) -
                        np.array([landmarks[17].x, landmarks[17].y])
                    ))
                    reference_span = 0.18
                    target_scale = palm_span / reference_span
                    target_scale = max(0.65, min(1.9, target_scale))

                    candidates.append({
                        "x": target_x,
                        "y": target_y,
                        "scale": target_scale,
                        "label": hand_label,
                    })

                if candidates:
                    chosen = None

                    # Prefer the currently tracked hand side to avoid left/right teleporting.
                    if self.tracked_hand_label:
                        same_label = [c for c in candidates if c["label"] == self.tracked_hand_label]
                        if same_label:
                            if self.hand_pos is not None:
                                prev_x, prev_y = self.hand_pos
                                chosen = min(
                                    same_label,
                                    key=lambda c: (c["x"] - prev_x) ** 2 + (c["y"] - prev_y) ** 2
                                )
                            else:
                                chosen = same_label[0]

                    # Bootstrap: default to Right hand first, then Left, then nearest.
                    if chosen is None and self.hand_pos is None:
                        right = [c for c in candidates if c["label"] == "Right"]
                        left = [c for c in candidates if c["label"] == "Left"]
                        chosen = right[0] if right else (left[0] if left else candidates[0])

                    if chosen is None and self.hand_pos is not None:
                        prev_x, prev_y = self.hand_pos
                        chosen = min(
                            candidates,
                            key=lambda c: (c["x"] - prev_x) ** 2 + (c["y"] - prev_y) ** 2
                        )
                    if chosen is None:
                        chosen = candidates[0]

                    target_x = chosen["x"]
                    target_y = chosen["y"]
                    target_scale = chosen["scale"]
                    self.tracked_hand_label = chosen["label"] if chosen["label"] != "Unknown" else self.tracked_hand_label

                    # Jitter filter (no smoothing/lag): ignore micro-movements only.
                    if self.hand_pos is not None:
                        prev_x, prev_y = self.hand_pos
                        jitter_px = 9.0
                        if (target_x - prev_x) ** 2 + (target_y - prev_y) ** 2 < (jitter_px ** 2):
                            target_x, target_y = prev_x, prev_y

                    # Follow selected hand directly for meaningful movement.
                    self.hand_pos = (target_x, target_y)
                    self.smooth_hand_pos = self.hand_pos
                if self.smooth_hand_effect_scale is None:
                    self.smooth_hand_effect_scale = target_scale
                else:
                    alpha_scale = 0.10
                    self.smooth_hand_effect_scale = (
                        self.smooth_hand_effect_scale +
                        (target_scale - self.smooth_hand_effect_scale) * alpha_scale
                    )
                self.hand_effect_scale = self.smooth_hand_effect_scale
                self.last_mp_result = result
                
                # 2. Draw Skeletons for ALL detected hands
                if self.settings.get("debug_hands", False):
                    CONNECTIONS = [
                        (0,1), (1,2), (2,3), (3,4), # Thumb
                        (0,5), (5,6), (6,7), (7,8), # Index
                        (5,9), (9,10), (10,11), (11,12), # Middle
                        (9,13), (13,14), (14,15), (15,16), # Ring
                        (13,17), (17,18), (18,19), (19,20), (0,17) # Pinky + Palm
                    ]
                    
                    for hand_idx, landmarks in enumerate(result.hand_landmarks):
                        # Use different color for second hand if desired (optional)
                        color = (0, 255, 0) # Primary Green
                        
                        for lm in landmarks:
                            cx, cy = int(lm.x * w), int(lm.y * h)
                            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
                            cv2.circle(frame, (cx, cy), 1, (255, 255, 255), -1)
                        
                        for conn in CONNECTIONS:
                            p1, p2 = landmarks[conn[0]], landmarks[conn[1]]
                            cv2.line(frame, (int(p1.x * w), int(p1.y * h)), 
                                            (int(p2.x * w), int(p2.y * h)), color, 2)
            else:
                self.hand_lost_frames += 1
                self.hand_pos = None
                self.smooth_hand_pos = None
                self.smooth_hand_effect_scale = None
                self.hand_effect_scale = 1.0
        except Exception as e:
            print(f"[!] detect_hands error: {e}")

    def detect_face(self, frame):
        """Detect face landmarks for fire positioning."""
        if not self.face_landmarker:
            return
        
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.face_landmarker.detect(mp_image)
            
            if result.face_landmarks:
                face = result.face_landmarks[0]
                h, w = frame.shape[:2]
                
                mouth = face[13]
                self.mouth_pos = (int(mouth.x * w), int(mouth.y * h))
                
                nose_x = face[1].x
                left_x = face[234].x
                right_x = face[454].x
                width = right_x - left_x
                if width > 0:
                    rel_nose = (nose_x - left_x) / width
                    self.head_yaw = (rel_nose - 0.5) * 2
        except:
            pass

    def cv2_to_pygame(self, frame):
        """Convert OpenCV frame to Pygame surface."""
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = np.flipud(frame)
        return pygame.surfarray.make_surface(frame)
