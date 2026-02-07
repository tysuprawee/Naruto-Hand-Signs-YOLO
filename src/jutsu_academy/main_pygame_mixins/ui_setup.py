from src.jutsu_academy.main_pygame_shared import *


class UISetupMixin:
    def _create_menu_ui(self):
        """Create main menu UI."""
        cx = SCREEN_WIDTH // 2
        btn_w, btn_h = 280, 60
        start_y = 345
        gap = 70
        
        self.menu_buttons = {
            "practice": Button(cx - btn_w // 2, start_y, btn_w, btn_h, "ENTER ACADEMY"),
            "settings": Button(cx - btn_w // 2, start_y + gap, btn_w, btn_h, "SETTINGS"),
            "tutorial": Button(cx - btn_w // 2, start_y + gap * 2, btn_w, btn_h, "TUTORIAL", color=COLORS["bg_card"]),
            "about": Button(cx - btn_w // 2, start_y + gap * 3, btn_w, btn_h, "ABOUT", color=COLORS["bg_card"]),
            "quit": Button(cx - btn_w // 2, start_y + gap * 4, btn_w, btn_h, "QUIT", color=COLORS["error"]),
        }
        
        # Mute button position (top right)
        self.mute_button_rect = pygame.Rect(SCREEN_WIDTH - 60, 20, 40, 40)

    def _create_settings_ui(self):
        
        # Settings Page UI
        cx = 290
        cy = 170
        camera_idx = self.settings["camera_idx"]
        if len(self.cameras) == 0:
            camera_idx = 0
            self.settings["camera_idx"] = 0
        elif camera_idx < 0 or camera_idx >= len(self.cameras):
            camera_idx = 0
            self.settings["camera_idx"] = 0
        
        self.settings_sliders = {
            "music": Slider(cx - 150, cy + 40, 300, "Music Volume", self.settings["music_vol"]),
            "sfx": Slider(cx - 150, cy + 120, 300, "SFX Volume", self.settings["sfx_vol"]),
        }
        
        self.camera_dropdown = Dropdown(cx - 60, cy + 210, 230, self.cameras, camera_idx)
        
        self.settings_checkboxes = {
            "debug_hands": Checkbox(cx - 150, cy + 290, 24, "Show Hand Skeleton", self.settings["debug_hands"]),
            "use_mp": Checkbox(cx - 150, cy + 330, 24, "Use MediaPipe AI (Faster/Experimental) - Always On", True),
            "restricted": Checkbox(cx - 150, cy + 370, 24, "Restricted Signs (Require 2 Hands) - Always On", True),
        }
        
        self.settings_buttons = {
            "preview_toggle": Button(cx - 100, cy + 395, 220, 44, "ENABLE PREVIEW", color=COLORS["bg_card"]),
            "scan_cameras": Button(cx - 100, cy + 350, 220, 40, "SCAN CAMERAS", color=COLORS["bg_card"]),
            "back": Button(cx - 100, cy + 450, 220, 52, "SAVE & BACK"),
        }

    def _refresh_settings_camera_options(self, force=False):
        """Probe and refresh camera dropdown options for settings."""
        now = time.time()
        if not force and self.cameras and (now - self.camera_scan_last_at) < 30.0:
            return

        detected = self._scan_cameras(probe=True)
        self.cameras = detected
        self.camera_scan_last_at = now

        if not hasattr(self, "camera_dropdown"):
            return

        self.camera_dropdown.options = list(self.cameras)
        if len(self.cameras) == 0:
            self.camera_dropdown.selected_idx = 0
            self.camera_dropdown.is_open = False
            self.settings["camera_idx"] = 0
        elif self.camera_dropdown.selected_idx >= len(self.cameras):
            self.camera_dropdown.selected_idx = 0
            self.settings["camera_idx"] = 0

    def _start_settings_camera_preview(self, camera_idx=None):
        """Start camera preview used only in settings screen."""
        if len(self.cameras) == 0:
            self._refresh_settings_camera_options(force=True)
        if len(self.cameras) == 0:
            self._stop_settings_camera_preview()
            return False

        idx = self.settings["camera_idx"] if camera_idx is None else int(camera_idx)
        idx = max(0, min(idx, len(self.cameras) - 1))
        if self.settings_preview_cap is not None and self.settings_preview_idx == idx:
            return True

        self._stop_settings_camera_preview()
        capture_idx = self._resolve_camera_capture_index(idx)

        if os.name == "nt":
            cap = cv2.VideoCapture(capture_idx, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(capture_idx)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        if not cap.isOpened():
            cap.release()
            self.settings_preview_cap = None
            self.settings_preview_idx = None
            return False

        self.settings_preview_cap = cap
        self.settings_preview_idx = idx
        return True

    def _stop_settings_camera_preview(self):
        """Stop settings camera preview stream."""
        if self.settings_preview_cap is not None:
            self.settings_preview_cap.release()
            self.settings_preview_cap = None
            self.settings_preview_idx = None

    def _get_settings_preview_surface(self):
        """Read preview frame and convert to pygame surface."""
        if self.settings_preview_cap is None:
            return None
        ret, frame = self.settings_preview_cap.read()
        if not ret:
            return None
        frame = cv2.flip(frame, 1)
        return self.cv2_to_pygame(frame)

    def _create_practice_select_ui(self):
        """Create practice mode selection UI."""
        cx = SCREEN_WIDTH // 2
        
        self.practice_buttons = {
            "freeplay": Button(cx - 150, 250, 300, 60, "FREE PLAY"),
            "challenge": Button(cx - 150, 330, 300, 60, "CHALLENGE"),
            "library": Button(cx - 150, 410, 300, 60, "JUTSU LIBRARY", color=(58, 92, 162)),
            "multiplayer": Button(cx - 150, 490, 300, 60, "MULTIPLAYER (LOCKED)", color=(40, 40, 40)),
            "quests": Button(cx - 150, 570, 300, 50, "QUEST BOARD", color=(80, 140, 110)),
            "leaderboard": Button(cx - 150, 635, 300, 50, "LEADERBOARD", color=(218, 165, 32)), # Gold
            "back": Button(cx - 100, 620, 200, 50, "BACK"),
        }
        self.practice_buttons["multiplayer"].enabled = False

    def _create_about_ui(self):
        """Create about page UI."""
        cx = SCREEN_WIDTH // 2
        
        self.about_buttons = {
            "back": Button(cx - 100, 650, 200, 50, "BACK"),
        }

    def _create_leaderboard_ui(self):
        """Create leaderboard UI."""
        self.leaderboard_buttons = {
            "back": Button(50, 50, 100, 40, "< Back", font_size=20),
            "refresh": Button(SCREEN_WIDTH - 150, 50, 100, 40, "Refresh", font_size=20, color=COLORS["success"])
        }

    def _create_library_ui(self):
        """Create jutsu library UI."""
        self.library_buttons = {
            "back": Button(50, 50, 100, 40, "< Back", font_size=20),
        }

    def _create_quest_ui(self):
        """Create quest board UI."""
        self.quest_buttons = {
            "back": Button(40, 40, 120, 44, "< BACK", font_size=22, color=COLORS["bg_card"]),
        }

    def _create_tutorial_ui(self):
        """Create tutorial navigation buttons."""
        cx = SCREEN_WIDTH // 2
        self.tutorial_buttons = {
            "back": Button(cx - 260, SCREEN_HEIGHT - 110, 160, 52, "BACK", color=COLORS["bg_card"]),
            "next": Button(cx + 100, SCREEN_HEIGHT - 110, 160, 52, "NEXT"),
            "skip": Button(cx - 80, SCREEN_HEIGHT - 110, 160, 52, "SKIP", color=COLORS["bg_card"]),
        }

    def _load_ml_models(self):
        """Load ML models (called when starting game)."""
        if self.model is not None:
            return True
        
        weights = get_latest_weights()
        if not weights:
            print("[-] No YOLO weights found!")
            return False
        
        print(f"[*] Loading YOLO: {weights}")
        self.model = YOLO(weights)
        self.class_names = get_class_names()
        
        # MediaPipe Face
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        face_path = Path("models/face_landmarker.task")
        if face_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(face_path))
                options = vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
                self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
                print("[+] Face detection loaded")
            except Exception as e:
                print(f"[!] Face detection failed: {e}")
        
        # MediaPipe Hands
        hand_path = Path("models/hand_landmarker.task")
        if hand_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(hand_path))
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=2,
                    running_mode=vision.RunningMode.VIDEO
                )
                self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
                print("[+] Hand tracking loaded")
            except Exception as e:
                print(f"[!] Hand tracking failed: {e}")
        
        return True

    def _start_camera(self):
        """Start camera capture."""
        if self.cap is not None:
            self.cap.release()
        
        cam_idx = self.settings["camera_idx"]
        cam_idx = self._resolve_camera_capture_index(cam_idx)
        # Use DirectShow on Windows for better compatibility
        if os.name == 'nt':
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(cam_idx)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        return self.cap.isOpened()

    def _stop_camera(self):
        """Stop camera capture."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def play_sound(self, name):
        """Play a sound effect."""
        if name in self.sounds:
            vol = self._effective_sfx_volume(self.settings["sfx_vol"])
            self.sounds[name].set_volume(vol)
            self.sounds[name].play()
