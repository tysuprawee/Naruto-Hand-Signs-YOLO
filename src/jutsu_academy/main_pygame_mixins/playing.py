from src.jutsu_academy.main_pygame_shared import *
from src.jutsu_academy.effects import EffectContext


class PlayingMixin:
    def _render_challenge_lobby(self, cam_x, cam_y, cam_w, cam_h):
        """Draw dimmed lobby with 'Press SPACE to Start'."""
        overlay = pygame.Surface((cam_w, cam_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (cam_x, cam_y))
        
        # Text
        txt = self.fonts["title_md"].render("PRESS [SPACE] TO START", True, COLORS["accent_glow"])
        rect = txt.get_rect(center=(cam_x + cam_w // 2, cam_y + cam_h // 2 - 40))
        self.screen.blit(txt, rect)
        
        sub = self.fonts["body"].render("Perform the sequence as FAST as possible!", True, COLORS["text_dim"])
        self.screen.blit(sub, sub.get_rect(center=(cam_x + cam_w // 2, cam_y + cam_h // 2 + 20)))
        rules = [
            "1. Timer starts on 'GO!'",
            "2. Detect all hand signs in order.",
            "3. Timer stops on the final sign."
        ]
        for i, r in enumerate(rules):
            rt = self.fonts["body_sm"].render(r, True, COLORS["text"])
            self.screen.blit(rt, rt.get_rect(center=(cam_x + cam_w // 2, cam_y + cam_h // 2 + 80 + i*25)))

    def _render_challenge_countdown(self, cam_x, cam_y, cam_w, cam_h):
        """Draw big countdown in center."""
        elapsed = time.time() - self.challenge_countdown_start
        remaining = 3 - int(elapsed)
        
        if remaining > 0:
            frac = 1.0 - (elapsed % 1.0) 
            size = int(120 * (1.0 + 0.5 * frac)) 
            font = pygame.font.Font(None, size) 
            
            txt = font.render(str(remaining), True, (255, 255, 0)) 
            rect = txt.get_rect(center=(cam_x + cam_w // 2, cam_y + cam_h // 2))
            self.screen.blit(txt, rect)
        else:
            self.challenge_state = "active"
            self.challenge_start_time = time.time()
            self.last_sign_time = time.time()
            self.play_sound("complete")

    def _render_challenge_results(self, cam_x, cam_y, cam_w, cam_h):
        """Draw results overlay with Rank and stats."""
        overlay = pygame.Surface((cam_w, cam_h), pygame.SRCALPHA)
        overlay.fill((10, 10, 15, 200)) 
        self.screen.blit(overlay, (cam_x, cam_y))
        
        # Card style
        card_w, card_h = min(cam_w - 40, 480), min(cam_h - 40, 400)
        card = pygame.Rect(cam_x + (cam_w - card_w) // 2, cam_y + (cam_h - card_h) // 2, card_w, card_h)
        pygame.draw.rect(self.screen, (25, 25, 30), card, border_radius=20)
        pygame.draw.rect(self.screen, COLORS["accent"], card, 2, border_radius=20)
        
        # Title
        t = self.fonts["title_md"].render("RESULTS", True, COLORS["accent"])
        self.screen.blit(t, t.get_rect(center=(card.centerx, card.y + 50)))
        
        # Final Time
        time_str = f"{self.challenge_final_time:.2f}s"
        st = self.fonts["title_lg"].render(time_str, True, COLORS["success"])
        self.screen.blit(st, st.get_rect(center=(card.centerx, card.y + 130)))
        
        # Rank Info
        if self.challenge_submitting:
            info = "Submitting score..."
            color = COLORS["text_dim"]
        elif self.challenge_rank_info:
            info = self.challenge_rank_info
            color = (255, 215, 0) # Gold
        else:
            info = "Awaiting response..."
            color = COLORS["text_dim"]
            
        rt = self.fonts["body"].render(info, True, color)
        self.screen.blit(rt, rt.get_rect(center=(card.centerx, card.y + 200)))
        
        # Help
        h1 = self.fonts["body_sm"].render("Press [SPACE] to Try Again", True, COLORS["text"])
        self.screen.blit(h1, h1.get_rect(center=(card.centerx, card.y + 280)))
        
        h2 = self.fonts["body_sm"].render("Press [ESC] to Exit", True, COLORS["text_dim"])
        self.screen.blit(h2, h2.get_rect(center=(card.centerx, card.y + 310)))
        
        # Trigger submission once
        if not self.challenge_submitting and not self.submission_complete:
            self.challenge_submitting = True
            threading.Thread(target=self._submit_challenge_score, daemon=True).start()

    def _submit_challenge_score(self):
        """Background thread to submit score and calculate local rank."""
        try:
            jutsu_name = self.jutsu_names[self.current_jutsu_idx]
            username = self.username if self.username else "Guest"
            
            d_id = None
            avatar_url = None
            if self.discord_user:
                d_id = self.discord_user.get("id")
                avatar_hash = self.discord_user.get("avatar")
                if d_id and avatar_hash:
                    avatar_url = f"https://cdn.discordapp.com/avatars/{d_id}/{avatar_hash}.png?size=64"
            
            # 1. Submit
            self.network_manager.submit_score(
                username, 
                self.challenge_final_time, 
                mode=jutsu_name.upper(),
                discord_id=d_id,
                avatar_url=avatar_url
            )
            
            # 2. Get Leadboard to find rank (simulated for immediate feedback)
            # Fetch enough to find approximate rank
            data = self.network_manager.get_leaderboard(limit=100, mode=jutsu_name.upper())
            rank = -1
            total = len(data)
            
            if data:
                for i, row in enumerate(data):
                    # Find our score
                    if abs(row.get("score_time", 0) - self.challenge_final_time) < 0.001:
                         rank = i + 1
                         break
                
                if rank > 0:
                    percentile = ((total - rank + 1) / total) * 100
                    self.challenge_rank_info = f"Rank: #{rank} (Top {percentile:.0f}%)"
                else:
                    self.challenge_rank_info = "Rank: Top 100+"
            else:
                 self.challenge_rank_info = "Rank: #1 (First Record!)"
                 
        except Exception as e:
            print(f"[!] Submission Error: {e}")
            self.challenge_rank_info = "Error submitting score."
        
        self.challenge_submitting = False
        self.submission_complete = True

    def render_playing(self, dt):
        """Render game playing state with Challenge Mode support."""
        # 1. Background Logic - Always draw first to clear previous frame
        if hasattr(self, 'bg_image') and self.bg_image:
             if hasattr(self, 'last_screen_w') and self.last_screen_w != SCREEN_WIDTH:
                 # Rescale background if screen size changes (simplified check)
                 self.bg_image = pygame.transform.smoothscale(self.bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
                 self.last_screen_w = SCREEN_WIDTH
             self.screen.blit(self.bg_image, (0, 0))
             
             # Professional darken overlay
             overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, 180)) 
             self.screen.blit(overlay, (0, 0))
        else:
             self.screen.fill(COLORS["bg_dark"])
        
        if self.cap is None or not self.cap.isOpened():
            self._draw_text_center("Camera Disconnected", 0, COLORS["error"])
            return
        
        ret, frame = self.cap.read()
        if not ret:
            self._draw_text_center("Camera blocked! Check OBS/Discord.", 0, COLORS["error"])
            return
        
        # Flip for mirror
        frame = cv2.flip(frame, 1)
        
        # Camera position on screen (Centered & Scaled)
        # We want to fill the screen as much as possible while maintaining aspect ratio
        frame_h, frame_w = frame.shape[:2]
        
        # Calculate scaling to fit screen height (Careful with 768p constraint)
        # 768 - 45(HUD) - 50(Title) - 135(Icons) - 60(Margins) = ~478
        target_h = SCREEN_HEIGHT - 300 
        scale = target_h / frame_h
        
        new_w = int(frame_w * scale)
        new_h = int(frame_h * scale)
        
        cam_x = (SCREEN_WIDTH - new_w) // 2
        cam_y = 100 # Moved up slightly to save space
        if hasattr(self, "playing_back_button"):
            self.playing_back_button.rect.width = 120
            self.playing_back_button.rect.height = 42
            # Keep clear of top HUD text and avoid overlapping the camera frame/title.
            self.playing_back_button.rect.x = max(16, cam_x - self.playing_back_button.rect.width - 24)
            self.playing_back_button.rect.y = max(56, cam_y + 6)
        
        # 1. Challenge Mode Visibility
        should_detect = True
        if self.game_mode == "challenge":
            if self.challenge_state in ["waiting", "countdown", "results"]:
                should_detect = False
                
        # 1.5 Locked Check (Shinobi Path)
        current_jutsu_name = self.jutsu_names[self.current_jutsu_idx]
        min_lv = self.jutsu_list[current_jutsu_name].get("min_level", 0)
        is_locked = self.progression.level < min_lv
        if is_locked:
            should_detect = False
        
        # 2. Detection Flow
        detected = None
        if should_detect:
            if not self.jutsu_active:
                # Sequence Phase: Recognition
                if self.settings.get("use_mediapipe_signs", False):
                    # Use MediaPipe Tasks API for sign recognition
                    self.detect_hands(frame) # This populates self.last_mp_result if successful
                    
                    if hasattr(self, 'last_mp_result') and self.last_mp_result.hand_landmarks:
                        features = self.recorder.process_tasks_landmarks(
                            self.last_mp_result.hand_landmarks, 
                            self.last_mp_result.handedness
                        )
                        detected = self.recorder.predict(features).lower()
                        
                        # --- 2-Hand Restriction logic ---
                        if self.settings.get("restricted_signs", False):
                            num_hands = len(self.last_mp_result.hand_landmarks)
                            if num_hands < 2:
                                detected = "idle"
                        
                        # (Removed moving OpenCV text to use static Pygame text below)
                    else:
                        detected = "Idle"
                else:
                    # Legacy Phase: Use YOLO for hand sign recognition (bounding boxes)
                    frame, detected = self.detect_and_process(frame)
            else:
                # Effect Phase: switch to MediaPipe for precise tracking
                self.detect_hands(frame)
                self.detect_face(frame)
        
        # 3. Process Sequence
        self.effect_orchestrator.on_sign_detected(
            detected,
            EffectContext(
                frame_bgr=frame,
                frame_shape=frame.shape,
                hand_pos=self.hand_pos,
                mouth_pos=self.mouth_pos,
                cam_x=cam_x,
                cam_y=cam_y,
                scale_x=(new_w / max(1, frame_w)),
                scale_y=(new_h / max(1, frame_h)),
            ),
        )

        if not self.jutsu_active and should_detect:
            # Check sequence
            if self.current_step < len(self.sequence):
                target = self.sequence[self.current_step]
                if detected == target:
                    now = time.time()
                    if now - self.last_sign_time > self.cooldown:
                        self.current_step += 1
                        self.last_sign_time = now
                        self.play_sound("each")
                        
                        if self.current_step >= len(self.sequence):
                            self.jutsu_active = True
                            self.jutsu_start_time = time.time()
                            self.current_step = 0
                            self.play_sound("complete")
                            
                            # Award XP (Robust Progression)
                            jutsu_name = self.jutsu_names[self.current_jutsu_idx]
                            seq_len = len(self.jutsu_list[jutsu_name]["sequence"])
                            bonus = seq_len * 10
                            total_xp = 50 + bonus # Base 50 + complexity bonus
                            
                            prev_level = self.progression.level
                            is_lv_up = self.progression.add_xp(total_xp)
                            self.process_unlock_alerts(previous_level=prev_level)
                            
                            # Add XP popup (Centered on Camera feed)
                            self.xp_popups.append({
                                "text": f"+{total_xp} XP", 
                                "x": cam_x + new_w // 2, 
                                "y": cam_y + new_h // 2, 
                                "timer": 2.0, 
                                "color": COLORS["accent"]
                            })
                            if is_lv_up:
                                self.xp_popups.append({
                                    "text": f"RANK UP: {self.progression.rank}!", 
                                    "x": cam_x + new_w // 2, 
                                    "y": cam_y + new_h // 2 + 40, 
                                    "timer": 3.0, 
                                    "color": COLORS["success"]
                                })
                            
                            # STOP TIMER if in challenge
                            if self.game_mode == "challenge":
                                self.challenge_final_time = self.jutsu_start_time - self.challenge_start_time
                            
                            jutsu_name = self.jutsu_names[self.current_jutsu_idx]
                            jutsu_data = self.jutsu_list[jutsu_name]
                            effect = jutsu_data.get("effect")
                            
                            # Schedule jutsu-specific sound (0.5s delay)
                            if jutsu_name in self.sounds:
                                self.pending_sound = {
                                    "name": jutsu_name,
                                    "time": time.time() + 0.5
                                }
                            
                            # Start effect based on type
                            if effect == "fire":
                                self.fire_particles.emitting = True
                            self.effect_orchestrator.on_jutsu_start(
                                effect,
                                EffectContext(jutsu_name=jutsu_name),
                            )
                            
                            # Start video overlay if available
                            if jutsu_name in self.jutsu_videos:
                                video_path = self.jutsu_videos[jutsu_name]
                                self.video_cap = cv2.VideoCapture(video_path)
                                self.current_video = jutsu_name
                                print(f"[+] Playing video: {video_path}")
        
        # (Camera dimensions already calculated at the top)
        
        # Update particles with correct screen position based on new scale
        if self.fire_particles.emitting and self.mouth_pos:
            # Convert camera frame coords to screen coords
            # Landmark coords are normalized (0-1), multiplied by frame size in detect methods
            # Here self.mouth_pos is likely in frame pixels. 
            # We need to scale it.
            
            # Note: stored self.mouth_pos is raw frame pixels (640x480)
            screen_x = cam_x + int(self.mouth_pos[0] * scale)
            screen_y = cam_y + int(self.mouth_pos[1] * scale)
            self.fire_particles.set_position(screen_x, screen_y)
            self.fire_particles.wind_x = -self.head_yaw * 200
        self.fire_particles.update(dt)
        self.effect_orchestrator.update(
            EffectContext(
                dt=dt,
                frame_bgr=frame,
                frame_shape=frame.shape,
                hand_pos=self.hand_pos,
                mouth_pos=self.mouth_pos,
                cam_x=cam_x,
                cam_y=cam_y,
                scale_x=(new_w / max(1, frame_w)),
                scale_y=(new_h / max(1, frame_h)),
            )
        )
        
        # Check jutsu duration
        if self.jutsu_active:
            if time.time() - self.jutsu_start_time > self.jutsu_duration:
                self.jutsu_active = False
                self.fire_particles.emitting = False
                self.effect_orchestrator.on_jutsu_end(EffectContext())
                self.current_video = None
                if self.video_cap:
                    self.video_cap.release()
                    self.video_cap = None
                
                # Check for results transition
                if self.game_mode == "challenge":
                    self.challenge_state = "results"
        
        # Convert and display frame with alpha blending for dimming
        if self.game_mode == "challenge" and self.challenge_state in ["waiting", "countdown", "results"]:
            # Dim the camera frame
            frame = (frame.astype(np.float32) * 0.4).astype(np.uint8)
            
        cam_surface = self.cv2_to_pygame(frame)
        cam_surface = pygame.transform.smoothscale(cam_surface, (new_w, new_h))
        
        # UI Frame for camera feed
        pygame.draw.rect(self.screen, (30, 30, 40), (cam_x - 6, cam_y - 6, new_w + 12, new_h + 12), border_radius=14)
        pygame.draw.rect(self.screen, COLORS["border"], (cam_x - 6, cam_y - 6, new_w + 12, new_h + 12), 2, border_radius=14)
        
        self.screen.blit(cam_surface, (cam_x, cam_y))
        
        if self.jutsu_active:
             jutsu_name = self.jutsu_names[self.current_jutsu_idx]
             if self.jutsu_list[jutsu_name].get("effect") == "lightning":
                  # Create a lightning-blue transparent overlay
                  blue_overlay = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
                  blue_overlay.fill((0, 80, 150, 40)) # Light blue tint
                  self.screen.blit(blue_overlay, (cam_x, cam_y))

        
        # Fire particles
        self.fire_particles.render(self.screen)
        self.effect_orchestrator.render(
            self.screen,
            EffectContext(
                frame_bgr=frame,
                frame_shape=frame.shape,
                cam_x=cam_x,
                cam_y=cam_y,
                scale_x=(new_w / max(1, frame_w)),
                scale_y=(new_h / max(1, frame_h)),
                font=self.fonts["tiny"],
                debug=self.settings.get("debug_hands", False),
            ),
        )
        
        # Timer Display (Challenge Mode Active) - Draw on top of frame but under results
        if self.game_mode == "challenge" and self.challenge_state == "active":
            if self.jutsu_active:
                elapsed = self.challenge_final_time
            else:
                elapsed = time.time() - self.challenge_start_time
            
            # Speedrun Style Timer
            time_str = f"{elapsed:.2f}s"
            t_txt = self.fonts["title_sm"].render(f"SPEED: {time_str}", True, (255, 255, 255))
            
            # Simple dark backing
            tw, th = t_txt.get_size()
            t_bg = pygame.Surface((tw + 24, th + 12), pygame.SRCALPHA)
            t_bg.fill((0, 0, 0, 140))
            pygame.draw.rect(t_bg, COLORS["accent"], t_bg.get_rect(), 1, border_radius=6)
            self.screen.blit(t_bg, (cam_x + 15, cam_y + 15))
            self.screen.blit(t_txt, (cam_x + 27, cam_y + 21))

        # --- Static Sign Prediction Label (Fixed Top-Right) ---
        if detected and detected != "Idle":
            pred_txt = self.fonts["body"].render(f"SIGN: {detected.upper()}", True, (255, 255, 255))
            tw, th = pred_txt.get_size()
            
            # Label Panel (Top Right of cam)
            lx, ly = cam_x + new_w - tw - 30, cam_y + 15
            lp_rect = pygame.Rect(lx - 12, ly - 6, tw + 24, th + 12)
            
            # Glass effect for label
            lp_surf = pygame.Surface((lp_rect.width, lp_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(lp_surf, (20, 20, 30, 200), (0, 0, lp_rect.width, lp_rect.height), border_radius=8)
            pygame.draw.rect(lp_surf, COLORS["success"], (0, 0, lp_rect.width, lp_rect.height), 1, border_radius=8)
            self.screen.blit(lp_surf, lp_rect)
            self.screen.blit(pred_txt, (lx, ly))

        elif self.state == GameState.WELCOME_MODAL:
            self.render_welcome_modal(dt)
        elif self.state == GameState.QUIT_CONFIRM:
            self.render_quit_confirm()
        elif self.state == GameState.LOGOUT_CONFIRM:
            self.render_logout_confirm()
        
        # --- Challenge Overlays (Responsive) ---
        if self.game_mode == "challenge" and not is_locked:
            if self.challenge_state == "waiting":
                self._render_challenge_lobby(cam_x, cam_y, new_w, new_h)
            elif self.challenge_state == "countdown":
                self._render_challenge_countdown(cam_x, cam_y, new_w, new_h)
            elif self.challenge_state == "results":
                self._render_challenge_results(cam_x, cam_y, new_w, new_h)
        
        # Sound Scheduler
        if hasattr(self, "pending_sound") and self.pending_sound:
             if time.time() >= self.pending_sound["time"]:
                 self.play_sound(self.pending_sound["name"])
                 self.pending_sound = None
        
        # Video overlay (for Chidori, Rasengan, etc.)
        if self.current_video and self.video_cap and self.video_cap.isOpened():
            ret, vid_frame = self.video_cap.read()
            if ret:
                # Track Hand
                if hasattr(self, 'hand_pos') and self.hand_pos:
                    hx, hy = self.hand_pos
                    size = 650 # Significantly bigger Chidori
                else:
                    hx, hy = 320, 240
                    size = 500 # Center if no hand
                
                # Calculate aspect ratio to avoid stretching
                v_h, v_w = vid_frame.shape[:2]
                aspect = v_w / v_h
                
                if aspect > 1: # Landscape
                    dw, dh = size, int(size / aspect)
                else: # Portrait/Square
                    dw, dh = int(size * aspect), size
                
                # Resize video (Maintaining aspect ratio)
                vid_frame = cv2.resize(vid_frame, (dw, dh))
                
                # Apply Radial Feathering (Removes hard square edges from video frame)
                # Create coordinate grids
                Y, X = np.ogrid[:dh, :dw]
                center_x, center_y = dw // 2, dh // 2
                # Normalized elliptical distance (0.0 at center, 1.0 at edges)
                dist = np.sqrt(((X - center_x) / (dw / 2))**2 + ((Y - center_y) / (dh / 2))**2)
                # Soft fade starting at 65% of the radius
                mask = np.clip(1.0 - (dist - 0.65) / 0.35, 0, 1)
                mask = (mask ** 1.5).astype(np.float32) # Smooth falloff
                # Apply mask to RGB values
                vid_frame = (vid_frame.astype(np.float32) * mask[:, :, np.newaxis]).astype(np.uint8)
                
                vid_frame = cv2.cvtColor(vid_frame, cv2.COLOR_BGR2RGB)
                vid_frame = np.rot90(vid_frame)
                vid_frame = np.flipud(vid_frame)
                vid_surface = pygame.surfarray.make_surface(vid_frame)
                
                # Blit centered on hand with additive blending
                self.screen.blit(vid_surface, (cam_x + hx - dw//2, cam_y + hy - dh//2), special_flags=pygame.BLEND_RGB_ADD)
            else:
                # Video ended, loop it
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # Progression HUD (MMO Style Top Bar)
        hud_h = 45
        hud_bg = pygame.Surface((SCREEN_WIDTH, hud_h), pygame.SRCALPHA)
        hud_bg.fill((20, 20, 25, 230))
        self.screen.blit(hud_bg, (0, 0))
        pygame.draw.line(self.screen, COLORS["border"], (0, hud_h), (SCREEN_WIDTH, hud_h), 1)

        # Level Badge
        badge_txt = f"{self.progression.rank} • LV.{self.progression.level}"
        badge_surf = self.fonts["body"].render(badge_txt, True, (255, 255, 255))
        self.screen.blit(badge_surf, (20, (hud_h - badge_surf.get_height()) // 2))

        # XP Bar (Centered Top)
        bar_w = 400
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = (hud_h - 12) // 2 + 2
        
        prev_lv_xp = self.progression.get_xp_for_level(self.progression.level)
        next_lv_xp = self.progression.get_xp_for_level(self.progression.level + 1)
        progress = (self.progression.xp - prev_lv_xp) / max(1, (next_lv_xp - prev_lv_xp))
        progress = max(0, min(1, progress))

        pygame.draw.rect(self.screen, (40, 40, 50), (bar_x, bar_y, bar_w, 10), border_radius=5)
        if progress > 0:
            pygame.draw.rect(self.screen, COLORS["accent"], (bar_x, bar_y, bar_w * progress, 10), border_radius=5)
            # Gloss
            pygame.draw.rect(self.screen, (255, 255, 255, 30), (bar_x, bar_y, bar_w * progress, 5), border_radius=5)

        xp_txt = f"{self.progression.xp} / {next_lv_xp} XP"
        xp_surf = self.fonts["tiny"].render(xp_txt, True, COLORS["text_dim"])
        self.screen.blit(xp_surf, (bar_x + bar_w + 10, bar_y - 3))

        # XP Popups
        for popup in self.xp_popups[:]:
            popup["timer"] -= dt
            if popup["timer"] <= 0:
                self.xp_popups.remove(popup)
                continue
            
            # Float up
            popup["y"] -= 40 * dt
            # Fade out
            alpha = int(min(255, popup["timer"] * 255))
            
            p_surf = self.fonts["title_sm"].render(popup["text"], True, popup["color"])
            p_surf.set_alpha(alpha)
            self.screen.blit(p_surf, p_surf.get_rect(center=(popup["x"], popup["y"])))

        # Icon bar
        # If locked, don't show sequence icons but a lock message
        if is_locked:
            lock_msg = self.fonts["body"].render(f"REQUIRED RANK: LV.{min_lv}", True, COLORS["error"])
            self.screen.blit(lock_msg, lock_msg.get_rect(center=(cam_x + new_w // 2, cam_y + new_h + 40)))
        else:
            self._render_icon_bar(cam_x, cam_y + new_h + 10, new_w)
        
        # Move Title (Styled Capsule)
        display_name = current_jutsu_name.upper() if not is_locked else "??????"
        text_color = (255, 255, 255) if not is_locked else (100, 100, 100)
        
        name_surf = self.fonts["title_sm"].render(display_name, True, text_color)
        tw, th = name_surf.get_size()
        
        padding_x, padding_y = 35, 10
        title_rect = pygame.Rect(cam_x + (new_w - tw - padding_x*2)//2, cam_y - 48, tw + padding_x*2, th + padding_y*2)
        
        if not is_locked:
            # Subtle Glow
            glow_rect = title_rect.inflate(6, 6)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (249, 115, 22, 30), (0, 0, glow_rect.width, glow_rect.height), border_radius=20)
            self.screen.blit(glow_surf, glow_rect)
            
            pygame.draw.rect(self.screen, (20, 20, 25), title_rect, border_radius=18)
            pygame.draw.rect(self.screen, COLORS["accent"], title_rect, 2, border_radius=18)
        else:
            # Grayed out for locked
            pygame.draw.rect(self.screen, (25, 25, 30), title_rect, border_radius=18)
            pygame.draw.rect(self.screen, (60, 60, 70), title_rect, 2, border_radius=18)

        self.screen.blit(name_surf, (title_rect.centerx - tw//2, title_rect.centery - th//2))
        
        # FPS Counter (Styled)
        self.frame_count += 1
        if time.time() - self.fps_timer >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.fps_timer = time.time()
        
        fps_txt = f"FPS: {self.fps}"
        fps_surf = self.fonts["tiny"].render(fps_txt, True, COLORS["success"])
        self.screen.blit(fps_surf, (cam_x + new_w - fps_surf.get_width() - 5, cam_y - 18))
        
        # Navigation arrows - Only show if not active and (if challenge) in waiting room
        show_nav = not self.jutsu_active
        if self.game_mode == "challenge" and self.challenge_state != "waiting":
            show_nav = False
            
        if show_nav:
            mouse_pos = pygame.mouse.get_pos()
            arrow_y = cam_y + new_h // 2 - 30
            
            # MODERN ARROWS: Semi-transparent circular buttons
            # Left Button
            l_btn_rect = pygame.Rect(cam_x - 70, arrow_y, 50, 60)
            self.left_arrow_rect = l_btn_rect
            l_hover = l_btn_rect.collidepoint(mouse_pos)
            
            l_alpha = 200 if l_hover else 120
            l_surf = pygame.Surface((50, 60), pygame.SRCALPHA)
            pygame.draw.rect(l_surf, (20, 20, 25, l_alpha), (0, 0, 50, 60), border_radius=10)
            pygame.draw.rect(l_surf, (*COLORS["accent"], l_alpha), (0, 0, 50, 60), 2, border_radius=10)
            
            # Triangle icon
            p1, p2, p3 = (35, 15), (15, 30), (35, 45)
            pygame.draw.polygon(l_surf, (255, 255, 255, l_alpha), [p1, p2, p3])
            self.screen.blit(l_surf, l_btn_rect)
            if l_hover: pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

            # Right Button
            r_btn_rect = pygame.Rect(cam_x + new_w + 20, arrow_y, 50, 60)
            self.right_arrow_rect = r_btn_rect
            r_hover = r_btn_rect.collidepoint(mouse_pos)
            
            r_alpha = 200 if r_hover else 120
            r_surf = pygame.Surface((50, 60), pygame.SRCALPHA)
            pygame.draw.rect(r_surf, (20, 20, 25, r_alpha), (0, 0, 50, 60), border_radius=10)
            pygame.draw.rect(r_surf, (*COLORS["accent"], r_alpha), (0, 0, 50, 60), 2, border_radius=10)
            
            # Triangle icon
            p1, p2, p3 = (15, 15), (35, 30), (15, 45)
            pygame.draw.polygon(r_surf, (255, 255, 255, r_alpha), [p1, p2, p3])
            self.screen.blit(r_surf, r_btn_rect)
            if r_hover: pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            

        else:
            if hasattr(self, "left_arrow_rect"): del self.left_arrow_rect
            if hasattr(self, "right_arrow_rect"): del self.right_arrow_rect
        
        # ESC hint
        hint = self.fonts["body_sm"].render("Press ESC to exit", True, COLORS["text_muted"])
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT - 30))

        if hasattr(self, "playing_back_button"):
            self.playing_back_button.render(self.screen)

    def _render_icon_bar(self, x, y, bar_w):
        """Render the jutsu sequence icon bar with dynamic scaling."""
        n = len(self.sequence)
        max_icon_size = 80
        gap = 12
        max_total_w = bar_w - 30 # padding within frame
        
        # Calculate optimal icon size
        icon_size = max_icon_size
        total_w = n * icon_size + (n - 1) * gap
        
        if total_w > max_total_w:
            icon_size = (max_total_w - (n - 1) * gap) // n
            icon_size = max(40, icon_size) 
            total_w = n * icon_size + (n - 1) * gap
            
        start_x = x + (bar_w - total_w) // 2
        
        # Background panel (Responsive)
        panel_h = 135
        panel_rect = pygame.Rect(x, y, bar_w, panel_h)
        # Deep translucent background
        panel_surf = pygame.Surface((bar_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (20, 20, 30, 240), (0, 0, bar_w, panel_h), border_radius=15)
        self.screen.blit(panel_surf, (x, y))
        pygame.draw.rect(self.screen, COLORS["border"], (x, y, bar_w, panel_h), 2, border_radius=15)
        
        # Status text
        icon_y_start = y + 45
        if self.jutsu_active:
            display = self.jutsu_list[self.jutsu_names[self.current_jutsu_idx]].get("display_text", "")
            status = self.fonts["title_sm"].render(display.upper(), True, COLORS["accent_glow"])
        else:
            target = self.sequence[self.current_step] if self.current_step < len(self.sequence) else ""
            status = self.fonts["body"].render(f"NEXT SIGN: {target.upper()}", True, (255, 255, 255))
        
        status_rect = status.get_rect(center=(x + bar_w // 2, y + 22))
        self.screen.blit(status, status_rect)
        
        # Icons
        for i, sign in enumerate(self.sequence):
            ix = start_x + i * (icon_size + gap)
            
            # Center icons vertically if they are smaller than max
            iy = icon_y_start + (80 - icon_size) // 2
            
            # Border
            if i < self.current_step:
                pygame.draw.rect(self.screen, COLORS["success"], (ix - 3, iy - 3, icon_size + 6, icon_size + 6), border_radius=10)
            elif i == self.current_step and not self.jutsu_active:
                pygame.draw.rect(self.screen, COLORS["accent"], (ix - 4, iy - 4, icon_size + 8, icon_size + 8), border_radius=10)
            
            # Icon
            if sign in self.icons:
                icon_surf = self.icons[sign]
                if icon_surf.get_width() != icon_size:
                    icon_surf = pygame.transform.smoothscale(icon_surf, (icon_size, icon_size))
                
                icon = icon_surf.copy()
                if i < self.current_step:
                    icon.set_alpha(100)
                self.screen.blit(icon, (ix, iy))
            else:
                pygame.draw.rect(self.screen, COLORS["border"], (ix, iy, icon_size, icon_size), border_radius=8)
