from src.jutsu_academy.main_pygame_shared import *


class LeaderboardMixin:
    def _fetch_leaderboard(self):
        """Fetch leaderboard data in background."""
        self.leaderboard_loading = True
        try:
            # Use self.leaderboard_mode (default FIREBALL if not set)
            # DATABASE USES UPPERCASE (based on user artifact)
            mode = getattr(self, "leaderboard_mode", "FIREBALL").upper()
            
            # Pagination
            self.leaderboard_limit = getattr(self, "leaderboard_limit", 10)
            self.leaderboard_page = getattr(self, "leaderboard_page", 0)
            offset = self.leaderboard_page * self.leaderboard_limit
            
            data = self.network_manager.get_leaderboard(limit=self.leaderboard_limit, offset=offset, mode=mode)
            self.leaderboard_data = data if data else []
            
            # Start background avatar fetch
            if self.leaderboard_data:
                 threading.Thread(target=self._load_leaderboard_avatars, args=(self.leaderboard_data,), daemon=True).start()
        except:
            self.leaderboard_data = []
        self.leaderboard_loading = False

    def _load_leaderboard_avatars(self, data):
        """Pre-fetch and round surfaces for leaderboard in background."""
        for entry in data:
            url = entry.get("avatar_url")
            username = entry.get("username", "Guest")
            
            # Key by URL if exists, else by username (since Guest might not have URL)
            cache_key = url if url else f"user_{username}"
            
            if cache_key in self.leaderboard_avatars:
                continue
                
            if url:
                try:
                    r = requests.get(url, timeout=3)
                    if r.status_code == 200:
                         self.leaderboard_avatars[cache_key] = self._create_rounded_avatar(r.content, size=(32, 32))
                         continue
                except:
                    pass
            
            # If fetch failed or no URL, use shadow fallback
            self.leaderboard_avatars[cache_key] = self._get_fallback_avatar(size=(32, 32))

    def _fetch_announcements(self):
        """Fetch announcements in background."""
        self.announcements_loading = True
        try:
            data = self.network_manager.get_announcements(limit=5)
            # Flatten if message is a list to allow multi-page paging
            flat_ann = []
            if data:
                for entry in data:
                    msg = entry.get("message", "")
                    # handle stringified lists or actual lists
                    if isinstance(msg, str) and msg.startswith("[") and msg.endswith("]"):
                        try:
                             msg = ast.literal_eval(msg)
                        except: pass
                        
                    if isinstance(msg, list):
                        for m in msg:
                            new_entry = entry.copy()
                            new_entry["message"] = str(m)
                            flat_ann.append(new_entry)
                    else:
                        flat_ann.append(entry)
                        
            self.announcements = flat_ann
            if self.announcements:
                 self.announcements_fetched = True
                 print(f"[+] Loaded {len(self.announcements)} announcement(s)")
        except:
            self.announcements = []
        self.announcements_loading = False

    def render_announcement_popup(self):
        """Render paginated announcement overlay."""
        if not self.show_announcements or not self.announcements:
            return
            
        # 1. Dim Backdrop
        backdrop = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 180))
        self.screen.blit(backdrop, (0, 0))
        
        # 2. Main Card
        card_w, card_h = 500, 350
        card_x = (SCREEN_WIDTH - card_w) // 2
        card_y = (SCREEN_HEIGHT - card_h) // 2
        
        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
        # Outer Border
        pygame.draw.rect(self.screen, (40, 40, 50), card_rect, border_radius=22)
        # Inner Fill
        inner_rect = card_rect.inflate(-4, -4)
        pygame.draw.rect(self.screen, (20, 20, 25), inner_rect, border_radius=20)
        
        # 3. Content
        padding = 30
        title_y = card_y + padding
        
        # Title
        title_txt = self.fonts["title_sm"].render("ANNOUNCEMENTS", True, (245, 158, 11))
        self.screen.blit(title_txt, title_txt.get_rect(center=(SCREEN_WIDTH // 2, title_y + 15)))
        
        # Page Indicator
        total = len(self.announcements)
        idx = self.current_announcement_idx
        page_txt = self.fonts["tiny"].render(f"{idx + 1} / {total}", True, (100, 100, 110))
        self.screen.blit(page_txt, page_txt.get_rect(center=(SCREEN_WIDTH // 2, title_y + 45)))
        
        # Message
        msg_y = title_y + 70
        curr = self.announcements[idx]
        msg = curr.get("message", "No content")
        if isinstance(msg, list): msg = msg[0] if msg else "No content"
        
        # Wrap Text (Simple wrap)
        words = str(msg).split(' ')
        lines = []
        current_line = []
        max_w = card_w - (padding * 2)
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            w, _ = self.fonts["body"].size(test_line)
            if w < max_w:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        
        for i, line in enumerate(lines[:6]): # Limit lines
            line_surf = self.fonts["body"].render(line, True, (220, 220, 230))
            self.screen.blit(line_surf, line_surf.get_rect(center=(SCREEN_WIDTH // 2, msg_y + i * 28)))
            
        # 4. Navigation Buttons
        btn_y = card_y + card_h - 45
        
        # Prev
        if idx > 0:
            txt = self.fonts["body_sm"].render("< Prev", True, (200, 200, 210))
            self.ann_prev_rect = txt.get_rect(center=(card_x + 80, btn_y))
            if self.ann_prev_rect.collidepoint(pygame.mouse.get_pos()):
                 txt = self.fonts["body_sm"].render("< Prev", True, COLORS["accent"])
            self.screen.blit(txt, self.ann_prev_rect)
            

        elif hasattr(self, 'ann_prev_rect'): del self.ann_prev_rect
            
        # Next
        if idx < total - 1:
            txt = self.fonts["body_sm"].render("Next >", True, (200, 200, 210))
            self.ann_next_rect = txt.get_rect(center=(card_x + card_w - 80, btn_y))
            if self.ann_next_rect.collidepoint(pygame.mouse.get_pos()):
                 txt = self.fonts["body_sm"].render("Next >", True, COLORS["accent"])
            self.screen.blit(txt, self.ann_next_rect)
            

        elif hasattr(self, 'ann_next_rect'): del self.ann_next_rect
            
        # Close (Only on last page)
        if idx == total - 1:
            close_txt = self.fonts["body"].render("CLOSE", True, (20, 20, 20))
            btn_w, btn_h = 100, 36
            self.ann_close_rect = pygame.Rect(SCREEN_WIDTH // 2 - btn_w // 2, btn_y - btn_h // 2, btn_w, btn_h)
            color = (245, 158, 11)
            if self.ann_close_rect.collidepoint(pygame.mouse.get_pos()):
                 color = (217, 119, 6)
            pygame.draw.rect(self.screen, color, self.ann_close_rect, border_radius=8)
            

            self.screen.blit(close_txt, close_txt.get_rect(center=self.ann_close_rect.center))
        elif hasattr(self, 'ann_close_rect'): 
            del self.ann_close_rect

    def render_leaderboard(self):
        """Render leaderboard screen."""
        self.screen.fill(COLORS["bg_dark"])
        
        # Initialize mode if not set
        if not hasattr(self, "leaderboard_mode"):
            self.leaderboard_mode = "FIREBALL"
            
        # Title
        title = self.fonts["title_md"].render("HALL OF FAME", True, (218, 165, 32))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)
        
        # --- Filter / Mode Selection ---
        center_x = SCREEN_WIDTH // 2
        y_pos = 110
        
        mode_surf = self.fonts["title_sm"].render(self.leaderboard_mode, True, COLORS["accent"])
        mode_rect = mode_surf.get_rect(center=(center_x, y_pos))
        self.screen.blit(mode_surf, mode_rect)
        
        # Arrows
        mp = pygame.mouse.get_pos()
        if "left" in self.arrow_icons:
             # Left Arrow
             l_arrow = self.arrow_icons["left"]
             l_rect = l_arrow.get_rect(center=(center_x - 140, y_pos))
             self.mode_arrow_left_rect = l_rect
             
             if l_rect.collidepoint(mp):
                 l_arrow.set_alpha(255)
                 pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
             else:
                 l_arrow.set_alpha(150)
             self.screen.blit(l_arrow, l_rect)
             

             
             # Right Arrow
             r_arrow = self.arrow_icons["right"]
             r_rect = r_arrow.get_rect(center=(center_x + 140, y_pos))
             self.mode_arrow_right_rect = r_rect
             
             if r_rect.collidepoint(mp):
                 r_arrow.set_alpha(255)
                 pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
             else:
                 r_arrow.set_alpha(150)
             self.screen.blit(r_arrow, r_rect)
             

        else:
             # Text fallback
             fallback_surf = self.fonts["body"].render("<  Target  >", True, COLORS["text_dim"])
             self.screen.blit(fallback_surf, fallback_surf.get_rect(center=(center_x, y_pos + 30)))

        # Draw buttons
        for btn in self.leaderboard_buttons.values():
            btn.render(self.screen)
            
        # Table
        panel_rect = pygame.Rect(100, 150, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200)
        pygame.draw.rect(self.screen, COLORS["bg_panel"], panel_rect, border_radius=16)
        pygame.draw.rect(self.screen, COLORS["border"], panel_rect, 1, border_radius=16)
        
        # Header
        h_y = 170
        headers = ["Rank", "Shinobi", "Score", "Title"] 
        x_offs = [40, 140, 480, 680] # Moved Shinobi slightly left to make room for avatar
        for i, (h, x) in enumerate(zip(headers, x_offs)):
            txt = self.fonts["body"].render(h, True, COLORS["accent"])
            # Adjust title slightly to the right to clear avatars
            draw_x = x if i != 1 else x + 40
            self.screen.blit(txt, (panel_rect.x + draw_x, h_y))
            
        pygame.draw.line(self.screen, COLORS["border"], (panel_rect.x + 20, h_y + 30), (panel_rect.right - 20, h_y + 30))
        
        # Rows
        if self.leaderboard_loading:
             txt = self.fonts["body"].render("Summoning scrolls...", True, COLORS["text"])
             self.screen.blit(txt, txt.get_rect(center=panel_rect.center))
        elif not self.leaderboard_data:
             txt = self.fonts["body"].render(f"No {self.leaderboard_mode} records found.", True, COLORS["text_dim"])
             self.screen.blit(txt, txt.get_rect(center=panel_rect.center))
        else:
             row_y = h_y + 50
             
             page = getattr(self, 'leaderboard_page', 0)
             limit = getattr(self, 'leaderboard_limit', 10)
             
             for i, entry in enumerate(self.leaderboard_data):
                 # Leave space for pagination
                 if row_y > panel_rect.bottom - 60: break
                 
                 rank_num = i + 1 + (page * limit)
                 
                 # Row Background
                 if rank_num == 1:
                     # Gold Glow for Hokage
                     r_glow = pygame.Rect(panel_rect.x + 10, row_y - 8, panel_rect.width - 20, 36)
                     # Need surface for alpha rect
                     s = pygame.Surface((r_glow.width, r_glow.height), pygame.SRCALPHA)
                     s.fill((218, 165, 32, 40)) # Low alpha gold
                     self.screen.blit(s, r_glow)
                     pygame.draw.rect(self.screen, (218, 165, 32), r_glow, 1, border_radius=8)
                 elif i % 2 == 0:
                     # Alternating dark stripe
                     r = pygame.Rect(panel_rect.x + 20, row_y - 5, panel_rect.width - 40, 30)
                     pygame.draw.rect(self.screen, (30, 30, 35), r, border_radius=4)
                 
                 # Rank Coloring & Titles
                 title_text = "Genin"
                 color = COLORS["text"]
                 
                 if rank_num == 1:
                     title_text = "HOKAGE"
                     color = (255, 215, 0) # Gold
                 elif rank_num <= 3:
                     title_text = "Jonin"
                     color = (192, 192, 192) # Silver-ish
                 elif rank_num <= 10:
                     title_text = "Chunin"
                     color = (205, 127, 50) # Bronze-ish
                     
                 # Rank
                 self.screen.blit(self.fonts["body_sm"].render(f"#{rank_num}", True, color), (panel_rect.x + x_offs[0], row_y))
                 
                 # Profile Picture (Avatar)
                 url = entry.get("avatar_url")
                 username = entry.get("username", "Guest")
                 cache_key = url if url else f"user_{username}"
                 avatar_surf = self.leaderboard_avatars.get(cache_key)
                 
                 if not avatar_surf:
                      # One-time lazy load if thread hasn't finished
                      fallback = self._get_fallback_avatar(size=(32, 32))
                      self.screen.blit(fallback, (panel_rect.x + x_offs[1], row_y - 8))
                 else:
                      self.screen.blit(avatar_surf, (panel_rect.x + x_offs[1], row_y - 8))

                 # Name
                 self.screen.blit(self.fonts["body_sm"].render(username[:14], True, COLORS["text"]), (panel_rect.x + x_offs[1] + 40, row_y))
                 
                 # Score
                 score = f"{entry.get('score_time', 0):.2f}s"
                 self.screen.blit(self.fonts["body_sm"].render(score, True, COLORS["success"]), (panel_rect.x + x_offs[2], row_y))
                 
                 # Title (replacing Mode)
                 self.screen.blit(self.fonts["body_sm"].render(title_text, True, color), (panel_rect.x + x_offs[3], row_y))
                 
                 row_y += 35
             
             # Pagination Controls
             page_y = panel_rect.bottom - 30
             center_x = panel_rect.centerx
             
             # Clean cleanup
             if hasattr(self, 'leaderboard_prev_rect'): del self.leaderboard_prev_rect
             if hasattr(self, 'leaderboard_next_rect'): del self.leaderboard_next_rect

             # Page Text
             p_txt = self.fonts["body_sm"].render(f"Page {page + 1}", True, COLORS["text_dim"])
             self.screen.blit(p_txt, p_txt.get_rect(center=(center_x, page_y)))
             
             # Prev Button
             if page > 0:
                 txt = self.fonts["body_sm"].render("< Prev", True, COLORS["accent"])
                 rect = txt.get_rect(center=(center_x - 80, page_y))
                 self.leaderboard_prev_rect = rect 
                 
                 if rect.collidepoint(pygame.mouse.get_pos()):
                     txt = self.fonts["body_sm"].render("< Prev", True, COLORS["accent_glow"])
                     pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                 self.screen.blit(txt, rect)
             
             # Next Button
             # If we have full page, assume more exist
             if len(self.leaderboard_data) >= limit:
                 txt = self.fonts["body_sm"].render("Next >", True, COLORS["accent"])
                 rect = txt.get_rect(center=(center_x + 80, page_y))
                 self.leaderboard_next_rect = rect

                 if rect.collidepoint(pygame.mouse.get_pos()):
                     txt = self.fonts["body_sm"].render("Next >", True, COLORS["accent_glow"])
                     pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                 self.screen.blit(txt, rect)
