from src.jutsu_academy.main_pygame_shared import *
import datetime


class CoreMixin:
    def _daily_period_id(self):
        return time.strftime("%Y-%m-%d")

    def _weekly_period_id(self):
        y, w, _ = datetime.date.today().isocalendar()
        return f"{y}-W{w:02d}"

    def _default_quest_state(self):
        return {
            "daily": {
                "period": self._daily_period_id(),
                "quests": {
                    "d_signs": {"progress": 0, "claimed": False},
                    "d_jutsus": {"progress": 0, "claimed": False},
                    "d_xp": {"progress": 0, "claimed": False},
                },
            },
            "weekly": {
                "period": self._weekly_period_id(),
                "quests": {
                    "w_jutsus": {"progress": 0, "claimed": False},
                    "w_challenges": {"progress": 0, "claimed": False},
                    "w_xp": {"progress": 0, "claimed": False},
                },
            },
        }

    def _reset_daily_quests(self):
        self.quest_state["daily"] = {
            "period": self._daily_period_id(),
            "quests": {
                "d_signs": {"progress": 0, "claimed": False},
                "d_jutsus": {"progress": 0, "claimed": False},
                "d_xp": {"progress": 0, "claimed": False},
            },
        }

    def _reset_weekly_quests(self):
        self.quest_state["weekly"] = {
            "period": self._weekly_period_id(),
            "quests": {
                "w_jutsus": {"progress": 0, "claimed": False},
                "w_challenges": {"progress": 0, "claimed": False},
                "w_xp": {"progress": 0, "claimed": False},
            },
        }

    def _refresh_quest_periods(self):
        changed = False
        if self.quest_state.get("daily", {}).get("period") != self._daily_period_id():
            self._reset_daily_quests()
            changed = True
        if self.quest_state.get("weekly", {}).get("period") != self._weekly_period_id():
            self._reset_weekly_quests()
            changed = True
        if changed:
            self._save_player_meta()

    def _inc_quest_progress(self, quest_id, amount=1):
        for scope in ("daily", "weekly"):
            q = self.quest_state.get(scope, {}).get("quests", {}).get(quest_id)
            if q and not q.get("claimed", False):
                q["progress"] = int(q.get("progress", 0)) + int(amount)

    def _record_sign_progress(self):
        self._inc_quest_progress("d_signs", 1)

    def _record_jutsu_completion(self, xp_gain, is_challenge):
        self._inc_quest_progress("d_jutsus", 1)
        self._inc_quest_progress("w_jutsus", 1)
        self._inc_quest_progress("d_xp", int(xp_gain))
        self._inc_quest_progress("w_xp", int(xp_gain))
        if is_challenge:
            self._inc_quest_progress("w_challenges", 1)

    def _quest_definitions(self):
        return [
            ("daily", "d_signs", "Land 25 correct signs", 25, 120),
            ("daily", "d_jutsus", "Complete 5 jutsu runs", 5, 180),
            ("daily", "d_xp", "Earn 450 XP", 450, 250),
            ("weekly", "w_jutsus", "Complete 30 jutsu runs", 30, 700),
            ("weekly", "w_challenges", "Finish 12 challenge runs", 12, 900),
            ("weekly", "w_xp", "Earn 4000 XP", 4000, 1200),
        ]

    def _claim_quest(self, scope, quest_id):
        defs = {f"{s}:{qid}": (target, reward, title) for s, qid, title, target, reward in self._quest_definitions()}
        key = f"{scope}:{quest_id}"
        if key not in defs:
            return False
        target, reward, title = defs[key]
        q = self.quest_state.get(scope, {}).get("quests", {}).get(quest_id)
        if not q or q.get("claimed", False) or int(q.get("progress", 0)) < int(target):
            return False
        q["claimed"] = True
        prev_level = self.progression.level
        leveled = self.progression.add_xp(reward)
        self.process_unlock_alerts(previous_level=prev_level)
        self.show_alert("Quest Reward", f"{title}\nReward claimed: +{reward} XP", "CLAIMED")
        if leveled:
            self.xp_popups.append({
                "text": f"RANK UP: {self.progression.rank}!",
                "x": SCREEN_WIDTH // 2,
                "y": SCREEN_HEIGHT // 2,
                "timer": 2.8,
                "color": COLORS["success"],
            })
        self._save_player_meta()
        return True

    def _mastery_thresholds(self, jutsu_name):
        seq_len = max(1, len(self.jutsu_list.get(jutsu_name, {}).get("sequence", [])))
        return {
            "bronze": seq_len * 4.0,
            "silver": seq_len * 2.8,
            "gold": seq_len * 2.0,
        }

    def _get_mastery_tier(self, jutsu_name):
        best = self.mastery_data.get(jutsu_name, {}).get("best_time")
        if best is None:
            return "none"
        t = self._mastery_thresholds(jutsu_name)
        if best <= t["gold"]:
            return "gold"
        if best <= t["silver"]:
            return "silver"
        if best <= t["bronze"]:
            return "bronze"
        return "none"

    def _record_mastery_completion(self, jutsu_name, clear_time):
        if clear_time is None or clear_time <= 0:
            return
        row = self.mastery_data.setdefault(jutsu_name, {})
        best = row.get("best_time")
        if best is None or clear_time < best:
            row["best_time"] = float(clear_time)
            self._save_player_meta()

    def _load_player_meta(self):
        path = Path("src/jutsu_academy/player_meta.json")
        self.player_meta_path = path
        self.tutorial_seen = False
        self.tutorial_seen_at = None
        self.tutorial_version = "1.0"
        self._tutorial_cloud_sync_enabled = True
        self.mastery_data = {}
        self.quest_state = self._default_quest_state()
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self.tutorial_seen = bool(data.get("tutorial_seen", False))
                self.tutorial_seen_at = data.get("tutorial_seen_at")
                self.mastery_data = dict(data.get("mastery", {}))
                qs = data.get("quests")
                if isinstance(qs, dict):
                    self.quest_state = qs
            except Exception:
                pass
        # Best effort: sync tutorial flag from cloud profile for logged-in users.
        if self.username != "Guest" and self.network_manager and self.network_manager.client:
            try:
                profile = self.network_manager.get_profile(self.username)
                if isinstance(profile, dict) and profile:
                    cloud_seen = bool(profile.get("tutorial_seen", False))
                    cloud_seen_at = profile.get("tutorial_seen_at")
                    cloud_ver = profile.get("tutorial_version")
                    if cloud_seen:
                        self.tutorial_seen = True
                    if cloud_seen_at and not self.tutorial_seen_at:
                        self.tutorial_seen_at = cloud_seen_at
                    if cloud_ver:
                        self.tutorial_version = str(cloud_ver)
            except Exception:
                pass
        self._refresh_quest_periods()

    def _sync_tutorial_meta_to_cloud(self):
        """Best-effort cloud sync for tutorial completion state."""
        if not getattr(self, "_tutorial_cloud_sync_enabled", True):
            return
        if self.username == "Guest":
            return
        if not self.network_manager or not self.network_manager.client:
            return
        try:
            payload = {
                "username": self.username,
                "tutorial_seen": bool(self.tutorial_seen),
                "tutorial_seen_at": self.tutorial_seen_at,
                "tutorial_version": self.tutorial_version,
            }
            self.network_manager.upsert_profile(payload)
        except Exception as e:
            # If schema isn't migrated yet, avoid repeated noisy attempts.
            self._tutorial_cloud_sync_enabled = False
            print(f"[!] Tutorial cloud sync disabled: {e}")

    def _save_player_meta(self):
        if not hasattr(self, "player_meta_path"):
            self.player_meta_path = Path("src/jutsu_academy/player_meta.json")
        try:
            self.player_meta_path.parent.mkdir(exist_ok=True)
            with open(self.player_meta_path, "w") as f:
                json.dump(
                    {
                        "tutorial_seen": bool(getattr(self, "tutorial_seen", False)),
                        "tutorial_seen_at": getattr(self, "tutorial_seen_at", None),
                        "mastery": getattr(self, "mastery_data", {}),
                        "quests": getattr(self, "quest_state", self._default_quest_state()),
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass
        self._sync_tutorial_meta_to_cloud()

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
        self.practice_scroll_y = 0
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
        self.pending_sounds = []
        self.pending_effects = []
        self.clone_spawn_delay_s = 1.5
        self.combo_clone_hold = False
        self.combo_chidori_triple = False
        self.combo_rasengan_triple = False
        
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
        self.hand_effect_scale = 1.0
        self.smooth_hand_effect_scale = None
        self.tracked_hand_label = None
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
        self._load_feature_icons()
        self._load_player_meta()
        self.sequence_run_start = None
        self.quest_claim_rects = []
        self.tutorial_step_index = 0
        self.tutorial_steps = [
            {
                "icon_key": "camera",
                "title": "Setup Your Camera",
                "lines": [
                    "Open Settings and choose your camera device.",
                    "Enable preview to verify framing and lighting.",
                    "Keep both hands visible in the camera panel.",
                ],
            },
            {
                "icon_key": "signs",
                "title": "Perform Signs In Order",
                "lines": [
                    "Follow the sign sequence shown at the bottom.",
                    "Each correct sign advances your combo step.",
                    "Stable lighting improves landmark recognition.",
                ],
            },
            {
                "icon_key": "execute",
                "title": "Execute The Jutsu",
                "lines": [
                    "Complete all signs to trigger the jutsu effect.",
                    "You earn XP for successful completions.",
                    "Level up to unlock higher-tier jutsu.",
                ],
            },
            {
                "icon_key": "challenge",
                "title": "Challenge And Progress",
                "lines": [
                    "Use Challenge mode for timed runs and leaderboard ranking.",
                    "Visit Quest Board for daily/weekly XP rewards.",
                    "Master each jutsu to reach Bronze, Silver, and Gold tiers.",
                ],
            },
        ]

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
        self._create_quest_ui()
        self._create_tutorial_ui()
        self.playing_back_button = Button(24, 20, 120, 42, "< BACK", font_size=22, color=COLORS["bg_card"])
        
        # FPS tracking
        self.fps = 0
        self.frame_count = 0
        self.fps_timer = time.time()

        if not self.tutorial_seen:
            self.state = GameState.TUTORIAL
        
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
