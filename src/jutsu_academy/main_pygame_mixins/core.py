from src.jutsu_academy.main_pygame_shared import *


class CoreMixin:
    def __init__(self):
        from src.jutsu_academy.effects import EffectOrchestrator, ShadowCloneEffect

        pygame.init()
        pygame.display.set_caption("Jutsu Academy")
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        
        # State
        self.state = GameState.MENU
        self.prev_state = None
        self.about_scroll_y = 0  # Scroll position for About page
        self.library_mode = "browse"  # browse | freeplay | challenge
        self.library_item_rects = []
        
        # User/Auth state
        self.username = "Guest"
        self.discord_user = None
        self.user_avatar = None
        self.login_in_progress = False
        self.login_attempt_id = 0          # Incremented each login attempt
        self.login_started_at = 0.0        # Timestamp when login started
        self.discord_auth_url = None       # Current OAuth URL (for resume)
        self.login_timeout_s = 180         # 3 minutes timeout
        self.login_error = ""              # Error message for UI
        self.auth_instance = None          # Active DiscordLogin instance
        self.profile_dropdown_open = False
        self.login_modal_message = ""
        self.pending_action = None  # Action to perform after login
        self._load_user_session()
        
        # Settings
        self.settings = {
            "music_vol": 0.5,
            "sfx_vol": 0.7,
            "camera_idx": 0,
            "debug_hands": False,
            "use_mediapipe_signs": True, # Forced ON
            "restricted_signs": True     # Forced ON
        }
        self.load_settings()
        self.settings["use_mediapipe_signs"] = True
        self.settings["restricted_signs"] = True
        
        # Camera list (startup-safe; no hardware probe here)
        self.cameras = self._scan_cameras(probe=False)
        self.camera_device_indices = []
        
        # Fonts (Load once to avoid performance issues)
        self.fonts = {
            "title_lg": pygame.font.Font(None, 80),
            "title_md": pygame.font.Font(None, 56),
            "title_sm": pygame.font.Font(None, 40),
            "body": pygame.font.Font(None, 28),
            "body_sm": pygame.font.Font(None, 24),
            "small": pygame.font.Font(None, 18),
            "tiny": pygame.font.Font(None, 16),
            "icon": pygame.font.Font(None, 30),
        }
        
        # Audio
        pygame.mixer.init()
        self.sounds = {}
        self.music_playing = False
        
        # Game state (must init before loading sounds that use jutsu_list)
        self.game_mode = "practice"  # practice, challenge
        self.jutsu_list = OFFICIAL_JUTSUS.copy()
        self.jutsu_names = list(self.jutsu_list.keys())
        
        # Now load sounds (uses jutsu_list)
        self._load_sounds()
        self._try_play_music()
        
        # ML Models (lazy loaded)
        self.model = None
        self.recorder = SignRecorder() # MediaPipe + KNN
        
        # Connection Monitor
        self.connection_fail_count = 0
        threading.Thread(target=self._monitor_connection_loop, daemon=True).start()
        
        # Network & Leaderboard
        self.network_manager = NetworkManager()
        self.leaderboard_data = []
        self.leaderboard_loading = False
        self.leaderboard_avatars = {} # Cache for rounded surfaces

        # Progression System (Shinobi Path)
        self.progression = ProgressionManager(self.username, network_manager=self.network_manager)
        self.xp_popups = [] # List of {"text": str, "x": int, "y": int, "timer": float, "color": tuple}
        self.unlocked_jutsus_known = {
            name for name, data in self.jutsu_list.items()
            if self.progression.level >= data.get("min_level", 0)
        }

        # Reusable alert queue/modal state
        self.alert_queue = []
        self.active_alert = None
        self.alert_ok_rect = pygame.Rect(0, 0, 0, 0)
        
        # Announcements
        self.announcements = []
        self.announcements_loading = False
        self.show_announcements = False
        self.current_announcement_idx = 0
        self.announcements_fetched = False
        self.version_alert_for_version = None
        self.announcement_timer_start = time.time()
        self.announcement_auto_show_delay = 1.5
        
        # Trigger background fetch if online
        if self.network_manager.client:
             threading.Thread(target=self._fetch_announcements, daemon=True).start()

        self.class_names = None
        self.face_landmarker = None
        self.hand_landmarker = None
        self.last_mp_timestamp = 0
        
        # Camera
        self.cap = None
        self.settings_preview_cap = None
        self.settings_preview_idx = None
        self.settings_preview_enabled = False
        self.camera_scan_last_at = 0.0
        
        # Game state continued
        self.current_jutsu_idx = 0
        self.sequence = []
        self.current_step = 0
        self.last_sign_time = 0
        self.cooldown = 0.5
        self.jutsu_active = False
        self.jutsu_start_time = 0
        self.jutsu_duration = 5.0
        
        # Challenge Mode State
        self.challenge_state = "waiting" # waiting, countdown, active, results
        self.challenge_start_time = 0
        self.challenge_final_time = 0
        self.challenge_countdown_start = 0
        self.challenge_rank_info = ""
        self.challenge_submitting = False
        self.submission_complete = False
        
        # Modal Rects (Pre-initialize to avoid first-frame click fails)
        self.welcome_ok_rect = pygame.Rect(0, 0, 0, 0)
        self.welcome_modal_timer = 0.0 # For animations
        
        # Tracking & Smoothing
        self.mouth_pos = None
        self.hand_pos = None
        self.smooth_hand_pos = None
        self.hand_lost_frames = 0
        self.max_hold_frames = 15 # frames to keep the effect where it was
        self.head_yaw = 0
        
        # Effects
        self.fire_particles = FireParticleSystem(200)
        self.effect_orchestrator = EffectOrchestrator()
        self.effect_orchestrator.register("clone", ShadowCloneEffect(swap_xy=True), passive=True)
        
        # Video overlay for jutsus
        self.current_video = None
        self.video_cap = None
        self.jutsu_videos = {}
        self._load_jutsu_videos()

        # Icons
        self.icons = {}
        self._load_icons()
        
        # Logo
        self.logo = None
        self._load_logo()
        
        # Background image
        self.bg_image = None
        self._load_background()
        
        # Social icons
        self.social_icons = {}
        self._load_social_icons()
        
        # Mute toggle state
        self.is_muted = False
        self.mute_icons = {"mute": None, "unmute": None}
        self._load_mute_icons()
        
        # Arrow icons for navigation
        self.arrow_icons = {"left": None, "right": None}
        self._load_arrow_icons()
        
        # UI Elements
        self._create_menu_ui()
        self._create_settings_ui()
        self._create_practice_select_ui()
        self._create_about_ui()
        self._create_leaderboard_ui()
        self._create_library_ui()
        self.playing_back_button = Button(24, 20, 120, 42, "< BACK", font_size=22, color=COLORS["bg_card"])
        
        # FPS tracking
        self.fps = 0
        self.frame_count = 0
        self.fps_timer = time.time()
        
        print("[+] Jutsu Academy initialized!")

    def show_alert(self, title, message, button_text="OK"):
        """Queue a reusable alert modal."""
        self.alert_queue.append({
            "title": str(title),
            "message": str(message),
            "button_text": str(button_text),
        })

    def process_unlock_alerts(self, previous_level=None):
        """Queue alert(s) for newly unlocked jutsus."""
        current_level = self.progression.level

        if previous_level is not None:
            newly_unlocked = sorted(
                [
                    name for name, data in self.jutsu_list.items()
                    if previous_level < data.get("min_level", 0) <= current_level
                ],
                key=lambda name: self.jutsu_list[name].get("min_level", 0),
            )
        else:
            currently_unlocked = {
                name for name, data in self.jutsu_list.items()
                if current_level >= data.get("min_level", 0)
            }
            newly_unlocked = sorted(
                currently_unlocked - self.unlocked_jutsus_known,
                key=lambda name: self.jutsu_list[name].get("min_level", 0),
            )

        for name in newly_unlocked:
            min_lv = self.jutsu_list[name].get("min_level", 0)
            self.show_alert(
                "New Skill Unlocked",
                f"{name} unlocked at LV.{min_lv}. Open Jutsu Library to preview sequence.",
                "NICE",
            )
        self.unlocked_jutsus_known = {
            name for name, data in self.jutsu_list.items()
            if current_level >= data.get("min_level", 0)
        }

    def _activate_next_alert(self):
        """Activate next queued alert if none is currently shown."""
        if self.active_alert is None and self.alert_queue:
            self.active_alert = self.alert_queue.pop(0)
