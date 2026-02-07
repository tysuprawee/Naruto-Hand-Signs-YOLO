from src.jutsu_academy.main_pygame_shared import *
import datetime


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
        
        # Main Panel
        panel_rect = pygame.Rect(70, 130, SCREEN_WIDTH - 140, SCREEN_HEIGHT - 190)
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], panel_rect, 2, border_radius=16)

        # Split sections
        left_rect = pygame.Rect(panel_rect.x + 16, panel_rect.y + 16, 470, panel_rect.height - 32)
        right_rect = pygame.Rect(left_rect.right + 16, panel_rect.y + 16, panel_rect.right - (left_rect.right + 32), panel_rect.height - 32)

        pygame.draw.rect(self.screen, (30, 30, 40), left_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["border"], left_rect, 1, border_radius=12)
        pygame.draw.rect(self.screen, (26, 26, 34), right_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["border"], right_rect, 1, border_radius=12)

        controls_title = self.fonts["body"].render("AUDIO • CAMERA • INPUT", True, COLORS["accent"])
        self.screen.blit(controls_title, (left_rect.x + 16, left_rect.y + 12))

        # Robust control layout anchored to panel (avoids overlap on future size tweaks)
        controls_cx = left_rect.x + left_rect.width // 2
        controls_top = left_rect.y + 46
        self.settings_sliders["music"].x = controls_cx - 150
        self.settings_sliders["music"].y = controls_top + 16
        self.settings_sliders["sfx"].x = controls_cx - 150
        self.settings_sliders["sfx"].y = controls_top + 96

        self.camera_dropdown.x = controls_cx - 115
        self.camera_dropdown.y = controls_top + 186
        self.camera_dropdown.width = min(280, left_rect.width - 44)
        self.camera_dropdown.rect = pygame.Rect(
            self.camera_dropdown.x,
            self.camera_dropdown.y,
            self.camera_dropdown.width,
            self.camera_dropdown.height,
        )

        cb_y = controls_top + 266
        for key in ["debug_hands", "use_mp", "restricted"]:
            cb = self.settings_checkboxes[key]
            cb.rect.x = controls_cx - 150
            cb.rect.y = cb_y
            cb_y += 40

        scan_btn = self.settings_buttons["scan_cameras"]
        scan_btn.rect.width = 120
        scan_btn.rect.height = 32
        scan_btn.rect.x = self.camera_dropdown.rect.right - scan_btn.rect.width
        scan_btn.rect.y = self.camera_dropdown.rect.y + self.camera_dropdown.rect.height + 8
        scan_btn.text = "SCAN"
        scan_btn.color = COLORS["bg_card"]

        back_btn = self.settings_buttons["back"]
        back_btn.rect.width = min(250, left_rect.width - 80)
        back_btn.rect.x = controls_cx - back_btn.rect.width // 2
        back_btn.rect.y = left_rect.bottom - 72

        # Sliders
        for slider in self.settings_sliders.values():
            slider.render(self.screen)
        
        # Camera dropdown label
        cam_label = self.fonts["body_sm"].render("Camera:", True, COLORS["text"])
        self.screen.blit(cam_label, (left_rect.x + 16, self.camera_dropdown.y + 6))
        if len(self.cameras) == 0:
            no_cam = self.fonts["tiny"].render("No camera cached yet (enable preview to detect)", True, COLORS["error"])
            self.screen.blit(no_cam, (left_rect.x + 140, self.camera_dropdown.y + 12))
        
        # Checkboxes
        for cb in self.settings_checkboxes.values():
            cb.render(self.screen)
            
        # Camera preview pane
        preview_title = self.fonts["body"].render("CAMERA PREVIEW", True, COLORS["accent"])
        self.screen.blit(preview_title, (right_rect.x + 14, right_rect.y + 12))

        preview_rect = pygame.Rect(right_rect.x + 14, right_rect.y + 50, right_rect.width - 28, right_rect.height - 100)
        pygame.draw.rect(self.screen, (12, 12, 16), preview_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["border"], preview_rect, 1, border_radius=10)

        preview_btn = self.settings_buttons["preview_toggle"]
        preview_btn.rect.width = min(220, preview_rect.width - 40)
        preview_btn.rect.height = 42
        preview_btn.rect.x = preview_rect.centerx - preview_btn.rect.width // 2
        preview_btn.rect.y = preview_rect.bottom - preview_btn.rect.height - 14
        if self.settings_preview_enabled:
            preview_btn.text = "DISABLE PREVIEW"
            preview_btn.color = COLORS["error"]
        else:
            preview_btn.text = "ENABLE PREVIEW"
            preview_btn.color = COLORS["bg_card"]

        preview_surface = self._get_settings_preview_surface()
        if self.settings_preview_enabled and preview_surface is not None:
            sw, sh = preview_surface.get_size()
            fit_scale = min(preview_rect.width / max(1, sw), preview_rect.height / max(1, sh))
            fit_w = max(1, int(sw * fit_scale))
            fit_h = max(1, int(sh * fit_scale))
            fitted = pygame.transform.smoothscale(preview_surface, (fit_w, fit_h))
            dx = preview_rect.x + (preview_rect.width - fit_w) // 2
            dy = preview_rect.y + (preview_rect.height - fit_h) // 2
            prev_clip = self.screen.get_clip()
            self.screen.set_clip(preview_rect)
            self.screen.blit(fitted, (dx, dy))
            self.screen.set_clip(prev_clip)
        else:
            status = "Preview off (click ENABLE PREVIEW)" if not self.settings_preview_enabled else "Preview unavailable"
            no_cam = self.fonts["body_sm"].render(status, True, COLORS["text_dim"])
            self.screen.blit(no_cam, no_cam.get_rect(center=(preview_rect.centerx, preview_rect.centery - 24)))

        hint = self.fonts["tiny"].render("Camera opens only in Settings preview and in active game.", True, COLORS["text_muted"])
        self.screen.blit(hint, (right_rect.x + 14, right_rect.bottom - 24))

        # Buttons
        for btn in self.settings_buttons.values():
            btn.render(self.screen)

        # Render dropdown last so its options are always in front
        self.camera_dropdown.render(self.screen)

    def render_practice_select(self):
        """Render practice mode selection in grouped 'Select Your Path' style."""
        if self.bg_image:
             bg = pygame.transform.smoothscale(self.bg_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
             self.screen.blit(bg, (0, 0))
        else:
             self.screen.fill(COLORS["bg_dark"])
             
        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        panel_w, panel_h = 740, 680
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel_rect, border_radius=22)
        pygame.draw.rect(self.screen, COLORS["border"], panel_rect, 2, border_radius=22)

        title = self.fonts["title_md"].render("SELECT YOUR PATH", True, COLORS["accent"])
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, panel_y + 52)))
        sub = self.fonts["body"].render("Choose how you want to train today.", True, COLORS["text"])
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, panel_y + 96)))

        mouse_pos = pygame.mouse.get_pos()

        # Fixed bottom button
        back_btn = self.practice_buttons["back"]
        back_btn.rect.width = 280
        back_btn.rect.height = 52
        back_btn.rect.x = panel_x + (panel_w - back_btn.rect.width) // 2
        back_btn.rect.y = panel_rect.bottom - 62
        back_btn.text = "BACK TO VILLAGE"

        # Scrollable viewport for cards/sections
        content_area = pygame.Rect(panel_x + 16, panel_y + 122, panel_w - 32, back_btn.rect.y - (panel_y + 122) - 10)

        def draw_section_header(text, local_y):
            y = content_area.y + local_y - self.practice_scroll_y
            bar = pygame.Rect(panel_x + 20, y, panel_w - 40, 28)
            pygame.draw.rect(self.screen, (52, 44, 36, 210), bar, border_radius=10)
            pygame.draw.rect(self.screen, COLORS["border"], bar, 1, border_radius=10)
            t = self.fonts["body"].render(text, True, (228, 192, 150))
            self.screen.blit(t, t.get_rect(center=bar.center))

        def draw_mode_card(name, title_text, desc_text, base_color, local_y, h=74):
            btn = self.practice_buttons[name]
            btn.rect = pygame.Rect(content_area.x + 27, content_area.y + local_y - self.practice_scroll_y, content_area.width - 54, h)
            hovered = btn.rect.collidepoint(mouse_pos) and btn.enabled
            card = pygame.Surface((btn.rect.width, btn.rect.height), pygame.SRCALPHA)
            card.fill((0, 0, 0, 0))
            pygame.draw.rect(card, base_color, card.get_rect(), border_radius=14)
            border = COLORS["accent_glow"] if hovered else (30, 25, 20)
            pygame.draw.rect(card, border, card.get_rect(), 2, border_radius=14)
            gloss = pygame.Surface((btn.rect.width, max(1, btn.rect.height // 2)), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 18 if hovered else 10))
            card.blit(gloss, (0, 0))
            self.screen.blit(card, btn.rect.topleft)

            name_col = (245, 225, 185) if btn.enabled else (170, 170, 180)
            desc_col = COLORS["text"] if btn.enabled else COLORS["text_dim"]
            n = self.fonts["title_sm"].render(title_text, True, name_col)
            d = self.fonts["body"].render(desc_text, True, desc_col)
            self.screen.blit(n, (btn.rect.x + 18, btn.rect.y + 6))
            self.screen.blit(d, (btn.rect.x + 18, btn.rect.y + 40))

            arrow = self.fonts["title_sm"].render(">", True, name_col)
            self.screen.blit(arrow, arrow.get_rect(center=(btn.rect.right - 22, btn.rect.centery)))

        # Content layout in local coordinates (inside scroll area)
        y0 = 0

        # Clamp scroll range
        content_total_h = y0 + 532 + 66 + 18
        max_scroll = max(0, content_total_h - content_area.height)
        if self.practice_scroll_y > max_scroll:
            self.practice_scroll_y = max_scroll
        if self.practice_scroll_y < 0:
            self.practice_scroll_y = 0

        soon = self.fonts["body_sm"].render("Coming Soon...", True, COLORS["text_dim"])

        # Clip cards to scroll area
        pygame.draw.rect(self.screen, COLORS["border"], content_area, 1, border_radius=8)
        prev_clip = self.screen.get_clip()
        self.screen.set_clip(content_area)
        # redraw within clip (simple second pass for clean clipping)
        draw_section_header("MAIN MODES", y0)
        draw_mode_card("freeplay", "FREE PLAY", "Practice any jutsu at your own pace", (140, 64, 28, 235), y0 + 34)
        draw_mode_card("challenge", "CHALLENGE", "Beat the clock and chain combos", (145, 58, 22, 235), y0 + 120)
        draw_section_header("LIBRARY & PROGRESSION", y0 + 206)
        draw_mode_card("library", "JUTSU LIBRARY", "View signs, unlocks, and tutorials", (44, 70, 112, 235), y0 + 240)
        draw_mode_card("quests", "QUEST BOARD", "Daily & weekly missions for bonus XP", (70, 86, 48, 235), y0 + 326)
        draw_mode_card("leaderboard", "LEADERBOARD", "View the rankings of the greatest Shinobi", (130, 100, 24, 235), y0 + 412)
        draw_section_header("COMING SOON", y0 + 498)
        draw_mode_card("multiplayer", "MULTIPLAYER (PVP BATTLES)", "Train hard. Arena opens soon...", (64, 66, 84, 220), y0 + 532, h=66)
        mp = self.practice_buttons["multiplayer"].rect
        self.screen.blit(soon, (mp.right - soon.get_width() - 18, mp.y + 24))
        self.screen.set_clip(prev_clip)

        # Scrollbar
        if max_scroll > 0:
            track = pygame.Rect(content_area.right - 8, content_area.y + 8, 5, content_area.height - 16)
            pygame.draw.rect(self.screen, (60, 60, 75), track, border_radius=3)
            thumb_h = max(30, int(track.height * (content_area.height / max(1, content_total_h))))
            thumb_y = track.y + int((track.height - thumb_h) * (self.practice_scroll_y / max_scroll))
            pygame.draw.rect(self.screen, (170, 170, 190), (track.x, thumb_y, track.width, thumb_h), border_radius=3)

        # Render interactive buttons last for proper hover/press behavior visuals
        self.practice_buttons["back"].render(self.screen)

    def render_about(self):
        """Render upgraded About page."""
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(COLORS["bg_dark"])

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title = self.fonts["title_md"].render("ABOUT JUTSU ACADEMY", True, COLORS["accent"])
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 58)))

        subtitle = self.fonts["body_sm"].render(
            "Project details, controls, privacy, and roadmap",
            True,
            COLORS["text_dim"],
        )
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        panel_margin_x = 90
        panel_w = SCREEN_WIDTH - panel_margin_x * 2
        panel_h = SCREEN_HEIGHT - 240
        panel_x = panel_margin_x
        panel_y = 120
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], panel_rect, 2, border_radius=16)

        content_h = max(1800, panel_h + 500)
        content_surf = pygame.Surface((panel_w, content_h), pygame.SRCALPHA)
        c_y = 20
        margin_x = 28
        section_w = panel_w - (margin_x * 2) - 10

        def wrap_text(text, font, max_width):
            words = text.split()
            if not words:
                return [""]
            lines = []
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            return lines

        def draw_section(title_text, lines, title_color=COLORS["accent"], body_color=COLORS["text_dim"]):
            nonlocal c_y
            title_font = self.fonts["title_sm"]
            body_font = self.fonts["body_sm"]
            line_h = 28

            wrapped_lines = []
            for line in lines:
                if line == "":
                    wrapped_lines.append("")
                    continue
                wrapped_lines.extend(wrap_text(line, body_font, section_w - 24))

            section_h = 20 + title_font.get_height() + 12 + len(wrapped_lines) * line_h + 16
            card_rect = pygame.Rect(margin_x, c_y, section_w, section_h)
            pygame.draw.rect(content_surf, (24, 24, 34, 230), card_rect, border_radius=12)
            pygame.draw.rect(content_surf, COLORS["border"], card_rect, 1, border_radius=12)

            t_surf = title_font.render(title_text, True, title_color)
            content_surf.blit(t_surf, (card_rect.x + 14, card_rect.y + 12))

            line_y = card_rect.y + 12 + title_font.get_height() + 8
            for line in wrapped_lines:
                if line == "":
                    line_y += line_h // 2
                    continue
                b_surf = body_font.render(line, True, body_color)
                content_surf.blit(b_surf, (card_rect.x + 14, line_y))
                line_y += line_h

            c_y = card_rect.bottom + 14

        draw_section(
            "OVERVIEW",
            [
                "Jutsu Academy is a Naruto-inspired hand-sign training game where players perform sign sequences in front of a camera to execute jutsu.",
                "The game focuses on timing, recognition accuracy, progression unlocks, and fast iteration between free practice and challenge runs.",
            ],
            title_color=COLORS["success"],
            body_color=COLORS["text"],
        )

        draw_section(
            "MODES",
            [
                "- Free Play: pick any unlocked jutsu and practice at your pace.",
                "- Challenge: pick an unlocked jutsu and clear the full sequence as fast as possible.",
                "- Jutsu Library: browse tiers, lock requirements, and progression status.",
                "- Leaderboard: compare challenge times against other players.",
            ],
        )

        draw_section(
            "CONTROLS",
            [
                "- Menu navigation: mouse + left click",
                "- Playing: LEFT / RIGHT arrows switch jutsu when allowed",
                "- Challenge: SPACE starts countdown and restarts after results",
                "- Exit current run: ESC or the in-game < BACK button",
                "- Settings: preview camera only when manually enabled",
            ],
            title_color=COLORS["accent_glow"],
        )

        draw_section(
            "PRIVACY & DATA",
            [
                "Camera frames are processed locally during gameplay and Settings preview.",
                "No raw camera frames are uploaded by the game client.",
                "If Discord login is used, session data is stored locally for authentication continuity.",
                "Online features (leaderboard/profile/announcements) only send gameplay/profile data needed for those systems.",
            ],
        )

        draw_section(
            "TECH STACK",
            [
                f"- Client: Python + Pygame (version {APP_VERSION})",
                "- Vision: MediaPipe + optional YOLO-based paths",
                "- Effects: modular orchestrator with jutsu effect systems",
                "- Backend integration: Supabase-powered online services",
            ],
            title_color=COLORS["success"],
        )

        draw_section(
            "ROADMAP",
            [
                "- Expand jutsu roster and progression tiers",
                "- Improve onboarding/tutorial for new players",
                "- Add deeper challenge analytics and timing breakdowns",
                "- Continue hardening camera/device handling UX",
            ],
            title_color=COLORS["accent"],
        )

        draw_section(
            "LEGAL NOTICE",
            [
                "This is a non-profit fan-made project for educational and portfolio use.",
                "Naruto and related names/characters are property of their respective rights holders.",
                "This project is not affiliated with or endorsed by official rights holders.",
            ],
            title_color=COLORS["error"],
            body_color=COLORS["text"],
        )

        max_scroll = max(0, c_y - panel_h + 10)
        if self.about_scroll_y > max_scroll:
            self.about_scroll_y = max_scroll
        if self.about_scroll_y < 0:
            self.about_scroll_y = 0

        area = pygame.Rect(0, self.about_scroll_y, panel_w, panel_h)
        self.screen.blit(content_surf, (panel_x, panel_y), area)

        # Top panel UI (draw after content so it never gets hidden behind scrolling cards)
        badge = pygame.Rect(panel_rect.right - 190, panel_rect.y + 12, 170, 30)
        pygame.draw.rect(self.screen, (26, 26, 36), badge, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["border"], badge, 1, border_radius=10)
        vtxt = self.fonts["small"].render(f"PYGAME v{APP_VERSION}", True, COLORS["accent"])
        self.screen.blit(vtxt, vtxt.get_rect(center=badge.center))

        hint = self.fonts["tiny"].render("Use mouse wheel to scroll", True, COLORS["text_muted"])
        self.screen.blit(hint, (panel_rect.x + 16, panel_rect.y + 14))

        if max_scroll > 0:
            track_rect = pygame.Rect(panel_x + panel_w - 12, panel_y + 10, 6, panel_h - 20)
            pygame.draw.rect(self.screen, (45, 45, 55), track_rect, border_radius=3)
            thumb_h = max(36, int((panel_h / max(1, c_y)) * track_rect.height))
            thumb_h = min(thumb_h, track_rect.height)
            thumb_y = track_rect.y + int((track_rect.height - thumb_h) * (self.about_scroll_y / max_scroll))
            pygame.draw.rect(self.screen, (130, 130, 145), (track_rect.x, thumb_y, track_rect.width, thumb_h), border_radius=3)

        pygame.draw.rect(self.screen, COLORS["border"], panel_rect, 2, border_radius=16)

        back_btn = self.about_buttons["back"]
        back_btn.rect.width = 220
        back_btn.rect.height = 50
        back_btn.rect.x = SCREEN_WIDTH // 2 - back_btn.rect.width // 2
        back_btn.rect.y = min(SCREEN_HEIGHT - back_btn.rect.height - 16, panel_rect.bottom + 14)

        for btn in self.about_buttons.values():
            btn.render(self.screen)

    def render_tutorial(self):
        """Render first-time onboarding/tutorial."""
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(COLORS["bg_dark"])

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        step_idx = max(0, min(getattr(self, "tutorial_step_index", 0), len(self.tutorial_steps) - 1))
        step = self.tutorial_steps[step_idx]

        title = self.fonts["title_md"].render("ACADEMY TUTORIAL", True, COLORS["accent"])
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 72)))

        panel = pygame.Rect(140, 120, SCREEN_WIDTH - 280, SCREEN_HEIGHT - 260)
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], panel, 2, border_radius=16)

        progress_text = self.fonts["body_sm"].render(f"STEP {step_idx + 1} / {len(self.tutorial_steps)}", True, COLORS["text_dim"])
        self.screen.blit(progress_text, (panel.x + 20, panel.y + 16))

        step_title = self.fonts["title_sm"].render(step["title"], True, COLORS["success"])
        self.screen.blit(step_title, (panel.x + 20, panel.y + 46))

        icon = self.tutorial_icons.get(step.get("icon_key", "camera"))
        if icon:
            self.screen.blit(icon, (panel.right - 120, panel.y + 26))

        text_y = panel.y + 106
        for line in step["lines"]:
            line_s = self.fonts["body"].render(line, True, COLORS["text"])
            self.screen.blit(line_s, (panel.x + 24, text_y))
            text_y += 36

        back_btn = self.tutorial_buttons["back"]
        next_btn = self.tutorial_buttons["next"]
        skip_btn = self.tutorial_buttons["skip"]
        back_btn.enabled = step_idx > 0
        next_btn.text = "FINISH" if step_idx == len(self.tutorial_steps) - 1 else "NEXT"

        for b in self.tutorial_buttons.values():
            b.render(self.screen)

    def render_quests(self):
        """Render daily/weekly quest board."""
        self.quest_claim_rects = []
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(COLORS["bg_dark"])

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title = self.fonts["title_md"].render("QUEST BOARD", True, COLORS["accent"])
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 64)))

        panel = pygame.Rect(84, 106, SCREEN_WIDTH - 168, SCREEN_HEIGHT - 190)
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], panel, 2, border_radius=16)

        daily_icon = self.quest_icons.get("daily")
        weekly_icon = self.quest_icons.get("weekly")
        if daily_icon:
            self.screen.blit(daily_icon, (panel.x + 20, panel.y + 14))
        if weekly_icon:
            self.screen.blit(weekly_icon, (panel.centerx + 20, panel.y + 14))

        d_title = self.fonts["body"].render("DAILY", True, COLORS["success"])
        w_title = self.fonts["body"].render("WEEKLY", True, COLORS["accent_glow"])
        self.screen.blit(d_title, (panel.x + 76, panel.y + 22))
        self.screen.blit(w_title, (panel.centerx + 76, panel.y + 22))

        now = datetime.datetime.now()
        tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        weekly_next = now + datetime.timedelta(days=(7 - now.weekday()))
        weekly_next = weekly_next.replace(hour=0, minute=0, second=0, microsecond=0)

        daily_left = str(tomorrow - now).split(".")[0]
        weekly_left = str(weekly_next - now).split(".")[0]
        self.screen.blit(self.fonts["tiny"].render(f"Resets in {daily_left}", True, COLORS["text_dim"]), (panel.x + 76, panel.y + 50))
        self.screen.blit(self.fonts["tiny"].render(f"Resets in {weekly_left}", True, COLORS["text_dim"]), (panel.centerx + 76, panel.y + 50))

        defs = self._quest_definitions()
        card_w = (panel.width - 52) // 2
        card_h = 78
        start_y = panel.y + 88

        for i, (scope, qid, label, target, reward) in enumerate(defs):
            col = 0 if scope == "daily" else 1
            row = i % 3
            x = panel.x + 18 + col * (card_w + 16)
            y = start_y + row * (card_h + 16)
            rect = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(self.screen, (24, 24, 34, 230), rect, border_radius=12)
            pygame.draw.rect(self.screen, COLORS["border"], rect, 1, border_radius=12)

            q = self.quest_state.get(scope, {}).get("quests", {}).get(qid, {"progress": 0, "claimed": False})
            progress = int(q.get("progress", 0))
            claimed = bool(q.get("claimed", False))
            pct = max(0.0, min(1.0, progress / max(1, target)))

            label_s = self.fonts["body_sm"].render(label, True, COLORS["text"])
            self.screen.blit(label_s, (rect.x + 12, rect.y + 10))

            stat_s = self.fonts["tiny"].render(f"{min(progress, target)}/{target}", True, COLORS["text_dim"])
            self.screen.blit(stat_s, (rect.right - 62, rect.y + 14))

            claim_rect = pygame.Rect(rect.right - 108, rect.y + 36, 92, 30)
            reward_x = claim_rect.x - 66
            track = pygame.Rect(rect.x + 12, rect.y + 42, reward_x - (rect.x + 12) - 8, 16)
            pygame.draw.rect(self.screen, (50, 50, 64), track, border_radius=8)
            if pct > 0:
                fill = pygame.Rect(track.x, track.y, int(track.width * pct), track.height)
                pygame.draw.rect(self.screen, COLORS["accent"], fill, border_radius=8)

            reward_txt = self.fonts["tiny"].render(f"+{reward} XP", True, COLORS["accent_glow"])
            self.screen.blit(reward_txt, (reward_x, track.y + 1))

            ready = (progress >= target) and (not claimed)
            if claimed:
                pygame.draw.rect(self.screen, (60, 80, 65), claim_rect, border_radius=8)
                cap = self.fonts["tiny"].render("CLAIMED", True, COLORS["success"])
            elif ready:
                pygame.draw.rect(self.screen, COLORS["accent"], claim_rect, border_radius=8)
                cap = self.fonts["tiny"].render("CLAIM", True, COLORS["text"])
                self.quest_claim_rects.append({"rect": claim_rect, "scope": scope, "id": qid})
            else:
                pygame.draw.rect(self.screen, (55, 55, 65), claim_rect, border_radius=8)
                cap = self.fonts["tiny"].render("LOCKED", True, COLORS["text_dim"])
            self.screen.blit(cap, cap.get_rect(center=claim_rect.center))

        hint = self.fonts["tiny"].render("Complete quests to claim XP rewards and level up faster.", True, COLORS["text_muted"])
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, panel.bottom - 20)))

        for btn in self.quest_buttons.values():
            btn.render(self.screen)

    def render_jutsu_library(self):
        """Render tiered jutsu library page with lock/unlock status."""
        self.library_item_rects = []
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(COLORS["bg_dark"])

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        title = self.fonts["title_md"].render("JUTSU LIBRARY", True, COLORS["accent"])
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        if self.library_mode == "freeplay":
            subtitle_text = "Select an unlocked jutsu to start Free Play"
        elif self.library_mode == "challenge":
            subtitle_text = "Select an unlocked jutsu to start Challenge Mode"
        else:
            subtitle_text = "Browse only: view lock/unlock progression"
        subtitle = self.fonts["body_sm"].render(subtitle_text, True, COLORS["text_dim"])
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 108)))

        tier_defs = [
            ("Academy Tier", 0, 2),
            ("Genin Tier", 3, 5),
            ("Chunin Tier", 6, 10),
            ("Jonin+ Tier", 11, 999999),
        ]

        tiers = []
        for tier_name, min_lv, max_lv in tier_defs:
            items = []
            for name, data in self.jutsu_list.items():
                req_lv = data.get("min_level", 0)
                if min_lv <= req_lv <= max_lv:
                    items.append((name, data))
            if items:
                items.sort(key=lambda x: x[1].get("min_level", 0))
                tiers.append((tier_name, items))

        panel_x = 70
        panel_w = SCREEN_WIDTH - 140
        panel_y = 140
        panel_gap = 16
        panel_h = 132
        card_w = 180
        card_h = 74
        card_gap = 14

        for idx, (tier_name, items) in enumerate(tiers):
            y = panel_y + idx * (panel_h + panel_gap)
            panel_rect = pygame.Rect(panel_x, y, panel_w, panel_h)

            panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            pygame.draw.rect(panel_bg, (22, 22, 30, 220), panel_bg.get_rect(), border_radius=14)
            pygame.draw.rect(panel_bg, COLORS["border"], panel_bg.get_rect(), 1, border_radius=14)
            self.screen.blit(panel_bg, panel_rect.topleft)

            tier_text = self.fonts["body"].render(tier_name.upper(), True, COLORS["accent_glow"])
            self.screen.blit(tier_text, (panel_rect.x + 16, panel_rect.y + 12))

            start_x = panel_rect.x + 16
            row_y = panel_rect.y + 44
            for i, (jutsu_name, jutsu_data) in enumerate(items):
                x = start_x + i * (card_w + card_gap)
                if x + card_w > panel_rect.right - 16:
                    break

                req_lv = jutsu_data.get("min_level", 0)
                unlocked = self.progression.level >= req_lv
                card_rect = pygame.Rect(x, row_y, card_w, card_h)
                hoverable = self.library_mode in ["freeplay", "challenge"]
                hovered = hoverable and card_rect.collidepoint(pygame.mouse.get_pos())

                if unlocked:
                    fill = (35, 52, 42, 230)
                    border = COLORS["success"]
                    status = "UNLOCKED"
                    status_color = COLORS["success"]
                    if hovered:
                        fill = (45, 70, 56, 235)
                else:
                    fill = (40, 40, 50, 220)
                    border = COLORS["border"]
                    status = f"LOCKED • LV.{req_lv}"
                    status_color = COLORS["error"]

                card_bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
                pygame.draw.rect(card_bg, fill, card_bg.get_rect(), border_radius=10)
                pygame.draw.rect(card_bg, border, card_bg.get_rect(), 2, border_radius=10)
                self.screen.blit(card_bg, card_rect.topleft)

                name_surf = self.fonts["body_sm"].render(jutsu_name.upper(), True, COLORS["text"])
                self.screen.blit(name_surf, (card_rect.x + 10, card_rect.y + 10))

                status_surf = self.fonts["tiny"].render(status, True, status_color)
                self.screen.blit(status_surf, (card_rect.x + 10, card_rect.y + 38))

                seq_len = len(jutsu_data.get("sequence", []))
                seq_surf = self.fonts["tiny"].render(f"SIGNS: {seq_len}", True, COLORS["text_dim"])
                self.screen.blit(seq_surf, (card_rect.x + 10, card_rect.y + 54))

                tier = self._get_mastery_tier(jutsu_name)
                badge = self.mastery_icons.get(tier, self.mastery_icons.get("none"))
                if badge:
                    self.screen.blit(badge, (card_rect.right - 34, card_rect.y + 6))
                tier_text = self.fonts["tiny"].render(f"M: {tier.upper()}", True, COLORS["text_dim"])
                self.screen.blit(tier_text, (card_rect.x + 92, card_rect.y + 54))

                self.library_item_rects.append({
                    "rect": card_rect,
                    "name": jutsu_name,
                    "unlocked": unlocked,
                    "min_level": req_lv,
                })

        hint = self.fonts["body_sm"].render(
            f"YOUR LEVEL: {self.progression.level} • RANK: {self.progression.rank}",
            True,
            COLORS["text"],
        )
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 70)))

        if self.library_mode == "browse":
            mode_hint = self.fonts["tiny"].render("Browse mode: card selection is disabled.", True, COLORS["text_dim"])
        else:
            mode_hint = self.fonts["tiny"].render("Click an unlocked jutsu card to continue.", True, COLORS["text_dim"])
        self.screen.blit(mode_hint, mode_hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 46)))

        for btn in self.library_buttons.values():
            btn.render(self.screen)

    def render_alert_modal(self):
        """Render reusable blocking alert modal."""
        if not self.active_alert:
            return

        title_text = self.active_alert.get("title", "Alert")
        message_text = self.active_alert.get("message", "")
        button_text = self.active_alert.get("button_text", "OK")

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 560, 280
        modal_x = (SCREEN_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        pygame.draw.rect(self.screen, COLORS["bg_panel"], modal_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["accent"], modal_rect, 2, border_radius=16)

        title = self.fonts["title_sm"].render(title_text, True, COLORS["accent_glow"])
        self.screen.blit(title, title.get_rect(center=(modal_rect.centerx, modal_rect.y + 48)))

        words = message_text.split(" ")
        lines = []
        line = []
        for word in words:
            test = " ".join(line + [word])
            if self.fonts["body_sm"].size(test)[0] < modal_w - 60:
                line.append(word)
            else:
                lines.append(" ".join(line))
                line = [word]
        if line:
            lines.append(" ".join(line))

        start_y = modal_rect.y + 98
        for i, msg_line in enumerate(lines[:4]):
            msg = self.fonts["body_sm"].render(msg_line, True, COLORS["text"])
            self.screen.blit(msg, msg.get_rect(center=(modal_rect.centerx, start_y + i * 28)))

        btn_w, btn_h = 180, 52
        self.alert_ok_rect = pygame.Rect(modal_rect.centerx - btn_w // 2, modal_rect.bottom - 78, btn_w, btn_h)
        hovered = self.alert_ok_rect.collidepoint(pygame.mouse.get_pos())
        color = COLORS["accent_glow"] if hovered else COLORS["accent"]
        pygame.draw.rect(self.screen, color, self.alert_ok_rect, border_radius=10)

        ok_text = self.fonts["body"].render(button_text, True, COLORS["text"])
        self.screen.blit(ok_text, ok_text.get_rect(center=self.alert_ok_rect.center))

        if hovered:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
