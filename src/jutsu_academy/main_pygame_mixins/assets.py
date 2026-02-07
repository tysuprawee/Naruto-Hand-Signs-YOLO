from src.jutsu_academy.main_pygame_shared import *


class AssetsMixin:
    def _scan_cameras(self):
        """Scan for available cameras with advanced names if possible."""
        cameras = []
        
        # 1. Try PyGrabber (Best for Windows Names)
        if FilterGraph:
            try:
                graph = FilterGraph()
                devices = graph.get_input_devices()
                if devices:
                    return devices
            except:
                pass
        
        # 2. Fallback to OpenCV
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(f"Camera {i}")
                cap.release()
        return cameras if cameras else ["Camera 0"]

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
                    if name == "chidori":
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
                    pygame.mixer.music.set_volume(self.settings["music_vol"])
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
            pygame.mixer.music.set_volume(self.settings["music_vol"])

    def load_settings(self):
        """Load settings from file."""
        settings_path = Path("src/jutsu_academy/settings.json")
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    saved = json.load(f)
                    self.settings.update(saved)
            except:
                pass

    def save_settings(self):
        """Save settings to file."""
        settings_path = Path("src/jutsu_academy/settings.json")
        try:
            settings_path.parent.mkdir(exist_ok=True)
            with open(settings_path, "w") as f:
                json.dump(self.settings, f, indent=2)
        except:
            pass
