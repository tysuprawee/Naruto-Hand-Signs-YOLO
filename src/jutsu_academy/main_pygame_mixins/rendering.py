from src.jutsu_academy.main_pygame_shared import *


class RenderingMixin:
    def render_menu(self):
        """Render main menu with cleaner, game-like aesthetic."""
        # 1. Background & Overlay
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(COLORS["bg_dark"])
            
        any_hovered = False
        
        # Subtle gradient overlay for better text contrast
        # Top gradient (darker)
        top_grad = pygame.Surface((SCREEN_WIDTH, 200), pygame.SRCALPHA)
        for y in range(200):
            alpha = int(180 * (1 - y/200))
            pygame.draw.line(top_grad, (0, 0, 0, alpha), (0, y), (SCREEN_WIDTH, y))
        self.screen.blit(top_grad, (0, 0))
        
        # Bottom gradient (darker)
        bot_grad = pygame.Surface((SCREEN_WIDTH, 150), pygame.SRCALPHA)
        for y in range(150):
            alpha = int(200 * (y/150))
            pygame.draw.line(bot_grad, (0, 0, 0, alpha), (0, y), (SCREEN_WIDTH, y))
        self.screen.blit(bot_grad, (0, SCREEN_HEIGHT - 150))
        
        # General darkening
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        self.screen.blit(overlay, (0, 0))
        
        # 2. Hero Section (Logo & Subtitle)
        if self.logo:
            logo_rect = self.logo.get_rect(center=(SCREEN_WIDTH // 2, 160))
            # Subtle shadow for logo
            shadow_surf = pygame.transform.scale(self.logo, (logo_rect.width + 10, logo_rect.height + 10))
            shadow_surf.fill((0, 0, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(shadow_surf, (logo_rect.x - 5, logo_rect.y + 5))
            self.screen.blit(self.logo, logo_rect)
        else:
            title = self.fonts["title_lg"].render("JUTSU ACADEMY", True, COLORS["accent"])
            title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
            self.screen.blit(title, title_rect)
        
        # Subtitle - with shadow effect
        # Shadow
        sub_shadow = self.fonts["body"].render("TRAIN • MASTER • RANK UP", True, (0, 0, 0))
        self.screen.blit(sub_shadow, sub_shadow.get_rect(center=(SCREEN_WIDTH // 2 + 2, 332)))
        # Main text
        subtitle = self.fonts["body"].render("TRAIN • MASTER • RANK UP", True, COLORS["accent_glow"])
        sub_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 330))
        self.screen.blit(subtitle, sub_rect)
        
        # Buttons - update hover status for cursor
        any_button_hovered = False
        for btn in self.menu_buttons.values():
            btn.render(self.screen)
            if btn.hovered:
                any_button_hovered = True
        
        # ─── Social Links with hover effects ───
        social_y = SCREEN_HEIGHT - 70
        social_x_start = SCREEN_WIDTH // 2 - 55
        social_gap = 45
        
        mouse_pos = pygame.mouse.get_pos()
        self.social_rects = {}
        icon_map = {"ig": "instagram", "yt": "youtube", "discord": "discord"}
        
        any_social_hovered = False
        for i, (icon_name, link_key) in enumerate(icon_map.items()):
            x = social_x_start + i * social_gap
            rect = pygame.Rect(x, social_y, 40, 40)
            self.social_rects[link_key] = rect
            
            is_hovered = rect.collidepoint(mouse_pos)
            if is_hovered: any_hovered = True
            
            if icon_name in self.social_icons:
                icon = self.social_icons[icon_name]
                if is_hovered:
                    # Glow/Scale
                    scaled = pygame.transform.smoothscale(icon, (36, 36))
                    self.screen.blit(scaled, (x+2, social_y+2))
                else:
                    icon_sm = pygame.transform.smoothscale(icon, (32, 32))
                    self.screen.blit(icon_sm, (x+4, social_y+4))
            

        
        # 6. Mute Button (Bottom Right)
        self.mute_button_rect = pygame.Rect(SCREEN_WIDTH - 60, SCREEN_HEIGHT - 60, 40, 40)
        mute_hovered = self.mute_button_rect.collidepoint(mouse_pos)
        if mute_hovered: any_hovered = True
        
        # Draw Mute
        # No box, just icon
        if self.is_muted:
            icon_key = "mute"
            color = COLORS["error"]
            sym = "🔇"
        else:
            icon_key = "unmute"
            color = COLORS["text_dim"]
            sym = "🔊"
            
        if self.mute_icons.get(icon_key):
            icon = self.mute_icons[icon_key]
            if mute_hovered:
                # brighter/larger
                scaled = pygame.transform.smoothscale(icon, (36, 36))
                self.screen.blit(scaled, (self.mute_button_rect.x + 2, self.mute_button_rect.y + 2))
            else:
                self.screen.blit(icon, (self.mute_button_rect.x + 4, self.mute_button_rect.y + 4))
        else:
            txt = self.fonts["icon"].render(sym, True, color)
            self.screen.blit(txt, (self.mute_button_rect.x+5, self.mute_button_rect.y+5))
            


        # Version (Bottom Right, above mute)
        version = self.fonts["tiny"].render(f"v{APP_VERSION}", True, (255, 255, 255, 100))
        self.screen.blit(version, (SCREEN_WIDTH - 120, SCREEN_HEIGHT - 35))

        # 4. Profile / Auth Status (Top Left)
        self.profile_rect = pygame.Rect(20, 20, 300, 95) # Larger for XP details
        profile_hovered = self.profile_rect.collidepoint(mouse_pos)
        
        # Draw Profile Container (Subtle Glassmorphism)
        bg_color = (20, 20, 25, 200) if profile_hovered else (20, 20, 25, 140)
        profile_surf = pygame.Surface(self.profile_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(profile_surf, bg_color, profile_surf.get_rect(), border_radius=15)
        pygame.draw.rect(profile_surf, (255, 255, 255, 40), profile_surf.get_rect(), 1, border_radius=15)
        self.screen.blit(profile_surf, self.profile_rect)
        
        # Avatar
        if self.user_avatar:
            self.screen.blit(self.user_avatar, (self.profile_rect.x + 15, self.profile_rect.y + 12))
        else:
            # Guest Icon
            guest_rect = pygame.Rect(self.profile_rect.x + 15, self.profile_rect.y + 12, 40, 40)
            pygame.draw.rect(self.screen, (60, 60, 70), guest_rect, border_radius=10)
            icon = self.fonts["body_sm"].render("?", True, COLORS["text_dim"])
            self.screen.blit(icon, icon.get_rect(center=(self.profile_rect.x + 35, self.profile_rect.y + 32)))

        # Name & Rank Info
        name_str = self.username if self.username else "Guest"
        if len(name_str) > 15: name_str = name_str[:15] + "..."
        name_render = self.fonts["body"].render(name_str, True, COLORS["text"])
        self.screen.blit(name_render, (self.profile_rect.x + 70, self.profile_rect.y + 12))
        
        # Check cloud sync status
        if getattr(self.progression, 'synced', True):
            rank_lv_str = f"{self.progression.rank} • LV.{self.progression.level}"
            rank_lv_render = self.fonts["tiny"].render(rank_lv_str.upper(), True, COLORS["accent_glow"])
            self.screen.blit(rank_lv_render, (self.profile_rect.x + 70, self.profile_rect.y + 36))

            # XP Progress Bar
            bar_w, bar_h = 210, 8
            bar_x, bar_y = self.profile_rect.x + 70, self.profile_rect.y + 60
            
            prev_lv_xp = self.progression.get_xp_for_level(self.progression.level)
            next_lv_xp = self.progression.get_xp_for_level(self.progression.level + 1)
            xp_needed = max(1, next_lv_xp - prev_lv_xp)
            xp_current = self.progression.xp - prev_lv_xp
            progress = max(0, min(1, xp_current / xp_needed))

            # Track
            pygame.draw.rect(self.screen, (40, 40, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            if progress > 0:
                # Filled part
                pygame.draw.rect(self.screen, COLORS["accent"], (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=4)
                # Gloss/Shine
                pygame.draw.rect(self.screen, (255, 255, 255, 40), (bar_x, bar_y, int(bar_w * progress), bar_h // 2), border_radius=4)
        else:
            # Show Syncing Animation
            dots = "." * (int(time.time() * 2) % 4)
            sync_render = self.fonts["tiny"].render(f"SYNCING PROFILE{dots}", True, COLORS["text_dim"])
            self.screen.blit(sync_render, (self.profile_rect.x + 70, self.profile_rect.y + 36))
            
            # Empty Track Placeholder
            bar_w, bar_h = 210, 8
            bar_x, bar_y = self.profile_rect.x + 70, self.profile_rect.y + 60
            pygame.draw.rect(self.screen, (30, 30, 35), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        # XP Label
        if getattr(self.progression, 'synced', True):
            xp_label_str = f"{self.progression.xp} / {next_lv_xp} XP"
            xp_render = self.fonts["tiny"].render(xp_label_str, True, COLORS["text_dim"])
            self.screen.blit(xp_render, (bar_x, bar_y + 12))

        # ─── New: Announcement Overlay Logic ───
        # Auto-show logic
        if not self.show_announcements and self.announcements_fetched and not hasattr(self, "_ann_shown_once"):
            if time.time() - self.announcement_timer_start > self.announcement_auto_show_delay:
                 self.show_announcements = True
                 self._ann_shown_once = True
                 
        if self.show_announcements:
            self.render_announcement_popup()
            status_color = COLORS["text_dim"]
        
        if profile_hovered:
            any_hovered = True

        # Dropdown Menu (if open)
        if self.profile_dropdown_open:
            dd_rect = pygame.Rect(self.profile_rect.x, self.profile_rect.bottom + 5, 200, 50)
            pygame.draw.rect(self.screen, COLORS["bg_card"], dd_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["border"], dd_rect, 1, border_radius=8)
            
            # Logout Option
            logout_txt = self.fonts["body_sm"].render("Log Out", True, COLORS["error"])
            # Hover check for dropdown item
            self.logout_item_rect = pygame.Rect(dd_rect.x, dd_rect.y, dd_rect.width, dd_rect.height)
            if self.logout_item_rect.collidepoint(mouse_pos):
                pygame.draw.rect(self.screen, COLORS["bg_hover"], self.logout_item_rect, border_radius=8)
                any_hovered = True
                
            self.screen.blit(logout_txt, (dd_rect.x + 20, dd_rect.y + 15))
            


        # Cursor update
        if any_button_hovered or any_social_hovered or any_hovered:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    def render_login_modal(self):
        """Render the login requirement modal."""
        # 1. Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200)) # Darker than normal overlay
        self.screen.blit(overlay, (0, 0))
        
        # 2. Modal Box
        modal_w, modal_h = 500, 300
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        # Shadow
        shadow_rect = modal_rect.copy()
        shadow_rect.inflate_ip(4, 4)
        shadow_rect.y += 4
        pygame.draw.rect(self.screen, (0, 0, 0, 100), shadow_rect, border_radius=16)
        
        # Background
        pygame.draw.rect(self.screen, COLORS["bg_panel"], modal_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], modal_rect, 1, border_radius=16)
        
        # 3. Content
        # Title
        title = self.fonts["title_sm"].render("Login Required", True, COLORS["error"])
        title_rect = title.get_rect(center=(modal_x + modal_w//2, modal_y + 50))
        self.screen.blit(title, title_rect)
        
        # Message based on login state
        if self.login_in_progress:
            msg_text = "Waiting for Discord in your browser..."
        elif self.login_error:
            msg_text = f"Login failed: {self.login_error}"
        else:
            msg_text = self.login_modal_message if self.login_modal_message else "Please log in to access this feature."
        
        # Simple word wrap for message
        words = msg_text.split(' ')
        lines = []
        current_line = []
        
        font = self.fonts["body_sm"]
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] < modal_w - 60:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        # Render lines
        start_msg_y = modal_y + 100
        for i, line in enumerate(lines):
            line_surf = font.render(line, True, COLORS["text"])
            line_rect = line_surf.get_rect(center=(modal_x + modal_w//2, start_msg_y + i*25))
            self.screen.blit(line_surf, line_rect)
            
        # 4. Buttons (different based on login state)
        btn_w, btn_h = 180, 50
        btn_y = modal_y + modal_h - 80
        mouse_pos = pygame.mouse.get_pos()
        
        if self.login_in_progress:
            # Show "Reopen Browser" and "Cancel" buttons
            self.modal_login_rect = pygame.Rect(modal_x + 50, btn_y, btn_w, btn_h)
            login_hover = self.modal_login_rect.collidepoint(mouse_pos)
            
            color = (108, 121, 255) if login_hover else (88, 101, 242)
            pygame.draw.rect(self.screen, color, self.modal_login_rect, border_radius=8)
            
            login_txt = self.fonts["body_sm"].render("Reopen Browser", True, (255, 255, 255))
            self.screen.blit(login_txt, login_txt.get_rect(center=self.modal_login_rect.center))
            

            
            # Cancel Button
            self.modal_cancel_rect = pygame.Rect(modal_x + modal_w - 50 - btn_w, btn_y, btn_w, btn_h)
            cancel_hover = self.modal_cancel_rect.collidepoint(mouse_pos)
            
            color = COLORS["error"] if cancel_hover else (120, 40, 40)
            pygame.draw.rect(self.screen, color, self.modal_cancel_rect, border_radius=8)
            
            cancel_txt = self.fonts["body_sm"].render("Cancel Login", True, COLORS["text"])
            self.screen.blit(cancel_txt, cancel_txt.get_rect(center=self.modal_cancel_rect.center))
            

        else:
            # Show "Login with Discord" and "Cancel" buttons
            self.modal_login_rect = pygame.Rect(modal_x + 50, btn_y, btn_w, btn_h)
            login_hover = self.modal_login_rect.collidepoint(mouse_pos)
            
            color = (108, 121, 255) if login_hover else (88, 101, 242)
            pygame.draw.rect(self.screen, color, self.modal_login_rect, border_radius=8)
            
            login_txt = self.fonts["body_sm"].render("Login with Discord", True, (255, 255, 255))
            self.screen.blit(login_txt, login_txt.get_rect(center=self.modal_login_rect.center))
            

            
            # Cancel Button
            self.modal_cancel_rect = pygame.Rect(modal_x + modal_w - 50 - btn_w, btn_y, btn_w, btn_h)
            cancel_hover = self.modal_cancel_rect.collidepoint(mouse_pos)
            
            color = COLORS["bg_hover"] if cancel_hover else COLORS["bg_card"]
            pygame.draw.rect(self.screen, color, self.modal_cancel_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["text_dim"], self.modal_cancel_rect, 1, border_radius=8)
            
            cancel_txt = self.fonts["body_sm"].render("Cancel", True, COLORS["text"])
            self.screen.blit(cancel_txt, cancel_txt.get_rect(center=self.modal_cancel_rect.center))
            

        
        if login_hover or cancel_hover:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

    def render_quit_confirm(self):
        """Render the quit confirmation modal."""
        # 1. Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200)) # Darker than normal overlay
        self.screen.blit(overlay, (0, 0))
        
        # 2. Modal Box
        modal_w, modal_h = 500, 280
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        # Shadow
        shadow_rect = modal_rect.copy()
        shadow_rect.inflate_ip(4, 4)
        shadow_rect.y += 4
        pygame.draw.rect(self.screen, (0, 0, 0, 100), shadow_rect, border_radius=16)
        
        # Background
        pygame.draw.rect(self.screen, COLORS["bg_panel"], modal_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], modal_rect, 1, border_radius=16)
        
        # Title
        title = self.fonts["title_sm"].render("Leaving so soon?", True, COLORS["text"])
        title_rect = title.get_rect(center=(modal_x + modal_w//2, modal_y + 50))
        self.screen.blit(title, title_rect)
        
        # Message
        msg_lines = ["Are you sure you want to quit", "Jutsu Academy?"]
        start_msg_y = modal_y + 100
        for i, line in enumerate(msg_lines):
            line_surf = self.fonts["body_sm"].render(line, True, COLORS["text_dim"])
            line_rect = line_surf.get_rect(center=(modal_x + modal_w//2, start_msg_y + i*30))
            self.screen.blit(line_surf, line_rect)
            
        # Buttons
        btn_w, btn_h = 160, 50
        btn_y = modal_y + modal_h - 80
        mouse_pos = pygame.mouse.get_pos()
        
        # Quit Button (Red)
        self.quit_confirm_rect = pygame.Rect(modal_x + 60, btn_y, btn_w, btn_h)
        quit_hover = self.quit_confirm_rect.collidepoint(mouse_pos)
        
        color = COLORS["error"] if quit_hover else (150, 40, 40)
        pygame.draw.rect(self.screen, color, self.quit_confirm_rect, border_radius=8)
        
        quit_txt = self.fonts["body_sm"].render("Yes, Quit", True, (255, 255, 255))
        self.screen.blit(quit_txt, quit_txt.get_rect(center=self.quit_confirm_rect.center))
        

        
        # Stay Button (Green/Blue/Neutral)
        self.quit_cancel_rect = pygame.Rect(modal_x + modal_w - 60 - btn_w, btn_y, btn_w, btn_h)
        cancel_hover = self.quit_cancel_rect.collidepoint(mouse_pos)
        
        color = COLORS["bg_hover"] if cancel_hover else COLORS["bg_card"]
        pygame.draw.rect(self.screen, color, self.quit_cancel_rect, border_radius=8)
        pygame.draw.rect(self.screen, (100, 100, 100), self.quit_cancel_rect, 1, border_radius=8)
        
        cancel_txt = self.fonts["body_sm"].render("Stay", True, COLORS["text"])
        self.screen.blit(cancel_txt, cancel_txt.get_rect(center=self.quit_cancel_rect.center))
        

        
        if quit_hover or cancel_hover:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

    def render_welcome_modal(self, dt):
        """Render the welcome success modal with premium aesthetics."""
        self.welcome_modal_timer += dt
        
        # 1. Dark overlay with subtle blur-like darkening
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 15, 230)) # Extra dark blue-ish
        self.screen.blit(overlay, (0, 0))
        
        # 2. Modal Dimensions
        modal_w, modal_h = 560, 420
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        # --- Shadow & Outer Glow ---
        for i in range(15, 0, -1):
            alpha = int(25 * (1 - i/15))
            glow_rect = modal_rect.inflate(i*2, i*2)
            pygame.draw.rect(self.screen, (*COLORS["success"], alpha), glow_rect, border_radius=30 + i)

        # 3. Main Glass Content
        modal_bg = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
        # Deep dark gradient-like fill
        pygame.draw.rect(modal_bg, (20, 20, 25, 255), modal_bg.get_rect(), border_radius=25)
        # Subtle top-light
        pygame.draw.rect(modal_bg, (60, 60, 70, 255), modal_bg.get_rect(), 2, border_radius=25)
        self.screen.blit(modal_bg, (modal_x, modal_y))
        
        # --- Avatar Section ---
        center_x = modal_x + modal_w // 2
        avatar_y = modal_y + 90
        
        # Circular Background for Avatar
        pygame.draw.circle(self.screen, (15, 15, 20), (center_x, avatar_y), 65)
        
        # Pulsing ring around avatar
        pulse = (math.sin(self.welcome_modal_timer * 4) + 1) / 2
        ring_size = 65 + int(pulse * 10)
        ring_alpha = int(100 * (1 - pulse))
        if ring_alpha > 0:
            ring_surf = pygame.Surface((ring_size*2, ring_size*2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (*COLORS["success"], ring_alpha), (ring_size, ring_size), ring_size, 3)
            self.screen.blit(ring_surf, (center_x - ring_size, avatar_y - ring_size))

        if self.user_avatar:
            # Scale and blit avatar
            av_size = 110
            scaled_avatar = pygame.transform.smoothscale(self.user_avatar, (av_size, av_size))
            av_rect = scaled_avatar.get_rect(center=(center_x, avatar_y))
            
            # Mask border
            pygame.draw.circle(self.screen, COLORS["success"], (center_x, avatar_y), 60, 3)
            self.screen.blit(scaled_avatar, av_rect)
        else:
             # Default generic icon
             pygame.draw.circle(self.screen, COLORS["bg_card"], (center_x, avatar_y), 55)
             pygame.draw.circle(self.screen, COLORS["success"], (center_x, avatar_y), 58, 2)
        
        # --- Text Content ---
        username = self.username if self.username else "Shinobi"
        title_txt = f"WELCOME, {username.upper()}"
        title_surf = self.fonts["title_md"].render(title_txt, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(center_x, avatar_y + 95))
        
        # Subtle title shadow
        shadow_surf = self.fonts["title_md"].render(title_txt, True, (0, 0, 0))
        self.screen.blit(shadow_surf, (title_rect.x + 2, title_rect.y + 2))
        self.screen.blit(title_surf, title_rect)
        
        # Status Message
        status_txt = "Access Granted. Academy protocols initialized."
        msg_surf = self.fonts["body"].render(status_txt, True, COLORS["text_dim"])
        msg_rect = msg_surf.get_rect(center=(center_x, title_rect.bottom + 25))
        self.screen.blit(msg_surf, msg_rect)
        
        # --- Enter Button ---
        btn_w, btn_h = 280, 65
        btn_x = modal_x + (modal_w - btn_w) // 2
        btn_y = modal_y + modal_h - 100
        self.welcome_ok_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        
        mouse_pos = pygame.mouse.get_pos()
        hover = self.welcome_ok_rect.collidepoint(mouse_pos)
        
        # Button Shadow
        pygame.draw.rect(self.screen, (0, 0, 0, 80), (btn_x + 4, btn_y + 4, btn_w, btn_h), border_radius=15)
        
        # Button Body
        base_color = COLORS["success"] if not hover else COLORS["success"]
        if hover:
            # Brighten slightly on hover
            base_color = tuple(min(255, c + 30) for c in base_color)
            pygame.draw.rect(self.screen, (*COLORS["success"], 100), self.welcome_ok_rect.inflate(8, 8), border_radius=18, width=2)
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

        pygame.draw.rect(self.screen, base_color, self.welcome_ok_rect, border_radius=15)
        
        # Inner gloss/shine for button
        shine_rect = pygame.Rect(btn_x + 5, btn_y + 5, btn_w - 10, btn_h // 2.5)
        pygame.draw.rect(self.screen, (255, 255, 255, 40), shine_rect, border_radius=12)
        
        # Button Text
        btn_txt = self.fonts["title_sm"].render("ENTER ACADEMY", True, (255, 255, 255))
        self.screen.blit(btn_txt, btn_txt.get_rect(center=self.welcome_ok_rect.center))
        
        # Fallback hint
        hint = self.fonts["tiny"].render("Press SPACE to continue", True, (100, 100, 110))
        self.screen.blit(hint, hint.get_rect(center=(center_x, btn_y + btn_h + 25)))

    def render_error_modal(self):
        """Render a generic error modal."""
        # 1. Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))
        
        # 2. Modal Box
        modal_w, modal_h = 550, 300
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        # Shadow
        shadow_rect = modal_rect.copy()
        shadow_rect.inflate_ip(4, 4)
        shadow_rect.y += 4
        pygame.draw.rect(self.screen, (0, 0, 0, 100), shadow_rect, border_radius=16)
        
        # Background
        pygame.draw.rect(self.screen, COLORS["bg_panel"], modal_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["error"], modal_rect, 2, border_radius=16) # Red border for error
        
        # Title
        title_text = getattr(self, "error_title", "Error")
        title = self.fonts["title_sm"].render(title_text, True, COLORS["error"])
        title_rect = title.get_rect(center=(modal_x + modal_w//2, modal_y + 50))
        self.screen.blit(title, title_rect)
        
        # Message (multiline support)
        msg_text = getattr(self, "error_message", "An unexpected error occurred.")
        lines = msg_text.split('\n')
        
        start_msg_y = modal_y + 100
        for i, line in enumerate(lines):
            line_surf = self.fonts["body_sm"].render(line, True, COLORS["text"])
            line_rect = line_surf.get_rect(center=(modal_x + modal_w//2, start_msg_y + i*30))
            self.screen.blit(line_surf, line_rect)
            
        # Back Button
        btn_w, btn_h = 160, 50
        btn_y = modal_y + modal_h - 80
        mouse_pos = pygame.mouse.get_pos()
        
        self.error_ok_rect = pygame.Rect(modal_x + (modal_w - btn_w)//2, btn_y, btn_w, btn_h)
        ok_hover = self.error_ok_rect.collidepoint(mouse_pos)
        
        color = COLORS["bg_hover"] if ok_hover else COLORS["bg_card"]
        pygame.draw.rect(self.screen, color, self.error_ok_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["border"], self.error_ok_rect, 1, border_radius=8)
        
        ok_txt = self.fonts["body_sm"].render("Back to Menu", True, COLORS["text"])
        self.screen.blit(ok_txt, ok_txt.get_rect(center=self.error_ok_rect.center))
        
        if ok_hover:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

    def render_logout_confirm(self):
        """Render the logout confirmation modal."""
        # 1. Dark overlay (darker)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        # 2. Modal Box
        modal_w, modal_h = 500, 280
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        # Shadow
        shadow_rect = modal_rect.copy()
        shadow_rect.inflate_ip(4, 4)
        shadow_rect.y += 4
        pygame.draw.rect(self.screen, (0, 0, 0, 100), shadow_rect, border_radius=16)
        
        # Background
        pygame.draw.rect(self.screen, COLORS["bg_panel"], modal_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], modal_rect, 1, border_radius=16)
        
        # Title
        title = self.fonts["title_sm"].render("Sign Out?", True, COLORS["text"])
        title_rect = title.get_rect(center=(modal_x + modal_w//2, modal_y + 50))
        self.screen.blit(title, title_rect)
        
        # Message
        msg_lines = ["Sign out and close the game?", "Your session will be cleared."]
        start_msg_y = modal_y + 100
        for i, line in enumerate(msg_lines):
            line_surf = self.fonts["body_sm"].render(line, True, COLORS["text_dim"])
            line_rect = line_surf.get_rect(center=(modal_x + modal_w//2, start_msg_y + i*30))
            self.screen.blit(line_surf, line_rect)
            
        # Buttons
        btn_w, btn_h = 160, 50
        btn_y = modal_y + modal_h - 80
        mouse_pos = pygame.mouse.get_pos()
        
        # Logout Button (Red)
        self.logout_confirm_rect = pygame.Rect(modal_x + 60, btn_y, btn_w, btn_h)
        logout_hover = self.logout_confirm_rect.collidepoint(mouse_pos)
        
        color = COLORS["error"] if logout_hover else (150, 40, 40)
        pygame.draw.rect(self.screen, color, self.logout_confirm_rect, border_radius=8)
        
        logout_txt = self.fonts["body_sm"].render("Sign Out", True, (255, 255, 255))
        self.screen.blit(logout_txt, logout_txt.get_rect(center=self.logout_confirm_rect.center))
        

        
        # Cancel Button
        self.logout_cancel_rect = pygame.Rect(modal_x + modal_w - 60 - btn_w, btn_y, btn_w, btn_h)
        cancel_hover = self.logout_cancel_rect.collidepoint(mouse_pos)
        
        color = COLORS["bg_hover"] if cancel_hover else COLORS["bg_card"]
        pygame.draw.rect(self.screen, color, self.logout_cancel_rect, border_radius=8)
        pygame.draw.rect(self.screen, (100, 100, 100), self.logout_cancel_rect, 1, border_radius=8)
        
        cancel_txt = self.fonts["body_sm"].render("Cancel", True, COLORS["text"])
        self.screen.blit(cancel_txt, cancel_txt.get_rect(center=self.logout_cancel_rect.center))
        

        
        if logout_hover or cancel_hover:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

    def render_connection_lost(self):
        """Render the connection lost modal."""
        # 1. Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))
        
        # 2. Modal Box
        modal_w, modal_h = 500, 280
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        
        # Background
        pygame.draw.rect(self.screen, COLORS["bg_panel"], modal_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["error"], modal_rect, 2, border_radius=16)
        
        # Icon/Title
        title = self.fonts["title_sm"].render("Connection Lost", True, COLORS["error"])
        title_rect = title.get_rect(center=(modal_x + modal_w//2, modal_y + 50))
        self.screen.blit(title, title_rect)
        
        # Message
        msg_lines = ["Network connection interrupted.", "Session has been terminated."]
        start_msg_y = modal_y + 100
        for i, line in enumerate(msg_lines):
            line_surf = self.fonts["body_sm"].render(line, True, COLORS["text"])
            line_rect = line_surf.get_rect(center=(modal_x + modal_w//2, start_msg_y + i*30))
            self.screen.blit(line_surf, line_rect)
            
        # Exit Button
        btn_w, btn_h = 160, 50
        btn_y = modal_y + modal_h - 80
        mouse_pos = pygame.mouse.get_pos()
        
        self.conn_lost_exit_rect = pygame.Rect(modal_x + (modal_w - btn_w)//2, btn_y, btn_w, btn_h)
        exit_hover = self.conn_lost_exit_rect.collidepoint(mouse_pos)
        
        color = COLORS["error"] if exit_hover else (150, 40, 40)
        pygame.draw.rect(self.screen, color, self.conn_lost_exit_rect, border_radius=8)
        
        exit_txt = self.fonts["body_sm"].render("Exit Game", True, (255, 255, 255))
        self.screen.blit(exit_txt, exit_txt.get_rect(center=self.conn_lost_exit_rect.center))
        
        if exit_hover:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

    def render_settings(self):
        """Render settings menu."""
        self.screen.fill(COLORS["bg_dark"])
        
        # Title
        title = self.fonts["title_md"].render("SETTINGS", True, COLORS["text"])
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 80))
        self.screen.blit(title, title_rect)
        
        # Panel
        panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, 150, 400, 390)
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel_rect, border_radius=16)
        
        # Sliders
        for slider in self.settings_sliders.values():
            slider.render(self.screen)
        
        # Camera dropdown
        cam_label = self.fonts["body_sm"].render("Camera:", True, COLORS["text"])
        self.screen.blit(cam_label, (SCREEN_WIDTH // 2 - 150, 395))
        self.camera_dropdown.render(self.screen)
        
        # Checkboxes
        for cb in self.settings_checkboxes.values():
            cb.render(self.screen)
            
        # Buttons
        for btn in self.settings_buttons.values():
            btn.render(self.screen)

    def render_practice_select(self):
        """Render practice mode selection with enhanced styling."""
        # 1. Background Logic
        if self.bg_image:
             bg = pygame.transform.smoothscale(self.bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
             self.screen.blit(bg, (0, 0))
        else:
             self.screen.fill(COLORS["bg_dark"])
             
        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        # 2. Main Panel
        panel_w, panel_h = 560, 650
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel_rect, border_radius=20)
        pygame.draw.rect(self.screen, COLORS["border"], panel_rect, 2, border_radius=20)
        
        # Title
        title = self.fonts["title_md"].render("SELECT MODE", True, COLORS["accent"])
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, panel_y + 60))
        self.screen.blit(title, title_rect)
        
        descriptions = {
            "freeplay": "Practice any jutsu at your own pace",
            "challenge": "Complete jutsus as fast as possible",
            "multiplayer": "PvP Battles (Coming Soon)",
            "leaderboard": "View the rankings of the greatest Shinobi"
        }
        
        for name, btn in self.practice_buttons.items():
            btn.render(self.screen)
            if name in descriptions:
                # Use small font to fit
                desc = self.fonts["small"].render(descriptions[name], True, (180, 180, 190))
                desc_rect = desc.get_rect(midtop=(btn.rect.centerx, btn.rect.bottom + 5))
                self.screen.blit(desc, desc_rect)

    def render_about(self):
        """Render about/specs page."""
        self.screen.fill(COLORS["bg_dark"])
        
        # Title
        title = self.fonts["title_md"].render("ABOUT JUTSU ACADEMY", True, COLORS["accent"])
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        # Panel Dimensions
        panel_w, panel_h = 600, 500
        panel_x = SCREEN_WIDTH // 2 - 300
        panel_y = 100
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Draw Panel Background
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel_rect, border_radius=16)
        
        # Create Content Surface
        content_h = 1500 # Increased height for legal text
        content_surf = pygame.Surface((panel_w, content_h), pygame.SRCALPHA)
        
        c_y = 20 # Start Y on content surface
        margin_x = 40
        
        # --- Content ---
        
        # Minimum Reqs
        header = self.fonts["title_sm"].render("MINIMUM REQUIREMENTS", True, COLORS["success"])
        content_surf.blit(header, (margin_x, c_y))
        c_y += 40
        
        min_reqs = [
            "- GPU: NVIDIA GTX 1050 or equivalent",
            "- CPU: Intel Core i5 8th Gen / Ryzen 5 2600",
            "- RAM: 8GB",
            "- Camera: 720p 30fps Webcam",
        ]
        
        for req in min_reqs:
            text = self.fonts["body_sm"].render(req, True, COLORS["text"])
            content_surf.blit(text, (margin_x, c_y))
            c_y += 30
        
        c_y += 20
        
        # Recommended Reqs
        header = self.fonts["title_sm"].render("RECOMMENDED", True, COLORS["accent"])
        content_surf.blit(header, (margin_x, c_y))
        c_y += 40
        
        rec_reqs = [
            "- GPU: RTX 2060 or better (for smooth tracking)",
            "- CPU: i7 10th Gen / Ryzen 7 3700X",
            "- RAM: 16GB",
            "- Camera: 1080p 60fps Webcam",
        ]
        
        for req in rec_reqs:
            text = self.fonts["body_sm"].render(req, True, COLORS["text"])
            content_surf.blit(text, (margin_x, c_y))
            c_y += 30
            
        c_y += 30
        
        # Divider Line
        pygame.draw.line(content_surf, COLORS["border"], (margin_x, c_y), (panel_w - margin_x, c_y), 2)
        c_y += 30
        
        # Developer Info
        dev_info = self.fonts["title_sm"].render("DEVELOPER", True, COLORS["text"])
        content_surf.blit(dev_info, (margin_x, c_y))
        c_y += 40
        
        dev_details = [
            "Created by: James Uzumaki",
            "Built with: Python, YOLO, MediaPipe, Pygame",
            f"Version: {APP_VERSION} - Pygame Edition",
        ]
        
        for detail in dev_details:
            text = self.fonts["body_sm"].render(detail, True, COLORS["text_dim"])
            content_surf.blit(text, (margin_x, c_y))
            c_y += 28

        c_y += 40

        # Legal Disclaimer
        disclaimer_header = self.fonts["title_sm"].render("LEGAL DISCLAIMER", True, COLORS["error"])
        content_surf.blit(disclaimer_header, (margin_x, c_y))
        c_y += 40
        
        disclaimer_lines = [
            "This is a non-profit fan-made project.",
            "Naruto and all related characters, names, and",
            "indices are trademarks of Masashi Kishimoto,",
            "Shueisha, TV Tokyo, and Viz Media.",
            "This project is not affiliated with or endorsed",
            "by the official rights holders.",
            "Intended for educational & portfolio purposes only.",
        ]
        
        for line in disclaimer_lines:
            text = self.fonts["body_sm"].render(line, True, COLORS["text"])
            content_surf.blit(text, (margin_x, c_y))
            c_y += 30

        c_y += 30

        # Privacy & Terms
        pt_header = self.fonts["title_sm"].render("TERMS & PRIVACY", True, COLORS["text"])
        content_surf.blit(pt_header, (margin_x, c_y))
        c_y += 40
        
        pt_lines = [
            "Privacy Policy:",
            "Camera data is processed LOCALLY on your device.",
            "No images or video are sent to any server.",
            "We do not collect personal data. Only a local",
            "session file is stored for Discord login.",
            "",
            "Terms of Service:",
            "By using this software, you agree that you",
            "understand this is a fan project provided 'as-is'.",
        ]
        
        for line in pt_lines:
            text = self.fonts["body_sm"].render(line, True, COLORS["text_dim"])
            content_surf.blit(text, (margin_x, c_y))
            c_y += 30

        # --- Blit visible portion ---
        
        # Limit scroll
        max_scroll = max(0, c_y - panel_h + 20)
        if self.about_scroll_y > max_scroll:
            self.about_scroll_y = max_scroll
            
        # Define visible area from content surface
        area = pygame.Rect(0, self.about_scroll_y, panel_w, panel_h)
        
        # Blit to screen
        self.screen.blit(content_surf, (panel_x, panel_y), area)
        
        # Draw Scrollbar (if needed)
        if max_scroll > 0:
            bar_w = 6
            bar_h = panel_h * (panel_h / content_h)
            bar_x = panel_x + panel_w - 12
            
            # Use safe division for track position
            scroll_ratio = self.about_scroll_y / max_scroll if max_scroll > 0 else 0
            track_len = panel_h - bar_h - 20
            bar_y = panel_y + 10 + (track_len * scroll_ratio)
            
            pygame.draw.rect(self.screen, (100, 100, 100), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        
        # Border overlay (to cover any edge aliasing)
        pygame.draw.rect(self.screen, COLORS["border"], panel_rect, 2, border_radius=16)
        
        # Back button
        for btn in self.about_buttons.values():
            btn.render(self.screen)
