#!/usr/bin/env python3
"""
Jutsu Academy - Full Pygame Edition
====================================
A complete Pygame-based launcher and game for the Jutsu Trainer with:
- Modern menu system
- Settings with volume sliders
- Camera selection
- Practice mode (Free Play, Challenge)
- Particle effects and visual polish
- Sound system

Usage:
    python src/jutsu_academy/main_pygame.py
"""

import cv2
import time
import math
import argparse
import socket
from pathlib import Path
import numpy as np
import pygame
import sys
import json
import webbrowser
import threading
import os
import requests
import ast
from io import BytesIO

# Add parent path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ultralytics import YOLO
import mediapipe as mp

from src.utils.paths import get_class_names, get_latest_weights
from src.jutsu_registry import OFFICIAL_JUTSUS
from src.mp_trainer import SignRecorder

# Safe Import NetworkManager
try:
    from src.jutsu_academy.network_manager import NetworkManager
except ImportError:
    print("[!] NetworkManager import failed (missing supabase?). using mock.")
    class NetworkManager:
        def __init__(self): self.client = None
        def get_leaderboard(self, **kwargs): return []
        def submit_score(self, **kwargs): pass

# Try importing Discord auth and dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Discord credentials from env
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")

# Advanced Camera Discovery
try:
    from pygrabber.dshow_graph import FilterGraph
except ImportError:
    FilterGraph = None


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
APP_VERSION = "1.0.0"
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Social Links
SOCIAL_LINKS = {
    "instagram": "https://www.instagram.com/james.uzumaki_/",
    "youtube": "https://www.youtube.com/@James_Uzumaki",
    "discord": "https://discord.gg/7xBQ22SnN2",
}

# Color Palette (Naruto-themed dark mode)
COLORS = {
    "bg_dark": (15, 15, 20),
    "bg_panel": (25, 25, 35),
    "bg_card": (35, 35, 50),
    "bg_hover": (45, 45, 65),
    "accent": (255, 120, 50),       # Orange (Naruto's color)
    "accent_dark": (200, 90, 30),
    "accent_glow": (255, 150, 80),
    "success": (50, 200, 120),
    "error": (220, 60, 60),
    "text": (240, 240, 245),
    "text_dim": (140, 140, 160),
    "text_muted": (80, 80, 100),
    "border": (60, 60, 80),
    "shadow": (0, 0, 0, 100),
    # Fire colors
    "fire_core": (255, 255, 200),
    "fire_mid": (255, 180, 50),
    "fire_outer": (255, 80, 20),
}


# ═══════════════════════════════════════════════════════════════════════════
# PARTICLE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, vx, vy, lifetime, size, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.color = color
    
    def update(self, dt, wind_x=0):
        self.x += (self.vx + wind_x) * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        self.x += math.sin(time.time() * 5 + self.y * 0.05) * 30 * dt
    
    def is_alive(self):
        return self.lifetime > 0
    
    def get_alpha(self):
        return max(0, min(255, int(255 * (self.lifetime / self.max_lifetime))))


class FireParticleSystem:
    def __init__(self, max_particles=150):
        self.particles = []
        self.max_particles = max_particles
        self.emitting = False
        self.emit_x = 0
        self.emit_y = 0
        self.wind_x = 0
    
    def set_position(self, x, y):
        self.emit_x = x
        self.emit_y = y
    
    def emit(self, count=5):
        if not self.emitting:
            return
        
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break
            
            angle = np.random.uniform(-0.5, 0.5)
            speed = np.random.uniform(100, 200)
            vx = speed * math.sin(angle) * 0.3
            vy = -speed
            
            lifetime = np.random.uniform(0.5, 1.2)
            size = np.random.uniform(8, 25)
            
            temp = np.random.random()
            if temp > 0.8:
                color = COLORS["fire_core"]
            elif temp > 0.4:
                color = COLORS["fire_mid"]
            else:
                color = COLORS["fire_outer"]
            
            self.particles.append(Particle(
                self.emit_x + np.random.uniform(-15, 15),
                self.emit_y + np.random.uniform(-5, 5),
                vx, vy, lifetime, size, color
            ))
    
    def update(self, dt):
        for p in self.particles:
            p.update(dt, self.wind_x)
        self.particles = [p for p in self.particles if p.is_alive()]
        if self.emitting:
            self.emit(8)
    
    def render(self, surface):
        for p in self.particles:
            alpha = p.get_alpha()
            life_ratio = p.lifetime / p.max_lifetime
            size = int(p.size * life_ratio)
            
            if size < 2:
                continue
            
            for i in range(3):
                glow_size = size + i * 4
                glow_alpha = max(0, alpha - i * 60)
                if glow_alpha <= 0:
                    continue
                
                color_with_alpha = (*p.color, glow_alpha)
                temp_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, color_with_alpha, (glow_size, glow_size), glow_size)
                surface.blit(temp_surf, (int(p.x - glow_size), int(p.y - glow_size)), special_flags=pygame.BLEND_ADD)


