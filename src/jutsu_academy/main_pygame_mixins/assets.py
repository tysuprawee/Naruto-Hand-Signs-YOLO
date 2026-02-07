from src.jutsu_academy.main_pygame_shared import *
import subprocess
import sys


class AssetsMixin:
    def _load_ui_image(self, path, size=None):
        p = Path(path)
        if not p.exists():
            p = Path("src/pics/placeholder.png")
        try:
            img = pygame.image.load(str(p)).convert_alpha()
            if size:
                img = pygame.transform.smoothscale(img, size)
            return img
        except Exception:
            return None

    def _load_feature_icons(self):
        """Load tutorial, mastery, quest and shared UI icons."""
        self.tutorial_icons = {
            "camera": self._load_ui_image("src/pics/tutorial/step_camera.png", (80, 80)),
            "signs": self._load_ui_image("src/pics/tutorial/step_signs.png", (80, 80)),
            "execute": self._load_ui_image("src/pics/tutorial/step_execute.png", (80, 80)),
            "challenge": self._load_ui_image("src/pics/tutorial/step_challenge.png", (80, 80)),
            "panel_bg": self._load_ui_image("src/pics/tutorial/panel_bg.png"),
        }
        self.mastery_icons = {
            "none": self._load_ui_image("src/pics/mastery/locked_badge.png", (28, 28)),
            "bronze": self._load_ui_image("src/pics/mastery/bronze_badge.png", (28, 28)),
            "silver": self._load_ui_image("src/pics/mastery/silver_badge.png", (28, 28)),
            "gold": self._load_ui_image("src/pics/mastery/gold_badge.png", (28, 28)),
        }
        self.quest_icons = {
            "daily": self._load_ui_image("src/pics/quests/daily_icon.png", (48, 48)),
            "weekly": self._load_ui_image("src/pics/quests/weekly_icon.png", (48, 48)),
            "card_bg": self._load_ui_image("src/pics/quests/quest_card_bg.png"),
            "progress_fill": self._load_ui_image("src/pics/quests/progress_fill.png"),
            "progress_track": self._load_ui_image("src/pics/quests/progress_track.png"),
            "claim_btn": self._load_ui_image("src/pics/quests/claim_btn.png"),
            "claimed_stamp": self._load_ui_image("src/pics/quests/claimed_stamp.png"),
            "refresh": self._load_ui_image("src/pics/quests/refresh_timer.png", (20, 20)),
        }
        self.ui_icons = {
            "info": self._load_ui_image("src/pics/ui/info.png", (20, 20)),
            "check": self._load_ui_image("src/pics/ui/check.png", (20, 20)),
            "lock": self._load_ui_image("src/pics/ui/lock.png", (20, 20)),
            "reward_xp": self._load_ui_image("src/pics/ui/reward_xp.png", (20, 20)),
        }

    def _macos_camera_names(self):
        """Best-effort camera names on macOS via system_profiler."""
        try:
            out = subprocess.check_output(
                ["system_profiler", "SPCameraDataType"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return []

        ignored = {
            "camera",
            "model id",
            "unique id",
            "serial number",
            "vendor id",
            "product id",
            "version",
        }
        names = []
        for line in out.splitlines():
            s = line.strip()
            if not s.endswith(":"):
                continue
            key = s[:-1].strip()
            low = key.lower()
            if not key:
                continue
            if low in ignored:
                continue
            if low.startswith("spcamera"):
                continue
            if low.startswith("usb") or low.startswith("built-in"):
                continue
            # Device groups are usually plain names with title case
            if len(key) > 1 and any(c.isalpha() for c in key):
                names.append(key)
        return names

    def _resolve_camera_capture_index(self, selected_idx):
        if hasattr(self, "camera_device_indices") and self.camera_device_indices:
            if 0 <= selected_idx < len(self.camera_device_indices):
                return self.camera_device_indices[selected_idx]
        return selected_idx

    def _scan_cameras(self, probe=False):
        """Get camera list. By default do not probe hardware to avoid startup camera access."""
        cameras = []
        indices = []
        
        # 1. Try PyGrabber (Best for Windows Names)
        if FilterGraph:
            try:
                graph = FilterGraph()
                devices = graph.get_input_devices()
                if devices:
                    self.camera_device_indices = list(range(len(devices)))
                    return devices
            except:
                pass
        
        # 2. Non-probing fallback (startup-safe)
        if not probe:
            self.camera_device_indices = []
            return []

        # 3. Fallback to OpenCV probing
        for i in range(8):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                indices.append(i)
            cap.release()

        if not indices:
            self.camera_device_indices = []
            return []

        # Use real camera names where possible
        if sys.platform == "darwin":
            names = self._macos_camera_names()
            for pos, idx in enumerate(indices):
                cameras.append(names[pos] if pos < len(names) else f"Camera {idx}")
        else:
            cameras = [f"Camera {idx}" for idx in indices]

        self.camera_device_indices = indices
        return cameras

    def _effective_music_volume(self, ui_value):
        """Map slider [0..1] to practical music gain."""
        v = max(0.0, min(1.0, float(ui_value)))
        return min(0.45, v ** 2.6)

    def _effective_sfx_volume(self, ui_value):
        """Map slider [0..1] to practical SFX gain."""
        v = max(0.0, min(1.0, float(ui_value)))
        return min(0.5, v ** 2.4)

    def _load_sounds(self):
        """Load sound effects."""
        sounds_dir = Path("src/sounds")
        
        for name in ["each", "complete", "hover", "click"]:
            for ext in [".mp3", ".wav"]:
                path = sounds_dir / f"{name}{ext}"
                if path.exists():
                    try:
                        self.sounds[name] = pygame.mixer.Sound(str(path))
                        print(f"[+] Sound loaded: {name}")
                        break
                    except Exception as e:
                        print(f"[!] Sound load error ({name}): {e}")
        
        # Load jutsu-specific sounds
        for name, data in self.jutsu_list.items():
            sound_path = data.get("sound_path")
            if sound_path and Path(sound_path).exists():
                try:
                    self.sounds[name] = pygame.mixer.Sound(sound_path)
                    if str(name).lower() == "chidori":
                        self.sounds[name].set_volume(0.3)
                    print(f"[+] Jutsu sound loaded: {name}")
                except Exception as e:
                    print(f"[!] Jutsu sound error ({name}): {e}")

    def _try_play_music(self):
        """Try to play background music."""
        music_paths = [
            Path("src/sounds/music2.mp3"),
            Path("src/sounds/music1.mp3"),
            Path("src/sounds/bgm.mp3"),
            Path("src/sounds/background.mp3"),
        ]
        
        for path in music_paths:
            if path.exists():
                try:
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.set_volume(self._effective_music_volume(self.settings["music_vol"]))
                    pygame.mixer.music.play(-1)  # Loop
                    self.music_playing = True
                    print(f"[+] Music playing: {path}")
                    break
                except Exception as e:
                    print(f"[!] Music error: {e}")

    def _load_icons(self):
        """Load hand sign icons."""
        pics_dir = Path("src/pics")
        class_names = get_class_names()
        
        for name in class_names:
            for ext in [".jpeg", ".jpg", ".png"]:
                path = pics_dir / f"{name}{ext}"
                if path.exists():
                    try:
                        img = pygame.image.load(str(path))
                        self.icons[name] = pygame.transform.smoothscale(img, (80, 80))
                        break
                    except:
                        pass

    def _load_logo(self):
        """Load logo image with proper aspect ratio."""
        logo_paths = [
            Path("src/pics/logo.png"),
            Path("src/pics/logo2.png"),
        ]
        for path in logo_paths:
            if path.exists():
                try:
                    img = pygame.image.load(str(path))
                    # Maintain aspect ratio - fit to max width 380, max height 200
                    w, h = img.get_size()
                    aspect = w / h
                    target_w = 380
                    target_h = int(target_w / aspect)
                    if target_h > 200:
                        target_h = 200
                        target_w = int(target_h * aspect)
                    self.logo = pygame.transform.smoothscale(img, (target_w, target_h))
                    break
                except:
                    pass

    def _load_background(self):
        """Load background image with proper aspect ratio (cover)."""
        bg_paths = [
            Path("src/socials/vl2.png"),
            Path("src/pics/bg.png"),
        ]
        for path in bg_paths:
            if path.exists():
                try:
                    img = pygame.image.load(str(path))
                    # Scale to cover (maintain aspect ratio, crop if needed)
                    img_w, img_h = img.get_size()
                    aspect = img_w / img_h
                    screen_aspect = SCREEN_WIDTH / SCREEN_HEIGHT
                    
                    if aspect > screen_aspect:
                        # Image is wider - scale by height
                        new_h = SCREEN_HEIGHT
                        new_w = int(new_h * aspect)
                    else:
                        # Image is taller - scale by width
                        new_w = SCREEN_WIDTH
                        new_h = int(new_w / aspect)
                    
                    scaled = pygame.transform.smoothscale(img, (new_w, new_h))
                    # Crop to center
                    x = (new_w - SCREEN_WIDTH) // 2
                    y = (new_h - SCREEN_HEIGHT) // 2
                    self.bg_image = scaled.subsurface((x, y, SCREEN_WIDTH, SCREEN_HEIGHT)).copy()
                    print(f"[+] Background loaded: {path}")
                    break
                except Exception as e:
                    print(f"[!] Background load error: {e}")
                    pass

    def _load_social_icons(self):
        """Load social media icons."""
        socials_dir = Path("src/socials")
        icon_names = ["ig", "yt", "discord"]
        
        for name in icon_names:
            for ext in [".png", ".jpg"]:
                path = socials_dir / f"{name}{ext}"
                if path.exists():
                    try:
                        img = pygame.image.load(str(path))
                        self.social_icons[name] = pygame.transform.smoothscale(img, (32, 32))
                        break
                    except:
                        pass

    def _load_mute_icons(self):
        """Load mute/unmute icons."""
        pics_dir = Path("src/pics")
        
        mute_path = pics_dir / "mute.png"
        unmute_path = pics_dir / "unmute.png"
        
        if mute_path.exists():
            try:
                img = pygame.image.load(str(mute_path))
                self.mute_icons["mute"] = pygame.transform.smoothscale(img, (32, 32))
            except:
                pass
        
        if unmute_path.exists():
            try:
                img = pygame.image.load(str(unmute_path))
                self.mute_icons["unmute"] = pygame.transform.smoothscale(img, (32, 32))
            except:
                pass

    def _load_arrow_icons(self):
        """Load arrow icons for navigation."""
        arrow_path = Path("src/pics/left-arrow.png")
        if arrow_path.exists():
            try:
                img = pygame.image.load(str(arrow_path))
                self.arrow_icons["left"] = pygame.transform.smoothscale(img, (50, 50))
                # Flip horizontally for right arrow
                self.arrow_icons["right"] = pygame.transform.flip(self.arrow_icons["left"], True, False)
                print("[+] Arrow icons loaded")
            except Exception as e:
                print(f"[!] Arrow icon error: {e}")

    def _load_jutsu_videos(self):
        """Load video paths for jutsu effects."""
        for name, data in self.jutsu_list.items():
            video_path = data.get("video_path")
            if video_path and Path(video_path).exists():
                self.jutsu_videos[name] = video_path
                print(f"[+] Jutsu video found: {name}")

    def toggle_mute(self):
        """Toggle music mute."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.set_volume(0)
        else:
            pygame.mixer.music.set_volume(self._effective_music_volume(self.settings["music_vol"]))

    def load_settings(self):
        """Load settings from file."""
        settings_path = Path("src/jutsu_academy/settings.json")
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    saved = json.load(f)
                    had_legacy_keys = ("use_mediapipe_signs" in saved) or ("restricted_signs" in saved)
                    # Keep only persisted user-editable keys.
                    allowed_keys = {"music_vol", "sfx_vol", "camera_idx", "debug_hands"}
                    sanitized = {k: v for k, v in saved.items() if k in allowed_keys}
                    self.settings.update(sanitized)
                    if had_legacy_keys:
                        with open(settings_path, "w") as out_f:
                            json.dump(sanitized, out_f, indent=2)
            except:
                pass
        # Force ON at runtime (not persisted in settings JSON).
        self.settings["use_mediapipe_signs"] = True
        self.settings["restricted_signs"] = True

    def save_settings(self):
        """Save settings to file."""
        settings_path = Path("src/jutsu_academy/settings.json")
        try:
            settings_path.parent.mkdir(exist_ok=True)
            with open(settings_path, "w") as f:
                persisted = {
                    "music_vol": self.settings.get("music_vol", 0.5),
                    "sfx_vol": self.settings.get("sfx_vol", 0.7),
                    "camera_idx": self.settings.get("camera_idx", 0),
                    "debug_hands": self.settings.get("debug_hands", False),
                }
                json.dump(persisted, f, indent=2)
        except:
            pass
