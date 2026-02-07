from src.jutsu_academy.main_pygame_shared import *


class AuthMixin:
    def _load_user_session(self):
        """Load saved user session and refresh profile."""
        try:
            session_path = Path("user_session.json")
            if session_path.exists():
                with open(session_path) as f:
                    data = json.load(f)
                    self.username = data.get("username", "Guest")
                    self.discord_user = data.get("discord_user")
                    
                    if self.discord_user:
                        print(f"[+] Loaded session: {self.username}")
                        # Load avatar and refresh token in background
                        threading.Thread(target=self._load_discord_avatar, daemon=True).start()
                        threading.Thread(target=self._refresh_discord_token, daemon=True).start()
        except Exception as e:
            print(f"[!] Session load error: {e}")

    def _refresh_discord_token(self):
        """Validate current session token with Discord."""
        if not self.discord_user or "access_token" not in self.discord_user:
            return
            
        try:
            token = self.discord_user["access_token"]
            r = requests.get("https://discord.com/api/users/@me", 
                             headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r.status_code == 200:
                print("[+] Discord session validated")
            else:
                print("[-] Discord session expired or invalid")
                # We don't force logout yet, but could if needed
        except Exception as e:
            print(f"[!] Token refresh error: {e}")

    def _save_user_session(self):
        """Save user session to file."""
        try:
            data = {
                "username": self.username,
                "discord_user": self.discord_user
            }
            with open("user_session.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[!] Session save error: {e}")

    def _monitor_connection_loop(self):
        """Monitor internet connection in background."""
        while True:
            try:
                # Ping Google DNS
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                self.connection_fail_count = 0
            except OSError:
                if self.state != GameState.CONNECTION_LOST:
                    print(f"[!] Connection check failed ({self.connection_fail_count + 1})")
                    self.connection_fail_count += 1
                    
                    if self.connection_fail_count >= 3:
                        print("[!] Connection lost. Terminating session.")
                        # Logout and show connection lost screen
                        self.logout_discord()
                        self.state = GameState.CONNECTION_LOST
            
            time.sleep(10) # Check every 10 seconds

    def _create_rounded_avatar(self, img_data, size=(40, 40)):
        """Convert raw image data to a rounded pygame surface using PIL for smooth masking."""
        try:
            from PIL import Image, ImageDraw
            if isinstance(img_data, bytes):
                pil_img = Image.open(BytesIO(img_data))
            else:
                pil_img = Image.open(img_data) # Path
                
            pil_img = pil_img.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
            
            # Create smooth rounded rectangle mask
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            # Use radius ~20% of size for a modern "squircle" look
            radius = size[0] // 5
            draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
            
            # Apply mask to alpha channel
            pil_img.putalpha(mask)
            
            # Convert back to pygame surface
            data = pil_img.tobytes()
            return pygame.image.fromstring(data, size, "RGBA")
        except Exception as e:
            print(f"[!] Avatar rounding error: {e}")
            return self._get_fallback_avatar(size)

    def _get_fallback_avatar(self, size=(40, 40)):
        """Load the shadow fallback and round it."""
        path = "src/pics/shadow.jpg"
        if not os.path.exists(path):
            # Procedural fallback if file missing
            surf = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.circle(surf, (60, 60, 70), (size[0]//2, size[1]//2), size[0]//2)
            return surf
        return self._create_rounded_avatar(path, size)

    def _load_discord_avatar(self):
        """Load Discord avatar from URL and round it."""
        if not self.discord_user:
            self.user_avatar = self._get_fallback_avatar()
            return
            
        try:
            user_id = self.discord_user.get("id")
            avatar_hash = self.discord_user.get("avatar")
            if user_id and avatar_hash:
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=64"
                response = requests.get(avatar_url, timeout=5)
                if response.status_code == 200:
                    self.user_avatar = self._create_rounded_avatar(response.content)
                    print("[+] Avatar loaded and rounded")
                    return
        except Exception as e:
            print(f"[!] Avatar fetch error: {e}")
            
        # Fallback
        self.user_avatar = self._get_fallback_avatar()

    def start_discord_login(self):
        """Start Discord login in background thread."""
        if self.discord_user:
            print("[AUTH] Already logged in")
            return
        
        if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
            print("[AUTH] Missing Discord credentials in env")
            return

        now = time.time()

        if self.login_in_progress:
            # Check if we have an active auth instance
            if self.auth_instance:
                # Reopen browser with potentially new random state
                url = self.auth_instance.get_authorize_url()
                print(f"[AUTH][attempt={self.login_attempt_id}] Resume: Reopening browser with fresh state")
                webbrowser.open(url)
                # Store the new URL just in case, though we primarily just open it
                self.discord_auth_url = url
                return

            # If stuck too long, force cancel and restart
            if self.login_started_at and (now - self.login_started_at) > self.login_timeout_s:
                print(f"[AUTH][attempt={self.login_attempt_id}] Stuck > timeout; forcing cancel/restart")
                self.cancel_discord_login()
            else:
                # Wait for init
                print(f"[AUTH][attempt={self.login_attempt_id}] Login initializing...")
                return

        # Start new attempt
        self.login_attempt_id += 1
        attempt_id = self.login_attempt_id
        self.login_in_progress = True
        self.login_started_at = now
        self.login_error = ""
        self.discord_auth_url = None

        print(f"[AUTH][attempt={attempt_id}] Starting login thread")
        threading.Thread(target=self._do_discord_login, args=(attempt_id,), daemon=True).start()

    def cancel_discord_login(self):
        """Cancel current login attempt."""
        # Shutdown current server if active
        if self.auth_instance:
            print("[AUTH] Shutting down active auth server...")
            self.auth_instance.shutdown()
            self.auth_instance = None
            
        self.login_attempt_id += 1  # invalidate old attempts
        self.login_in_progress = False
        self.login_started_at = 0.0
        self.discord_auth_url = None
        self.login_error = "Canceled"
        print(f"[AUTH] Cancel requested. New current attempt={self.login_attempt_id}")

    def _do_discord_login(self, attempt_id):
        """Perform Discord login (runs in thread)."""
        try:
            from src.jutsu_academy.discord_auth import DiscordLogin
            # Create and store instance
            auth = DiscordLogin(DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET)
            self.auth_instance = auth

            # Expose the URL
            self.discord_auth_url = auth.get_authorize_url()
            print(f"[AUTH][attempt={attempt_id}] URL ready: {self.discord_auth_url[:50]}...")
            webbrowser.open(self.discord_auth_url)
            print(f"[AUTH][attempt={attempt_id}] Browser opened")

            # Wait for login
            user = auth.login(timeout=self.login_timeout_s)

            # Stale attempt guard
            if attempt_id != self.login_attempt_id:
                print(f"[AUTH][attempt={attempt_id}] Stale result ignored (current={self.login_attempt_id})")
                return

            if user:
                self.discord_user = user
                self.username = user.get("username", "User")
                self.progression = ProgressionManager(self.username, network_manager=self.network_manager) # Reload for new user
                self._save_user_session()
                self._save_user_session()
                threading.Thread(target=self._load_discord_avatar, daemon=True).start()
                print(f"[AUTH][attempt={attempt_id}] Success: {self.username}")
                # Show welcome modal
                self.state = GameState.WELCOME_MODAL
            else:
                self.login_error = "Login timed out. Please try again."
                print(f"[AUTH][attempt={attempt_id}] No user returned (timeout/cancel)")
                # Show modal with error
                if self.state != GameState.MENU:
                    self.state = GameState.LOGIN_MODAL

        except Exception as e:
            if attempt_id == self.login_attempt_id:
                self.login_error = "Login failed. Please try again."
                if self.state != GameState.MENU:
                    self.state = GameState.LOGIN_MODAL
            print(f"[AUTH][attempt={attempt_id}] Error: {e}")

        finally:
            # Cleanup auth instance reference if it matches this thread's
            if self.auth_instance == auth:
                self.auth_instance = None
                
            # Only clear status if this attempt is still current
            if attempt_id == self.login_attempt_id:
                self.login_in_progress = False
                self.discord_auth_url = None
                print(f"[AUTH][attempt={attempt_id}] Login finished; in_progress=False")

    def logout_discord(self):
        """Log out Discord user."""
        self.discord_user = None
        self.username = "Guest"
        self.username = "Guest"
        self.progression = ProgressionManager(self.username, network_manager=self.network_manager) # Reset to guest progress
        self.user_avatar = None
        self.user_avatar = None
        # Delete session file
        try:
            Path("user_session.json").unlink(missing_ok=True)
        except:
            pass
        print("[*] Logged out")