# ═══════════════════════════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════
class Button:
    def __init__(self, x, y, width, height, text, font_size=28, color=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font_size = font_size
        self.color = color or COLORS["accent"]
        self.hovered = False
        self.pressed = False
        self.press_started = False  # Track if press started on this button
        self.font = None
        self.enabled = True
    
    def update(self, mouse_pos, mouse_click, mouse_down, play_sound=None):
        if not self.enabled:
            self.hovered = False
            self.pressed = False
            self.press_started = False
            return False
        
        prev_hover = self.hovered
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        # Hover Sound
        if self.hovered and not prev_hover and play_sound:
            play_sound("hover")
        
        # Track if mouse press started on this button
        if mouse_click and self.hovered:
            self.press_started = True
        
        # Visual pressed state (for rendering)
        self.pressed = self.hovered and mouse_down and self.press_started
        
        # Check for complete click (press started here AND released here)
        clicked = False
        if not mouse_down and self.press_started:
            # Mouse was released
            if self.hovered:
                # Released on the button - valid click!
                clicked = True
                if play_sound:
                    play_sound("click")
                    
            # Reset press tracking
            self.press_started = False
        
        return clicked
    
    def render(self, surface):
        if self.font is None:
            self.font = pygame.font.Font(None, self.font_size)
        
        # Background
        if not self.enabled:
            color = COLORS["text_muted"]
        elif self.pressed:
            color = COLORS["accent_dark"]
        elif self.hovered:
            color = COLORS["accent_glow"]
        else:
            color = self.color
        
        # Shadow
        shadow_rect = self.rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(surface, (0, 0, 0, 50), shadow_rect, border_radius=12)
        
        # Button
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        
        # Border glow on hover
        if self.hovered and self.enabled:
            pygame.draw.rect(surface, COLORS["text"], self.rect, 2, border_radius=12)
        
        # Text
        text_color = COLORS["text"] if self.enabled else COLORS["text_dim"]
        text_surf = self.font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        



class Slider:
    def __init__(self, x, y, width, label, initial=0.7):
        self.x = x
        self.y = y
        self.width = width
        self.label = label
        self.value = initial
        self.height = 10
        # Larger hit area that covers the knob (extends 15px above and below)
        self.rect = pygame.Rect(x - 15, y - 15, width + 30, 40)
        self.dragging = False
        self.font = None
    
    def update(self, mouse_pos, mouse_down, mouse_click):
        # Track area for clicking
        track_rect = pygame.Rect(self.x, self.y - 10, self.width, 30)
        knob_x = self.x + int(self.width * self.value)
        knob_rect = pygame.Rect(knob_x - 15, self.y - 15, 30, 30)
        
        # Start dragging on click (on knob or track)
        if mouse_click:
            if track_rect.collidepoint(mouse_pos) or knob_rect.collidepoint(mouse_pos):
                self.dragging = True
                # Immediately update value on click
                new_value = (mouse_pos[0] - self.x) / self.width
                self.value = max(0.0, min(1.0, new_value))
        
        # Continue dragging while mouse is held
        if self.dragging:
            if mouse_down:
                new_value = (mouse_pos[0] - self.x) / self.width
                self.value = max(0.0, min(1.0, new_value))
            else:
                # Mouse released
                self.dragging = False
        
        return self.dragging
    
    def render(self, surface):
        if self.font is None:
            self.font = pygame.font.Font(None, 24)
        
        # Label
        label_surf = self.font.render(f"{self.label}: {int(self.value * 100)}%", True, COLORS["text"])
        surface.blit(label_surf, (self.x, self.y - 25))
        
        # Track
        track_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, COLORS["border"], track_rect, border_radius=5)
        
        # Fill
        fill_width = int(self.width * self.value)
        fill_rect = pygame.Rect(self.x, self.y, fill_width, self.height)
        pygame.draw.rect(surface, COLORS["accent"], fill_rect, border_radius=5)
        
        # Knob
        knob_x = self.x + fill_width
        pygame.draw.circle(surface, COLORS["text"], (knob_x, self.y + 5), 12)
        pygame.draw.circle(surface, COLORS["accent"], (knob_x, self.y + 5), 8)
        



