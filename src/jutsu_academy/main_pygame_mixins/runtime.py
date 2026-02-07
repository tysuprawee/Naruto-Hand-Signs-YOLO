from src.jutsu_academy.main_pygame_shared import *


class RuntimeMixin:
    def handle_events(self):
        """Handle pygame events."""
        mouse_click = False
        
        # Capture events first
        events = pygame.event.get()
        self._activate_next_alert()
        self._refresh_quest_periods()

        # Global reusable alert modal: blocks underlying interactions
        if self.active_alert:
            mouse_pos = pygame.mouse.get_pos()
            for event in events:
                if event.type == pygame.QUIT:
                    self.prev_state = self.state
                    self.state = GameState.QUIT_CONFIRM
                    self.active_alert = None
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.alert_ok_rect.collidepoint(mouse_pos):
                        self.play_sound("click")
                        self.active_alert = None
                        return
                if event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE]:
                    self.play_sound("click")
                    self.active_alert = None
                    return
            return
        
        # IMPORTANT: Announcement Overlay Clicks
        # If showing announcements, we intercept clicks and keys
        if self.show_announcements:
            mouse_pos = pygame.mouse.get_pos()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Prev
                    if hasattr(self, 'ann_prev_rect') and self.ann_prev_rect.collidepoint(mouse_pos):
                         self.current_announcement_idx = max(0, self.current_announcement_idx - 1)
                         self.play_sound("click")
                    # Next
                    elif hasattr(self, 'ann_next_rect') and self.ann_next_rect.collidepoint(mouse_pos):
                         self.current_announcement_idx = min(len(self.announcements)-1, self.current_announcement_idx + 1)
                         self.play_sound("click")
                    # Close
                    elif hasattr(self, 'ann_close_rect') and self.ann_close_rect.collidepoint(mouse_pos):
                         self.show_announcements = False
                         self.play_sound("click")
                elif event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN]:
                         self.show_announcements = False
                         self.play_sound("click")
                    elif event.key == pygame.K_LEFT:
                         self.current_announcement_idx = max(0, self.current_announcement_idx - 1)
                    elif event.key == pygame.K_RIGHT:
                         self.current_announcement_idx = min(len(self.announcements)-1, self.current_announcement_idx + 1)
            return # Block other menu interactions while announcements are up

        for event in events:
            if event.type == pygame.QUIT:
                # Intercept close button
                if self.state == GameState.SETTINGS:
                    self._stop_settings_camera_preview()
                self.prev_state = self.state
                self.state = GameState.QUIT_CONFIRM
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_click = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.PLAYING:
                        self.stop_game()
                    elif self.state == GameState.MENU:
                        # ESC in menu -> Quit Confirm
                        self.prev_state = GameState.MENU
                        self.state = GameState.QUIT_CONFIRM
                    elif self.state in [GameState.SETTINGS, GameState.ABOUT, GameState.PRACTICE_SELECT, GameState.JUTSU_LIBRARY, GameState.QUESTS, GameState.TUTORIAL]:
                        if self.state == GameState.SETTINGS:
                            self._stop_settings_camera_preview()
                        if self.state == GameState.JUTSU_LIBRARY:
                            self.state = GameState.PRACTICE_SELECT
                        elif self.state == GameState.QUESTS:
                            self.state = GameState.PRACTICE_SELECT
                        elif self.state == GameState.TUTORIAL:
                            self.tutorial_seen = True
                            self.tutorial_seen_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                            self._save_player_meta()
                            self.state = GameState.MENU
                        else:
                            self.state = GameState.MENU
                    elif self.state == GameState.LOGIN_MODAL:
                        if not self.login_in_progress:
                            self.state = GameState.MENU
                elif self.state == GameState.PLAYING:
                    can_switch = not self.jutsu_active
                    if self.game_mode == "challenge" and self.challenge_state != "waiting":
                        can_switch = False
                        
                    if event.key == pygame.K_LEFT and can_switch:
                        self.switch_jutsu(-1)
                    elif event.key == pygame.K_RIGHT and can_switch:
                        self.switch_jutsu(1)
                    elif event.key == pygame.K_r:
                        self.current_step = 0
                        self.sequence_run_start = None
                        self.jutsu_active = False
                        self.fire_particles.emitting = False
                    elif event.key == pygame.K_SPACE:
                        if self.game_mode == "challenge":
                            if self.challenge_state == "waiting":
                                self.challenge_state = "countdown"
                                self.challenge_countdown_start = time.time()
                                self.play_sound("click")
                            elif self.challenge_state == "results":
                                # Reset challenge
                                self.challenge_state = "waiting"
                                self.current_step = 0
                                self.sequence_run_start = None
                                self.jutsu_active = False
                                self.submission_complete = False
                                self.challenge_rank_info = ""
                                if self.video_cap:
                                    self.video_cap.release()
                                    self.video_cap = None
                                self.current_video = None
            elif event.type == pygame.MOUSEWHEEL:
                if self.state == GameState.ABOUT:
                    self.about_scroll_y -= event.y * 30
                    if self.about_scroll_y < 0:
                        self.about_scroll_y = 0
                elif self.state == GameState.PRACTICE_SELECT:
                    self.practice_scroll_y -= event.y * 36
                    if self.practice_scroll_y < 0:
                        self.practice_scroll_y = 0
        
        # ✅ IMPORTANT: read mouse state AFTER event processing
        mouse_pos = pygame.mouse.get_pos()
        mouse_down = pygame.mouse.get_pressed()[0]
        
        # State-specific updates
        if self.state == GameState.QUIT_CONFIRM:
            if mouse_click:
                # Quit
                if hasattr(self, 'quit_confirm_rect') and self.quit_confirm_rect.collidepoint(mouse_pos):
                    # Do NOT call cleanup() here, let the loop finish
                    self.play_sound("click")
                    self.running = False
                # Stay
                if hasattr(self, 'quit_cancel_rect') and self.quit_cancel_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    self.state = self.prev_state if self.prev_state else GameState.MENU
        
        elif self.state == GameState.LOGOUT_CONFIRM:
            if mouse_click:
                # Yes, Logout and Quit
                if hasattr(self, 'logout_confirm_rect') and self.logout_confirm_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    self.logout_discord()
                    self.profile_dropdown_open = False
                    self.running = False # Quit game on logout as requested
                # Cancel
                if hasattr(self, 'logout_cancel_rect') and self.logout_cancel_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    self.state = GameState.MENU
                    
        elif self.state == GameState.WELCOME_MODAL:
            # Handle key fallback
            if any(event.type == pygame.KEYDOWN and event.key in [pygame.K_SPACE, pygame.K_RETURN] for event in events):
                 self.play_sound("click")
                 self.state = GameState.MENU
                 if self.pending_action == "practice":
                     self.state = GameState.PRACTICE_SELECT
                     self.pending_action = None
            
            if mouse_click:
                if hasattr(self, 'welcome_ok_rect') and self.welcome_ok_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    self.state = GameState.MENU
                    # Optionally go to practice if that was pending
                    if self.pending_action == "practice":
                        self.state = GameState.PRACTICE_SELECT
                        self.pending_action = None
                        
        elif self.state == GameState.ERROR_MODAL:
            if mouse_click:
                 if hasattr(self, 'error_ok_rect') and self.error_ok_rect.collidepoint(mouse_pos):
                     self.play_sound("click")
                     self.state = GameState.MENU
            
        elif self.state == GameState.CONNECTION_LOST:
            if mouse_click:
                if hasattr(self, 'conn_lost_exit_rect') and self.conn_lost_exit_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    self.running = False

        elif self.state == GameState.MENU:
            # Check mute button click
            if mouse_click and self.mute_button_rect.collidepoint(mouse_pos):
                self.play_sound("click")
                self.toggle_mute()
            
            # Check social links
            if mouse_click and hasattr(self, 'social_rects'):
                for link_name, rect in self.social_rects.items():
                    if rect.collidepoint(mouse_pos):
                        self.play_sound("click")
                        url = SOCIAL_LINKS.get(link_name)
                        if url:
                            webbrowser.open(url)
            
            # Profile Interactions
            if mouse_click:
                if self.profile_dropdown_open:
                    # Check logout click
                    if hasattr(self, 'logout_item_rect') and self.logout_item_rect.collidepoint(mouse_pos):
                        self.play_sound("click")
                        self.state = GameState.LOGOUT_CONFIRM
                        self.profile_dropdown_open = False
                    # Close dropdown if clicked outside
                    elif hasattr(self, 'profile_rect') and not self.profile_rect.collidepoint(mouse_pos):
                        self.profile_dropdown_open = False
                
                # Toggle dropdown on profile click (if logged in)
                if hasattr(self, 'profile_rect') and self.profile_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    if self.discord_user:
                        self.profile_dropdown_open = not self.profile_dropdown_open
                    else:
                        # If guest, clicking profile opens login modal
                        self.state = GameState.LOGIN_MODAL
                        self.login_modal_message = "Log in to access your profile."
                        self.pending_action = None

            # Menu buttons
            for name, btn in self.menu_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "practice":
                        # Check login requirement
                        if not self.discord_user:
                            self.state = GameState.LOGIN_MODAL
                            self.login_modal_message = "Please log in with Discord to access the Academy and save your progress."
                            self.pending_action = "practice"
                        else:
                            self.state = GameState.PRACTICE_SELECT
                    elif name == "settings":
                        self.settings_preview_enabled = False
                        self._stop_settings_camera_preview()
                        self.state = GameState.SETTINGS
                    elif name == "about":
                        self.state = GameState.ABOUT
                    elif name == "tutorial":
                        self.tutorial_step_index = 0
                        self.state = GameState.TUTORIAL
                    elif name == "quit":
                        self.prev_state = GameState.MENU
                        self.state = GameState.QUIT_CONFIRM
        
        elif self.state == GameState.LOGIN_MODAL:
            if mouse_click:
                if hasattr(self, 'modal_login_rect') and self.modal_login_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    if self.login_in_progress:
                        # Reopen browser - same server will receive callback
                        if self.discord_auth_url:
                            webbrowser.open(self.discord_auth_url)
                            print(f"[AUTH] User clicked reopen browser")
                        else:
                            print(f"[AUTH] No URL yet, waiting...")
                    else:
                        # Start new login
                        self.start_discord_login()
                
                # Cancel button
                if hasattr(self, 'modal_cancel_rect') and self.modal_cancel_rect.collidepoint(mouse_pos):
                    self.play_sound("click")
                    if self.login_in_progress:
                        # Cancel the login
                        self.cancel_discord_login()
                    self.state = GameState.MENU
                    self.pending_action = None
                    self.login_error = ""
        
        elif self.state == GameState.SETTINGS:
            # Update sliders
            any_dragging = False
            for slider in self.settings_sliders.values():
                if slider.update(mouse_pos, mouse_down, mouse_click):
                    any_dragging = True
            
            # Real-time volume updates while dragging
            if any_dragging or mouse_click:
                if not self.is_muted:
                    pygame.mixer.music.set_volume(self._effective_music_volume(self.settings_sliders["music"].value))
            
            if self.camera_dropdown.update(mouse_pos, mouse_click, self.play_sound):
                self.settings["camera_idx"] = self.camera_dropdown.selected_idx
                if self.settings_preview_enabled:
                    self._start_settings_camera_preview(self.camera_dropdown.selected_idx)
            
            # Keep these always ON and non-interactive.
            self.settings_checkboxes["use_mp"].checked = True
            self.settings_checkboxes["restricted"].checked = True
            self.settings_checkboxes["debug_hands"].update(mouse_pos, mouse_click, self.play_sound)
            
            for name, btn in self.settings_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "preview_toggle":
                        self.settings_preview_enabled = not self.settings_preview_enabled
                        if self.settings_preview_enabled:
                            self._refresh_settings_camera_options(force=False)
                            self._start_settings_camera_preview(self.settings["camera_idx"])
                        else:
                            self._stop_settings_camera_preview()
                    if name == "scan_cameras":
                        self._refresh_settings_camera_options(force=True)
                        self.settings["camera_idx"] = self.camera_dropdown.selected_idx
                        if self.settings_preview_enabled:
                            self._start_settings_camera_preview(self.settings["camera_idx"])
                    if name == "back":
                        # Save settings
                        self.settings["music_vol"] = self.settings_sliders["music"].value
                        self.settings["sfx_vol"] = self.settings_sliders["sfx"].value
                        self.settings["camera_idx"] = self.camera_dropdown.selected_idx
                        self.settings["debug_hands"] = self.settings_checkboxes["debug_hands"].checked
                        self.settings["use_mediapipe_signs"] = True
                        self.settings["restricted_signs"] = True
                        
                        if not self.is_muted:
                            pygame.mixer.music.set_volume(self._effective_music_volume(self.settings["music_vol"]))
                        self.save_settings()
                        self.settings_preview_enabled = False
                        self._stop_settings_camera_preview()
                        self.state = GameState.MENU
        
        elif self.state == GameState.PRACTICE_SELECT:
            for name, btn in self.practice_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "freeplay":
                        self.library_mode = "freeplay"
                        self.state = GameState.JUTSU_LIBRARY
                    elif name == "challenge":
                        self.library_mode = "challenge"
                        self.state = GameState.JUTSU_LIBRARY
                    elif name == "library":
                        self.library_mode = "browse"
                        self.state = GameState.JUTSU_LIBRARY
                    elif name == "multiplayer":
                        self.play_sound("click")
                        print("[*] Multiplayer is currently locked.")
                    elif name == "quests":
                        self.state = GameState.QUESTS
                    elif name == "leaderboard":
                        self.state = GameState.LEADERBOARD
                        # Trigger fetch
                        threading.Thread(target=self._fetch_leaderboard, daemon=True).start()
                    elif name == "back":
                        self.state = GameState.MENU
        
        elif self.state == GameState.LEADERBOARD:
            # Mode Selector Click (Arrows)
            clicked_dir = 0
            if mouse_click:
                if hasattr(self, 'mode_arrow_left_rect') and self.mode_arrow_left_rect.collidepoint(mouse_pos):
                    clicked_dir = -1
                elif hasattr(self, 'mode_arrow_right_rect') and self.mode_arrow_right_rect.collidepoint(mouse_pos):
                    clicked_dir = 1
            
            if clicked_dir != 0:
                self.play_sound("click")
                
                # Get modes
                if not hasattr(self, "leaderboard_modes_list"):
                    try:
                        self.leaderboard_modes_list = [k.upper() for k in OFFICIAL_JUTSUS.keys()]
                    except:
                        self.leaderboard_modes_list = ["FIREBALL", "CHIDORI", "SHARINGAN", "RASENGAN"]
                        
                # Cycle
                curr = getattr(self, "leaderboard_mode", "FIREBALL")
                try:
                    idx = self.leaderboard_modes_list.index(curr)
                    new_idx = (idx + clicked_dir) % len(self.leaderboard_modes_list)
                    self.leaderboard_mode = self.leaderboard_modes_list[new_idx]
                except:
                    self.leaderboard_mode = self.leaderboard_modes_list[0]
                    
                # Refetch
                threading.Thread(target=self._fetch_leaderboard, daemon=True).start()

            # Pagination Clicks
            if mouse_click:
                page_changed = False
                if hasattr(self, 'leaderboard_prev_rect') and self.leaderboard_prev_rect.collidepoint(mouse_pos):
                    self.leaderboard_page = max(0, getattr(self, 'leaderboard_page', 0) - 1)
                    page_changed = True
                    self.play_sound("click")
                elif hasattr(self, 'leaderboard_next_rect') and self.leaderboard_next_rect.collidepoint(mouse_pos):
                    self.leaderboard_page = getattr(self, 'leaderboard_page', 0) + 1
                    page_changed = True
                    self.play_sound("click")
                
                if page_changed:
                    threading.Thread(target=self._fetch_leaderboard, daemon=True).start()

            for name, btn in self.leaderboard_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "back":
                        self.state = GameState.PRACTICE_SELECT
                    elif name == "refresh":
                        threading.Thread(target=self._fetch_leaderboard, daemon=True).start()
        
        elif self.state == GameState.ABOUT:
            for name, btn in self.about_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "back":
                        self.state = GameState.MENU

        elif self.state == GameState.TUTORIAL:
            step_idx = getattr(self, "tutorial_step_index", 0)
            max_idx = len(self.tutorial_steps) - 1
            for name, btn in self.tutorial_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "back":
                        self.tutorial_step_index = max(0, step_idx - 1)
                    elif name == "next":
                        if step_idx >= max_idx:
                            self.tutorial_seen = True
                            self.tutorial_seen_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                            self._save_player_meta()
                            self.state = GameState.MENU
                        else:
                            self.tutorial_step_index = min(max_idx, step_idx + 1)
                    elif name == "skip":
                        self.tutorial_seen = True
                        self.tutorial_seen_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        self._save_player_meta()
                        self.state = GameState.MENU

        elif self.state == GameState.QUESTS:
            if mouse_click:
                for item in getattr(self, "quest_claim_rects", []):
                    if item["rect"].collidepoint(mouse_pos):
                        self._claim_quest(item["scope"], item["id"])
                        break
            for name, btn in self.quest_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "back":
                        self.state = GameState.PRACTICE_SELECT

        elif self.state == GameState.JUTSU_LIBRARY:
            if mouse_click:
                for item in getattr(self, "library_item_rects", []):
                    if item["rect"].collidepoint(mouse_pos):
                        if self.library_mode == "browse":
                            self.play_sound("click")
                            break

                        if not item["unlocked"]:
                            self.play_sound("click")
                            req_lv = item["min_level"]
                            self.show_alert("Skill Locked", f"{item['name']} unlocks at LV.{req_lv}.")
                            break

                        if item["name"] in self.jutsu_names:
                            jutsu_idx = self.jutsu_names.index(item["name"])
                            self.play_sound("click")
                            mode = "practice" if self.library_mode == "freeplay" else "challenge"
                            self.start_game(mode, initial_jutsu_idx=jutsu_idx)
                            break

            for name, btn in self.library_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "back":
                        self.state = GameState.PRACTICE_SELECT
        
        elif self.state == GameState.PLAYING:
            if hasattr(self, "playing_back_button"):
                if self.playing_back_button.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    self.stop_game(return_to_library=True)
                    return

            # Check arrow clicks
            cam_x = (SCREEN_WIDTH - 640) // 2
            cam_y = 110 # Synchronized with render_playing margin
            
            # Switch gating: Disable if challenge is active/countdown
            can_switch = not self.jutsu_active
            if self.game_mode == "challenge" and self.challenge_state != "waiting":
                can_switch = False

            if mouse_click and can_switch:
                if hasattr(self, "left_arrow_rect") and self.left_arrow_rect.collidepoint(mouse_pos):
                    self.switch_jutsu(-1)
                    self.play_sound("click")
                elif hasattr(self, "right_arrow_rect") and self.right_arrow_rect.collidepoint(mouse_pos):
                    self.switch_jutsu(1)
                    self.play_sound("click")

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            
            self.handle_events()
            
            # Render based on state
            if self.state == GameState.MENU:
                self.render_menu()
            elif self.state == GameState.LOGIN_MODAL:
                # Render menu underneath, then modal on top
                self.render_menu()
                self.render_login_modal()
            elif self.state == GameState.SETTINGS:
                self.render_settings()
            elif self.state == GameState.PRACTICE_SELECT:
                self.render_practice_select()
            elif self.state == GameState.ABOUT:
                self.render_about()
            elif self.state == GameState.TUTORIAL:
                self.render_tutorial()
            elif self.state == GameState.JUTSU_LIBRARY:
                self.render_jutsu_library()
            elif self.state == GameState.QUESTS:
                self.render_quests()
            elif self.state == GameState.LEADERBOARD:
                self.render_leaderboard()
            elif self.state == GameState.LOADING:
                self._render_loading()
            elif self.state == GameState.PLAYING:
                self.render_playing(dt)
            elif self.state == GameState.LOGIN_MODAL:
                # Render underlying state first for background context
                if self.prev_state == GameState.MENU:
                    self.render_menu()
                elif self.prev_state == GameState.PRACTICE_SELECT:
                    self.render_practice_select()
                else:
                    self.render_menu()
                self.render_login_modal()
            elif self.state == GameState.QUIT_CONFIRM:
                # Render underlying state first
                if self.prev_state:
                    if self.prev_state == GameState.MENU:
                        self.render_menu()
                    else:
                        self.screen.fill(COLORS["bg_dark"])
                else:
                    self.render_menu()
                self.render_quit_confirm()
            elif self.state == GameState.WELCOME_MODAL:
                # Render underlying background only (cleaner)
                if hasattr(self, 'background') and self.background:
                    # Scale to fit if needed
                    self.screen.blit(self.background, (0, 0))
                else:
                    self.screen.fill(COLORS["bg_dark"])
                self.render_welcome_modal(dt)
            elif self.state == GameState.LOGOUT_CONFIRM:
                # Render underlying state first
                self.render_menu()
                self.render_logout_confirm()
            elif self.state == GameState.CONNECTION_LOST:
                # Render underlying state first (to look like an overlay)
                self.render_menu()
                self.render_connection_lost()

            if self.active_alert:
                self.render_alert_modal()
            
            pygame.display.flip()
        
        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self._stop_camera()
        pygame.quit()
        print("[*] Jutsu Academy closed.")
