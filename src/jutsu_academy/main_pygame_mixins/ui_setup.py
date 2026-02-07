from src.jutsu_academy.main_pygame_shared import *


class UISetupMixin:
    def _create_menu_ui(self):
        """Create main menu UI."""
        cx = SCREEN_WIDTH // 2
        btn_w, btn_h = 280, 60
        start_y = 380
        gap = 70
        
        self.menu_buttons = {
            "practice": Button(cx - btn_w // 2, start_y, btn_w, btn_h, "ENTER ACADEMY"),
            "settings": Button(cx - btn_w // 2, start_y + gap, btn_w, btn_h, "SETTINGS"),
            "about": Button(cx - btn_w // 2, start_y + gap * 2, btn_w, btn_h, "ABOUT", color=COLORS["bg_card"]),
            "quit": Button(cx - btn_w // 2, start_y + gap * 3, btn_w, btn_h, "QUIT", color=COLORS["error"]),
        }
        
        # Mute button position (top right)
        self.mute_button_rect = pygame.Rect(SCREEN_WIDTH - 60, 20, 40, 40)

    def _create_settings_ui(self):
        
        # Settings Page UI
        cx = SCREEN_WIDTH // 2
        cy = 180
        
        self.settings_sliders = {
            "music": Slider(cx - 150, cy + 40, 300, "Music Volume", self.settings["music_vol"]),
            "sfx": Slider(cx - 150, cy + 120, 300, "SFX Volume", self.settings["sfx_vol"]),
        }
        
        self.camera_dropdown = Dropdown(cx - 50, cy + 200, 200, self.cameras, self.settings["camera_idx"])
        
        self.settings_checkboxes = {
            "debug_hands": Checkbox(cx - 150, cy + 260, 24, "Show Hand Skeleton", self.settings["debug_hands"]),
            "use_mp": Checkbox(cx - 150, cy + 300, 24, "Use MediaPipe AI (Faster/Experimental)", self.settings["use_mediapipe_signs"]),
            "restricted": Checkbox(cx - 150, cy + 340, 24, "Restricted Signs (Require 2 Hands)", self.settings.get("restricted_signs", False)),
        }
        
        self.settings_buttons = {
            "back": Button(cx - 100, cy + 400, 200, 50, "SAVE & BACK"),
        }

    def _create_practice_select_ui(self):
        """Create practice mode selection UI."""
        cx = SCREEN_WIDTH // 2
        
        self.practice_buttons = {
            "freeplay": Button(cx - 150, 250, 300, 60, "FREE PLAY"),
            "challenge": Button(cx - 150, 330, 300, 60, "CHALLENGE"),
            "multiplayer": Button(cx - 150, 410, 300, 60, "MULTIPLAYER (LOCKED)", color=(40, 40, 40)),
            "leaderboard": Button(cx - 150, 490, 300, 50, "LEADERBOARD", color=(218, 165, 32)), # Gold
            "back": Button(cx - 100, 620, 200, 50, "BACK"),
        }

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
            vol = self.settings["sfx_vol"]
            self.sounds[name].set_volume(vol)
            self.sounds[name].play()