class Dropdown:
    def __init__(self, x, y, width, options, default_idx=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = 40
        self.options = options
        self.selected_idx = default_idx
        self.is_open = False
        self.rect = pygame.Rect(x, y, width, self.height)
        self.font = None
    
    def update(self, mouse_pos, mouse_click, play_sound=None):
        if mouse_click:
            if self.is_open:
                # Check if clicked on an option
                for i, _ in enumerate(self.options):
                    opt_rect = pygame.Rect(self.x, self.y + (i + 1) * self.height, self.width, self.height)
                    if opt_rect.collidepoint(mouse_pos):
                        if play_sound: play_sound("click")
                        self.selected_idx = i
                        self.is_open = False
                        return True
                # Click outside closes
                if self.is_open: # Only if it was open
                     self.is_open = False
                     # Optional: Click outside close sound? No.
            elif self.rect.collidepoint(mouse_pos):
                if play_sound: play_sound("click")
                self.is_open = True
        return False
    
    def render(self, surface):
        if self.font is None:
            self.font = pygame.font.Font(None, 26)
        
        # Main box
        pygame.draw.rect(surface, COLORS["bg_card"], self.rect, border_radius=8)
        pygame.draw.rect(surface, COLORS["border"], self.rect, 2, border_radius=8)
        
        # Selected text
        if self.options:
            text = self.font.render(self.options[self.selected_idx], True, COLORS["text"])
            surface.blit(text, (self.x + 15, self.y + 10))
        
        # Arrow
        arrow = "▼" if not self.is_open else "▲"
        arrow_surf = self.font.render(arrow, True, COLORS["text_dim"])
        surface.blit(arrow_surf, (self.x + self.width - 30, self.y + 10))
        
        # Dropdown options
        if self.is_open:
            for i, opt in enumerate(self.options):
                opt_rect = pygame.Rect(self.x, self.y + (i + 1) * self.height, self.width, self.height)
                hovered = opt_rect.collidepoint(pygame.mouse.get_pos())
                
                color = COLORS["bg_hover"] if hovered else COLORS["bg_card"]
                pygame.draw.rect(surface, color, opt_rect)
                pygame.draw.rect(surface, COLORS["border"], opt_rect, 1)
                
                text = self.font.render(opt, True, COLORS["text"])
                surface.blit(text, (self.x + 15, opt_rect.y + 10))
                
                # DEBUG: Hitbox
                pygame.draw.rect(surface, (255, 0, 0), opt_rect, 1)
        
        # DEBUG: Hitbox
        pygame.draw.rect(surface, (255, 0, 0), self.rect, 1)

class Checkbox:
    def __init__(self, x, y, size, label, initial=False):
        self.rect = pygame.Rect(x, y, size, size)
        self.size = size
        self.label = label
        self.checked = initial
        self.font = None
    
    def update(self, mouse_pos, mouse_click, play_sound=None):
        if mouse_click and self.rect.collidepoint(mouse_pos):
            self.checked = not self.checked
            if play_sound: play_sound("click")
            return True
        return False
    
    def render(self, surface):
        if self.font is None:
            self.font = pygame.font.Font(None, 24)
            
        # Box
        pygame.draw.rect(surface, COLORS["bg_card"], self.rect, border_radius=4)
        pygame.draw.rect(surface, COLORS["border"], self.rect, 2, border_radius=4)
        
        # Check
        if self.checked:
            inner = self.rect.inflate(-8, -8)
            pygame.draw.rect(surface, COLORS["accent"], inner, border_radius=2)
            
        # Label
        label_surf = self.font.render(self.label, True, COLORS["text"])
        surface.blit(label_surf, (self.rect.right + 10, self.rect.y + (self.size - 24)//2 + 4))
        


    def get_selected(self):
        if self.options and 0 <= self.selected_idx < len(self.options):
            return self.options[self.selected_idx]
        return None

class ProgressionManager:
    """Handles the 'Shinobi Path' progression system including XP, Levels, and Ranks."""
    def __init__(self, username="Guest", network_manager=None):
        self.username = username
        self.network_manager = network_manager
        # Unique file per user if logged in
        safe_name = "".join(x for x in username if x.isalnum())
        self.file_path = Path(f"user_progression_{safe_name}.json")
        
        self.xp = 0
        self.level = 0
        self.rank = "Academy Student"
        self.stats = {
            "total_signs": 0,
            "total_jutsus": 0,
            "fastest_combo": 99.0
        }
        
        # Level requirements and Rank names
        self.RANKS = [
            (0, "Academy Student"),
            (5, "Genin Candidate"),
            (10, "Genin"),
            (25, "Chunin Candidate"),
            (50, "Chunin"),
            (100, "Special Jonin"),
            (250, "Jonin"),
            (500, "ANBU Black Ops"),
            (1000, "S-Rank Shinobi"),
            (2500, "Sanin"),
            (5000, "Hokage Candidate"),
            (10000, "HOKAGE")
        ]
        
        self.load()
        # If logged in (not Guest), try to fetch latest from cloud
        if self.username != "Guest" and self.network_manager:
            threading.Thread(target=self.sync_from_cloud, daemon=True).start()

    def sync_from_cloud(self):
        """Fetch latest XP and Level from Supabase."""
        if not self.network_manager: return
        profile = self.network_manager.get_profile(self.username)
        if profile:
            # Only update if cloud has MORE XP than local (prevents overwriting newer local progress)
            if profile.get("xp", 0) > self.xp:
                self.xp = profile["xp"]
                self.level = profile.get("level", 0)
                self.rank = profile.get("rank", "Academy Student")
                self.update_rank()
                self.save() # Update local cache
                print(f"[*] Cloud Sync Success: Restored Lv.{self.level} progression for {self.username}")
        else:
            # No cloud profile found -> This is a new user (or offline progress to sync up)
            print(f"[*] New cloud user: Creating profile for {self.username}")
            # We call the internal DB function directly to avoid spawning another thread from within this thread
            data = {
                "username": self.username,
                "xp": self.xp,
                "level": self.level,
                "rank": self.rank,
                "total_signs": self.stats["total_signs"],
                "total_jutsus": self.stats["total_jutsus"]
            }
            self.network_manager.upsert_profile(data)

    def sync_to_cloud(self):
        """Push current progression to Supabase."""
        if not self.network_manager or self.username == "Guest": return
        data = {
            "username": self.username,
            "xp": self.xp,
            "level": self.level,
            "rank": self.rank,
            "total_signs": self.stats["total_signs"],
            "total_jutsus": self.stats["total_jutsus"]
        }
        # Run in thread to not block UI
        threading.Thread(target=self.network_manager.upsert_profile, args=(data,), daemon=True).start()

    def get_xp_for_level(self, level):
        """Standard quadratic scaling."""
        if level <= 0: return 0
        return int(pow(level, 1.8) * 150) # Scale: L1=150, L5=2715...

    def get_next_level_xp(self):
        return self.get_xp_for_level(self.level + 1)

    def add_xp(self, amount):
        old_level = self.level
        self.xp += amount
        self.stats["total_jutsus"] += 1
        
        # Level up check
        while self.xp >= self.get_xp_for_level(self.level + 1):
            self.level += 1
            self.update_rank()
            
        is_level_up = self.level > old_level
        if is_level_up:
             print(f"[!] SHINOBI RANK UP: Level {self.level} - {self.rank}")
             
        self.save()
        self.sync_to_cloud() # Push update to DB
        return is_level_up

    def update_rank(self):
        for lv, name in reversed(self.RANKS):
            if self.level >= lv:
                self.rank = name
                break

    def save(self):
        try:
            data = {
                "xp": self.xp,
                "level": self.level,
                "rank": self.rank,
                "stats": self.stats
            }
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=4)
        except: pass

    def load(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                    self.xp = data.get("xp", 0)
                    self.level = data.get("level", 0)
                    self.rank = data.get("rank", "Academy Student")
                    self.stats = data.get("stats", self.stats)
                    self.update_rank()
            except: pass


# ═══════════════════════════════════════════════════════════════════════════
# GAME STATES
# ═══════════════════════════════════════════════════════════════════════════
class GameState:
    MENU = "menu"
    SETTINGS = "settings"
    PRACTICE_SELECT = "practice_select"
    LOADING = "loading"  # Loading screen while camera/models init
    PLAYING = "playing"
    PAUSED = "paused"
    ABOUT = "about"
    LOGIN_MODAL = "login_modal"  # Modal overlay for login prompt
    QUIT_CONFIRM = "quit_confirm" # Modal to confirm exit
    WELCOME_MODAL = "welcome_modal" # Modal to show after login success
    LOGOUT_CONFIRM = "logout_confirm" # Modal to confirm logout
    LOGOUT_CONFIRM = "logout_confirm" # Modal to confirm logout
    CONNECTION_LOST = "connection_lost" # Modal when internet drops
    LEADERBOARD = "leaderboard" # Leaderboard screen
    ERROR_MODAL = "error_modal" # Generic error modal (e.g. Camera fail)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════
class JutsuAcademy:
    def __init__(self):
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
    
    # ─── USER SESSION MANAGEMENT ───
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
    
    def _create_menu_ui(self):
        """Create main menu UI."""
        cx = SCREEN_WIDTH // 2
        btn_w, btn_h = 280, 60
        start_y = 380
        gap = 70
        
        self.menu_buttons = {
            "practice": Button(cx - btn_w // 2, start_y, btn_w, btn_h, "ENTER ACADEMY"),
            "settings": Button(cx - btn_w // 2, start_y + gap, btn_w, btn_h, "SETTINGS"),
            "about": Button(cx - btn_w // 2, start_y + gap * 2, btn_w, btn_h, "ABOUT", color=COLORS["bg_card"]),
            "quit": Button(cx - btn_w // 2, start_y + gap * 3, btn_w, btn_h, "QUIT", color=COLORS["error"]),
        }
        
        # Mute button position (top right)
        self.mute_button_rect = pygame.Rect(SCREEN_WIDTH - 60, 20, 40, 40)
    
    def _create_settings_ui(self):
        
        # Settings Page UI
        cx = SCREEN_WIDTH // 2
        cy = 180
        
        self.settings_sliders = {
            "music": Slider(cx - 150, cy + 40, 300, "Music Volume", self.settings["music_vol"]),
            "sfx": Slider(cx - 150, cy + 120, 300, "SFX Volume", self.settings["sfx_vol"]),
        }
        
        self.camera_dropdown = Dropdown(cx - 50, cy + 200, 200, self.cameras, self.settings["camera_idx"])
        
        self.settings_checkboxes = {
            "debug_hands": Checkbox(cx - 150, cy + 260, 24, "Show Hand Skeleton", self.settings["debug_hands"]),
            "use_mp": Checkbox(cx - 150, cy + 300, 24, "Use MediaPipe AI (Faster/Experimental)", self.settings["use_mediapipe_signs"]),
            "restricted": Checkbox(cx - 150, cy + 340, 24, "Restricted Signs (Require 2 Hands)", self.settings.get("restricted_signs", False)),
        }
        
        self.settings_buttons = {
            "back": Button(cx - 100, cy + 400, 200, 50, "SAVE & BACK"),
        }
    
    def _create_practice_select_ui(self):
        """Create practice mode selection UI."""
        cx = SCREEN_WIDTH // 2
        
        self.practice_buttons = {
            "freeplay": Button(cx - 150, 250, 300, 60, "FREE PLAY"),
            "challenge": Button(cx - 150, 330, 300, 60, "CHALLENGE"),
            "multiplayer": Button(cx - 150, 410, 300, 60, "MULTIPLAYER (LOCKED)", color=(40, 40, 40)),
            "leaderboard": Button(cx - 150, 490, 300, 50, "LEADERBOARD", color=(218, 165, 32)), # Gold
            "back": Button(cx - 100, 620, 200, 50, "BACK"),
        }
    
    def _create_about_ui(self):
        """Create about page UI."""
        cx = SCREEN_WIDTH // 2
        
        self.about_buttons = {
            "back": Button(cx - 100, 650, 200, 50, "BACK"),
        }
        
    def _create_leaderboard_ui(self):
        """Create leaderboard UI."""
        self.leaderboard_buttons = {
            "back": Button(50, 50, 100, 40, "< Back", font_size=20),
            "refresh": Button(SCREEN_WIDTH - 150, 50, 100, 40, "Refresh", font_size=20, color=COLORS["success"])
        }
    
    def _load_ml_models(self):
        """Load ML models (called when starting game)."""
        if self.model is not None:
            return True
        
        weights = get_latest_weights()
        if not weights:
            print("[-] No YOLO weights found!")
            return False
        
        print(f"[*] Loading YOLO: {weights}")
        self.model = YOLO(weights)
        self.class_names = get_class_names()
        
        # MediaPipe Face
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        face_path = Path("models/face_landmarker.task")
        if face_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(face_path))
                options = vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
                self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
                print("[+] Face detection loaded")
            except Exception as e:
                print(f"[!] Face detection failed: {e}")
        
        # MediaPipe Hands
        hand_path = Path("models/hand_landmarker.task")
        if hand_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(hand_path))
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=2,
                    running_mode=vision.RunningMode.VIDEO
                )
                self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
                print("[+] Hand tracking loaded")
            except Exception as e:
                print(f"[!] Hand tracking failed: {e}")
        
        return True
    
    def _start_camera(self):
        """Start camera capture."""
        if self.cap is not None:
            self.cap.release()
        
        cam_idx = self.settings["camera_idx"]
        # Use DirectShow on Windows for better compatibility
        if os.name == 'nt':
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(cam_idx)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        return self.cap.isOpened()
    
    def _stop_camera(self):
        """Stop camera capture."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def play_sound(self, name):
        """Play a sound effect."""
        if name in self.sounds:
            vol = self.settings["sfx_vol"]
            self.sounds[name].set_volume(vol)
            self.sounds[name].play()
    
    # ═══════════════════════════════════════════════════════════════════════
    # GAME LOGIC
    # ═══════════════════════════════════════════════════════════════════════
    def start_game(self, mode):
        """Start the game with specified mode."""
        self.game_mode = mode
        self.loading_message = "Initializing..."
        self.state = GameState.LOADING
        
        # Render loading screen immediately
        self._render_loading()
        pygame.display.flip()
        
        # Load models if not loaded
        self.loading_message = "Loading AI models..."
        self._render_loading()
        pygame.display.flip()
        
        if not self._load_ml_models():
            self.state = GameState.MENU
            return
        
        # Start camera
        self.loading_message = "Starting camera..."
        self._render_loading()
        pygame.display.flip()
        
        if not self._start_camera():
            print("[-] Failed to open camera!")
            # Show dedicated error modal
            self.error_title = "Camera Error"
            self.error_message = "Could not access camera.\nPlease check if OBS, Discord, or another app is using it."
            self.state = GameState.ERROR_MODAL 
            return
        
        # Reset state
        self.loading_message = "Ready!"
        self._render_loading()
        pygame.display.flip()
        
        self.current_jutsu_idx = 0
        self.sequence = self.jutsu_list[self.jutsu_names[0]]["sequence"]
        self.current_step = 0
        self.jutsu_active = False
        self.fire_particles.emitting = False
        
        # Challenge Mode Init
        self.challenge_state = "waiting"
        self.challenge_start_time = 0
        self.challenge_final_time = 0
        self.challenge_rank_info = ""
        self.challenge_submitting = False
        self.submission_complete = False
        
        self.state = GameState.PLAYING
    
    def _render_loading(self):
        """Render loading screen."""
        if hasattr(self, 'bg_image') and self.bg_image:
             self.screen.blit(self.bg_image, (0, 0))
             # Very dark overlay for loading state
             overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, 220)) 
             self.screen.blit(overlay, (0, 0))
        else:
             self.screen.fill(COLORS["bg_dark"])
        
        # Loading text
        title = self.fonts["title_md"].render("LOADING", True, COLORS["accent"])
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
        self.screen.blit(title, title_rect)
        
        # Status message
        msg = getattr(self, 'loading_message', 'Please wait...')
        status = self.fonts["body"].render(msg, True, COLORS["text"])
        status_rect = status.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(status, status_rect)
        
        # Simple spinner animation (dots)
        dots = "." * (int(time.time() * 2) % 4)
        dots_surf = self.fonts["body"].render(dots, True, COLORS["text_dim"])
        self.screen.blit(dots_surf, (status_rect.right + 5, status_rect.y))

    def _draw_text_center(self, text, y_offset=0, color=(255, 255, 255)):
        """Helper to draw centered text."""
        surf = self.fonts["title_md"].render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + y_offset))
        self.screen.blit(surf, rect)
    
    def stop_game(self):
        """Stop the game and return to menu."""
        self._stop_camera()
        self.fire_particles.emitting = False
        self.jutsu_active = False
        self.current_video = None
        if self.video_cap:
            self.video_cap.release()
            self.video_cap = None
        self.state = GameState.MENU
    
    def switch_jutsu(self, direction):
        """Switch to next/prev jutsu."""
        self.current_jutsu_idx = (self.current_jutsu_idx + direction) % len(self.jutsu_names)
        name = self.jutsu_names[self.current_jutsu_idx]
        self.sequence = self.jutsu_list[name]["sequence"]
        self.current_step = 0
        self.jutsu_active = False
        self.fire_particles.emitting = False
    
    def detect_and_process(self, frame):
        """Run detection and check sequence."""
        if self.model is None:
            return frame, None
        
        results = self.model(frame, stream=True, verbose=False, imgsz=320)
        detected_class = None
        highest_conf = 0.0
        self.hand_pos = None # Reset
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                cls_name = self.class_names[cls]
                
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                if conf > 0.5 and conf > highest_conf:
                    highest_conf = conf
                    detected_class = cls_name
                    # Store center
                    self.hand_pos = ((x1 + x2) // 2, (y1 + y2) // 2)
                
                # Draw bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{cls_name} {conf:.2f}", (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return frame, detected_class
    
    def detect_hands(self, frame):
        """Detect hand landmarks for skeleton visualization and tracking."""
        if not self.hand_landmarker:
            return
            
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            
            # Using current clock time for timestamp (MS)
            timestamp = int(time.time() * 1000)
            result = self.hand_landmarker.detect_for_video(mp_image, timestamp)
            
            if result.hand_landmarks:
                self.hand_lost_frames = 0
                h, w = frame.shape[:2]
                
                # 1. Primary Hand logic for effects (using the first hand)
                primary_landmarks = result.hand_landmarks[0]
                
                # Base Position (Centroid of Wrist + All Knuckles)
                indices = [0, 5, 9, 13, 17]
                base_x = sum(primary_landmarks[i].x for i in indices) / len(indices)
                base_y = sum(primary_landmarks[i].y for i in indices) / len(indices)

                # Palm Normal for offsetting effect
                def to_vec(landmarks, idx):
                    lm = landmarks[idx]
                    return np.array([lm.x, lm.y, lm.z])
                
                v1 = to_vec(primary_landmarks, 5) - to_vec(primary_landmarks, 0)
                v2 = to_vec(primary_landmarks, 17) - to_vec(primary_landmarks, 0)
                normal = np.cross(v1, v2)
                mag = np.linalg.norm(normal)
                if mag > 1e-6: normal /= mag
                
                offset_strength = 0.25
                if result.handedness:
                    label = result.handedness[0][0].category_name
                    if label == "Left": offset_strength = -0.25

                target_x = (base_x + normal[0] * offset_strength) * w
                target_y = (base_y + normal[1] * offset_strength) * h
                
                # Temporal Smoothing
                if self.smooth_hand_pos is None:
                    self.smooth_hand_pos = (target_x, target_y)
                else:
                    alpha = 0.08 
                    curr_x, curr_y = self.smooth_hand_pos
                    self.smooth_hand_pos = (curr_x + (target_x - curr_x) * alpha, 
                                            curr_y + (target_y - curr_y) * alpha)
                
                self.hand_pos = self.smooth_hand_pos
                self.last_mp_result = result
                
                # 2. Draw Skeletons for ALL detected hands
                if self.settings.get("debug_hands", False):
                    CONNECTIONS = [
                        (0,1), (1,2), (2,3), (3,4), # Thumb
                        (0,5), (5,6), (6,7), (7,8), # Index
                        (5,9), (9,10), (10,11), (11,12), # Middle
                        (9,13), (13,14), (14,15), (15,16), # Ring
                        (13,17), (17,18), (18,19), (19,20), (0,17) # Pinky + Palm
                    ]
                    
                    for hand_idx, landmarks in enumerate(result.hand_landmarks):
                        # Use different color for second hand if desired (optional)
                        color = (0, 255, 0) # Primary Green
                        
                        for lm in landmarks:
                            cx, cy = int(lm.x * w), int(lm.y * h)
                            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
                            cv2.circle(frame, (cx, cy), 1, (255, 255, 255), -1)
                        
                        for conn in CONNECTIONS:
                            p1, p2 = landmarks[conn[0]], landmarks[conn[1]]
                            cv2.line(frame, (int(p1.x * w), int(p1.y * h)), 
                                            (int(p2.x * w), int(p2.y * h)), color, 2)
            else:
                self.hand_lost_frames += 1
                # Increase hold time to 30 frames (~1 sec at 30fps)
                if self.hand_lost_frames < 30:
                    # Keep previous smooth position as current output
                    self.hand_pos = self.smooth_hand_pos
                else:
                    # Truly lost, allow fallback to center
                    self.hand_pos = None
                    self.smooth_hand_pos = None
        except Exception as e:
            print(f"[!] detect_hands error: {e}")

    def detect_face(self, frame):
        """Detect face landmarks for fire positioning."""
        if not self.face_landmarker:
            return
        
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.face_landmarker.detect(mp_image)
            
            if result.face_landmarks:
                face = result.face_landmarks[0]
                h, w = frame.shape[:2]
                
                mouth = face[13]
                self.mouth_pos = (int(mouth.x * w), int(mouth.y * h))
                
                nose_x = face[1].x
                left_x = face[234].x
                right_x = face[454].x
                width = right_x - left_x
                if width > 0:
                    rel_nose = (nose_x - left_x) / width
                    self.head_yaw = (rel_nose - 0.5) * 2
        except:
            pass
    
    def cv2_to_pygame(self, frame):
        """Convert OpenCV frame to Pygame surface."""
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = np.flipud(frame)
        return pygame.surfarray.make_surface(frame)
    
    # ═══════════════════════════════════════════════════════════════════════
    # RENDER METHODS
    # ═══════════════════════════════════════════════════════════════════════
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

        # XP Label
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
                

    
    # ─── Challenge Mode Helpers ───
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
                            
                            is_lv_up = self.progression.add_xp(total_xp)
                            
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
        
        # Check jutsu duration
        if self.jutsu_active:
            if time.time() - self.jutsu_start_time > self.jutsu_duration:
                self.jutsu_active = False
                self.fire_particles.emitting = False
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
    
    # ═══════════════════════════════════════════════════════════════════════
    # UPDATE LOOP
    # ═══════════════════════════════════════════════════════════════════════
    def handle_events(self):
        """Handle pygame events."""
        mouse_click = False
        
        # Capture events first
        events = pygame.event.get()
        
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
                    elif self.state in [GameState.SETTINGS, GameState.ABOUT, GameState.PRACTICE_SELECT]:
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
                        self.state = GameState.SETTINGS
                    elif name == "about":
                        self.state = GameState.ABOUT
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
                    pygame.mixer.music.set_volume(self.settings_sliders["music"].value)
            
            self.camera_dropdown.update(mouse_pos, mouse_click, self.play_sound)
            
            for name, cb in self.settings_checkboxes.items():
                 cb.update(mouse_pos, mouse_click, self.play_sound)
            
            for name, btn in self.settings_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "back":
                        # Save settings
                        self.settings["music_vol"] = self.settings_sliders["music"].value
                        self.settings["sfx_vol"] = self.settings_sliders["sfx"].value
                        self.settings["camera_idx"] = self.camera_dropdown.selected_idx
                        self.settings["debug_hands"] = self.settings_checkboxes["debug_hands"].checked
                        self.settings["use_mediapipe_signs"] = self.settings_checkboxes["use_mp"].checked
                        self.settings["restricted_signs"] = self.settings_checkboxes["restricted"].checked
                        
                        if not self.is_muted:
                            pygame.mixer.music.set_volume(self.settings["music_vol"])
                        self.save_settings()
                        self.state = GameState.MENU
        
        elif self.state == GameState.PRACTICE_SELECT:
            for name, btn in self.practice_buttons.items():
                if btn.update(mouse_pos, mouse_click, mouse_down, self.play_sound):
                    if name == "freeplay":
                        self.start_game("practice")
                    elif name == "challenge":
                        self.start_game("challenge")
                    elif name == "multiplayer":
                        self.play_sound("click")
                        print("[*] Multiplayer is currently locked.")
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
        
        elif self.state == GameState.PLAYING:
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
            
            pygame.display.flip()
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self._stop_camera()
        pygame.quit()
        print("[*] Jutsu Academy closed.")


def main():
    app = JutsuAcademy()
    app.run()


if __name__ == "__main__":
    main()
