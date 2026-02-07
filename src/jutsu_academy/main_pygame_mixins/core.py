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
            "use_mediapipe_signs": True, # NEW: Toggle between YOLO and MediaPipe
            "restricted_signs": False     # NEW: Only detect when 2 hands are visible
        }
        self.load_settings()
        
        # Camera list
        self.cameras = self._scan_cameras()
        
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
        
        # Announcements
        self.announcements = []
        self.announcements_loading = False
        self.show_announcements = False
        self.current_announcement_idx = 0
        self.announcements_fetched = False
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
        
        # FPS tracking
        self.fps = 0
        self.frame_count = 0
        self.fps_timer = time.time()
        
        print("[+] Jutsu Academy initialized!")
