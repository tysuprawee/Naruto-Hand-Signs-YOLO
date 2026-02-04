#!/usr/bin/env python3
"""
Jutsu Academy - Pygame Edition
==============================
A Pygame-based UI for the Jutsu Trainer with:
- Modern button/slider UI
- Particle effects for fire/lightning
- Smooth animations
- Better visual design

Usage:
    python src/jutsu_trainer_pygame.py
"""

import cv2
import time
import math
import argparse
from pathlib import Path
import numpy as np
import pygame
from pygame import gfxdraw
import sys

# Add parent path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))
from ultralytics import YOLO
import mediapipe as mp

from src.utils.paths import get_class_names, get_latest_weights
from src.jutsu_registry import OFFICIAL_JUTSUS


# ═══════════════════════════════════════════════════════════════════════════
# COLORS (Modern Dark Theme)
# ═══════════════════════════════════════════════════════════════════════════
COLORS = {
    "bg_dark": (18, 18, 24),
    "bg_panel": (28, 28, 38),
    "bg_card": (38, 38, 52),
    "accent": (255, 120, 50),      # Orange
    "accent_hover": (255, 150, 80),
    "success": (50, 200, 120),
    "text": (240, 240, 245),
    "text_dim": (140, 140, 160),
    "border": (60, 60, 80),
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
        # Add turbulence
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
            
            # Random spread
            angle = np.random.uniform(-0.5, 0.5)
            speed = np.random.uniform(100, 200)
            
            vx = speed * math.sin(angle) * 0.3
            vy = -speed  # Upward
            
            lifetime = np.random.uniform(0.5, 1.2)
            size = np.random.uniform(8, 25)
            
            # Color based on temperature (hotter = whiter)
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
        # Update existing particles
        for p in self.particles:
            p.update(dt, self.wind_x)
        
        # Remove dead particles
        self.particles = [p for p in self.particles if p.is_alive()]
        
        # Emit new particles
        if self.emitting:
            self.emit(8)
    
    def render(self, surface):
        for p in self.particles:
            alpha = p.get_alpha()
            life_ratio = p.lifetime / p.max_lifetime
            size = int(p.size * life_ratio)
            
            if size < 2:
                continue
            
            # Create a soft glow effect
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
    def __init__(self, x, y, width, height, text, callback=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.font = pygame.font.Font(None, 24)
    
    def update(self, mouse_pos, mouse_click):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered and mouse_click and self.callback:
            self.callback()
    
    def render(self, surface):
        color = COLORS["accent_hover"] if self.hovered else COLORS["accent"]
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        
        text_surf = self.font.render(self.text, True, COLORS["text"])
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class Toggle:
    def __init__(self, x, y, label, initial=True, callback=None):
        self.x = x
        self.y = y
        self.label = label
        self.value = initial
        self.callback = callback
        self.width = 50
        self.height = 26
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.font = pygame.font.Font(None, 22)
    
    def update(self, mouse_pos, mouse_click):
        if self.rect.collidepoint(mouse_pos) and mouse_click:
            self.value = not self.value
            if self.callback:
                self.callback(self.value)
    
    def render(self, surface):
        # Label
        label_surf = self.font.render(self.label, True, COLORS["text"])
        surface.blit(label_surf, (self.x - label_surf.get_width() - 10, self.y + 4))
        
        # Track
        track_color = COLORS["success"] if self.value else COLORS["border"]
        pygame.draw.rect(surface, track_color, self.rect, border_radius=13)
        
        # Knob
        knob_x = self.x + (self.width - 22) if self.value else self.x + 4
        pygame.draw.circle(surface, COLORS["text"], (knob_x + 9, self.y + 13), 9)


class Slider:
    def __init__(self, x, y, width, label, initial=0.7, callback=None):
        self.x = x
        self.y = y
        self.width = width
        self.label = label
        self.value = initial
        self.callback = callback
        self.height = 8
        self.rect = pygame.Rect(x, y, width, self.height)
        self.dragging = False
        self.font = pygame.font.Font(None, 22)
    
    def update(self, mouse_pos, mouse_down, mouse_click):
        if self.rect.collidepoint(mouse_pos) and mouse_click:
            self.dragging = True
        
        if not mouse_down:
            self.dragging = False
        
        if self.dragging:
            new_value = (mouse_pos[0] - self.x) / self.width
            self.value = max(0.0, min(1.0, new_value))
            if self.callback:
                self.callback(self.value)
    
    def render(self, surface):
        # Label
        label_surf = self.font.render(f"{self.label}: {int(self.value * 100)}%", True, COLORS["text_dim"])
        surface.blit(label_surf, (self.x, self.y - 18))
        
        # Track
        pygame.draw.rect(surface, COLORS["border"], self.rect, border_radius=4)
        
        # Fill
        fill_width = int(self.width * self.value)
        fill_rect = pygame.Rect(self.x, self.y, fill_width, self.height)
        pygame.draw.rect(surface, COLORS["accent"], fill_rect, border_radius=4)
        
        # Knob
        knob_x = self.x + fill_width
        pygame.draw.circle(surface, COLORS["text"], (knob_x, self.y + 4), 10)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN TRAINER CLASS
# ═══════════════════════════════════════════════════════════════════════════
class JutsuTrainerPygame:
    def __init__(self, model_path, camera_index=0):
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption("Jutsu Academy - Pygame Edition")
        
        # Window setup
        self.cam_width = 640
        self.cam_height = 480
        self.panel_height = 140
        self.screen_width = self.cam_width
        self.screen_height = self.cam_height + self.panel_height
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.clock = pygame.time.Clock()
        
        # Load YOLO
        print(f"[*] Loading YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        self.class_names = get_class_names()
        
        # Initialize MediaPipe Face
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        self.face_landmarker = None
        face_model_path = Path("models/face_landmarker.task")
        if face_model_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(face_model_path))
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    num_faces=1
                )
                self.face_landmarker = vision.FaceLandmarker.create_from_options(options)
                print("[+] Face detection: MediaPipe")
            except Exception as e:
                print(f"[!] Face detection failed: {e}")
        
        # Initialize MediaPipe Hands
        self.hand_landmarker = None
        hand_model_path = Path("models/hand_landmarker.task")
        self.last_mp_timestamp = 0
        if hand_model_path.exists():
            try:
                base_options = python.BaseOptions(model_asset_path=str(hand_model_path))
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=1,
                    running_mode=vision.RunningMode.VIDEO
                )
                self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
                print("[+] Hand tracking: MediaPipe")
            except Exception as e:
                print(f"[!] Hand tracking failed: {e}")
        
        # Camera
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Jutsu state
        self.jutsu_list = OFFICIAL_JUTSUS.copy()
        self.jutsu_names = list(self.jutsu_list.keys())
        self.current_jutsu_idx = 0
        self.sequence = self.jutsu_list[self.jutsu_names[0]]["sequence"]
        self.current_step = 0
        self.last_sign_time = 0
        self.cooldown = 0.5
        self.jutsu_active = False
        self.jutsu_start_time = 0
        self.jutsu_duration = 5.0
        
        # Particle systems
        self.fire_particles = FireParticleSystem(max_particles=200)
        
        # Tracking data
        self.mouth_pos = None
        self.hand_pos = None
        self.head_yaw = 0
        
        # Load icons
        self.icons = {}
        self._load_icons()
        
        # Sound setup
        pygame.mixer.init()
        self.sounds = {}
        self._load_sounds()
        
        # Volume settings
        self.vol_master = 0.7
        self.vol_each = 1.0
        self.vol_complete = 0.7
        self.vol_signature = 0.7
        
        # UI State
        self.show_settings = False
        self.show_bbox = True
        self.show_effects = True
        
        # Create UI elements
        self._create_ui()
        
        # FPS tracking
        self.fps = 0
        self.frame_count = 0
        self.fps_timer = time.time()
        
        print("[+] Pygame Jutsu Trainer initialized!")
    
    def _load_icons(self):
        """Load hand sign icons."""
        pics_dir = Path("src/pics")
        for name in self.class_names:
            for ext in [".jpeg", ".jpg", ".png"]:
                path = pics_dir / f"{name}{ext}"
                if path.exists():
                    try:
                        img = pygame.image.load(str(path))
                        self.icons[name] = pygame.transform.scale(img, (70, 70))
                        break
                    except:
                        pass
    
    def _load_sounds(self):
        """Load sound effects."""
        sounds_dir = Path("src/sounds")
        
        if (sounds_dir / "each.mp3").exists():
            self.sounds["each"] = pygame.mixer.Sound(str(sounds_dir / "each.mp3"))
        
        if (sounds_dir / "complete.mp3").exists():
            self.sounds["complete"] = pygame.mixer.Sound(str(sounds_dir / "complete.mp3"))
        
        # Load per-jutsu sounds
        for name, data in self.jutsu_list.items():
            sound_path = data.get("sound_path")
            if sound_path and Path(sound_path).exists():
                self.sounds[name] = pygame.mixer.Sound(sound_path)
    
    def _create_ui(self):
        """Create UI elements."""
        self.toggles = []
        self.sliders = []
        self.buttons = []
        
        # Settings will be created dynamically when shown
    
    def play_sound(self, sound_type):
        """Play sound with volume control."""
        if sound_type == "each" and "each" in self.sounds:
            self.sounds["each"].set_volume(self.vol_master * self.vol_each)
            self.sounds["each"].play()
        elif sound_type == "complete" and "complete" in self.sounds:
            self.sounds["complete"].set_volume(self.vol_master * self.vol_complete)
            self.sounds["complete"].play()
        elif sound_type == "signature":
            jutsu_name = self.jutsu_names[self.current_jutsu_idx]
            if jutsu_name in self.sounds:
                self.sounds[jutsu_name].set_volume(self.vol_master * self.vol_signature)
                self.sounds[jutsu_name].play()
    
    def detect_hands_yolo(self, frame):
        """Run YOLO detection."""
        results = self.model(frame, stream=True, verbose=False, imgsz=320)
        detected_class = None
        highest_conf = 0.0
        
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                cls_name = self.class_names[cls]
                
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                self.hand_pos = (cx, cy)
                
                if conf > 0.5 and conf > highest_conf:
                    highest_conf = conf
                    detected_class = cls_name
                
                # Draw bbox on frame if enabled
                if self.show_bbox:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"{cls_name} {conf:.2f}", (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame, detected_class
    
    def detect_face(self, frame):
        """Run face detection for fire positioning."""
        if not self.face_landmarker:
            return
        
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.face_landmarker.detect(mp_image)
            
            if result.face_landmarks:
                face = result.face_landmarks[0]
                h, w = frame.shape[:2]
                
                # Mouth position
                mouth = face[13]
                self.mouth_pos = (int(mouth.x * w), int(mouth.y * h))
                
                # Head yaw for wind direction
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
        # Frame should already be flipped before detection
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = np.flipud(frame)
        return pygame.surfarray.make_surface(frame)
    
    def render_icon_bar(self, surface, y_offset):
        """Render the icon bar showing jutsu sequence."""
        panel = pygame.Surface((self.cam_width, self.panel_height), pygame.SRCALPHA)
        panel.fill(COLORS["bg_panel"])
        
        # Draw sequence icons
        icon_size = 70
        gap = 10
        n_signs = len(self.sequence)
        total_width = n_signs * (icon_size + gap) - gap
        start_x = (self.cam_width - total_width) // 2
        y = 35
        
        for i, sign_name in enumerate(self.sequence):
            x = start_x + i * (icon_size + gap)
            
            # Background
            if i < self.current_step:
                # Completed
                pygame.draw.rect(panel, COLORS["success"], (x - 3, y - 3, icon_size + 6, icon_size + 6), border_radius=8)
            elif i == self.current_step and not self.jutsu_active:
                # Current target
                pygame.draw.rect(panel, COLORS["accent"], (x - 4, y - 4, icon_size + 8, icon_size + 8), border_radius=8)
            
            # Icon
            if sign_name in self.icons:
                icon = self.icons[sign_name].copy()
                if i < self.current_step:
                    # Dim completed icons
                    icon.set_alpha(100)
                panel.blit(icon, (x, y))
            else:
                pygame.draw.rect(panel, COLORS["border"], (x, y, icon_size, icon_size), border_radius=8)
        
        # Status text
        font = pygame.font.Font(None, 32)
        if self.jutsu_active:
            jutsu_name = self.jutsu_names[self.current_jutsu_idx]
            display_text = self.jutsu_list[jutsu_name].get("display_text", jutsu_name)
            text = font.render(display_text, True, COLORS["accent"])
        else:
            target = self.sequence[self.current_step] if self.current_step < len(self.sequence) else ""
            text = font.render(f"Next: {target.upper()}", True, COLORS["text"])
        
        text_rect = text.get_rect(center=(self.cam_width // 2, 20))
        panel.blit(text, text_rect)
        
        surface.blit(panel, (0, y_offset))
    
    def render_settings(self, surface):
        """Render settings overlay."""
        if not self.show_settings:
            return
        
        # Semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Panel
        panel_w, panel_h = 350, 400
        panel_x = (self.screen_width - panel_w) // 2
        panel_y = (self.screen_height - panel_h) // 2
        
        pygame.draw.rect(surface, COLORS["bg_card"], (panel_x, panel_y, panel_w, panel_h), border_radius=16)
        pygame.draw.rect(surface, COLORS["border"], (panel_x, panel_y, panel_w, panel_h), 2, border_radius=16)
        
        # Title
        font_title = pygame.font.Font(None, 36)
        title = font_title.render("SETTINGS", True, COLORS["text"])
        surface.blit(title, (panel_x + panel_w // 2 - title.get_width() // 2, panel_y + 20))
        
        # Close button (X)
        close_btn = pygame.Rect(panel_x + panel_w - 40, panel_y + 10, 30, 30)
        pygame.draw.rect(surface, COLORS["accent"], close_btn, border_radius=6)
        font_x = pygame.font.Font(None, 28)
        x_text = font_x.render("X", True, COLORS["text"])
        surface.blit(x_text, (close_btn.x + 10, close_btn.y + 5))
        
        # Instructions
        font_small = pygame.font.Font(None, 22)
        inst = font_small.render("Press ESC or click X to close", True, COLORS["text_dim"])
        surface.blit(inst, (panel_x + 20, panel_y + panel_h - 30))
    
    def run(self):
        """Main game loop."""
        running = True
        mouse_click = False
        
        while running:
            dt = self.clock.tick(60) / 1000.0  # Delta time in seconds
            mouse_pos = pygame.mouse.get_pos()
            mouse_down = pygame.mouse.get_pressed()[0]
            mouse_click = False
            
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_r:
                        self.current_step = 0
                        self.jutsu_active = False
                    elif event.key == pygame.K_ESCAPE:
                        self.show_settings = not self.show_settings
                    elif event.key == pygame.K_LEFT:
                        self.current_jutsu_idx = (self.current_jutsu_idx - 1) % len(self.jutsu_names)
                        self._switch_jutsu()
                    elif event.key == pygame.K_RIGHT:
                        self.current_jutsu_idx = (self.current_jutsu_idx + 1) % len(self.jutsu_names)
                        self._switch_jutsu()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_click = True
            
            # Capture frame
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Flip frame FIRST (mirror for selfie view)
            frame = cv2.flip(frame, 1)
            
            # Detection (on already-flipped frame so labels are correct)
            if not self.jutsu_active:
                frame, detected_class = self.detect_hands_yolo(frame)
                
                # Sequence logic
                if self.current_step < len(self.sequence):
                    target = self.sequence[self.current_step]
                    if detected_class == target:
                        now = time.time()
                        if now - self.last_sign_time > self.cooldown:
                            print(f"[+] Correct: {detected_class}")
                            self.current_step += 1
                            self.last_sign_time = now
                            self.play_sound("each")
                            
                            if self.current_step >= len(self.sequence):
                                print("[!!!] JUTSU ACTIVATED [!!!]")
                                self.jutsu_active = True
                                self.jutsu_start_time = time.time()
                                self.current_step = 0
                                self.play_sound("complete")
                                
                                # Activate fire
                                effect = self.jutsu_list[self.jutsu_names[self.current_jutsu_idx]]["effect"]
                                if effect == "fire":
                                    self.fire_particles.emitting = True
            
            # Face detection for effect positioning
            self.detect_face(frame)
            
            # Update particles (mirror x position since frame was flipped)
            if self.fire_particles.emitting and self.mouth_pos:
                # Mouth pos is already in flipped coordinates, use directly
                self.fire_particles.set_position(self.mouth_pos[0], self.mouth_pos[1])
                # Invert wind direction since we flipped
                self.fire_particles.wind_x = -self.head_yaw * 200
            self.fire_particles.update(dt)
            
            # Check jutsu duration
            if self.jutsu_active:
                if time.time() - self.jutsu_start_time > self.jutsu_duration:
                    self.jutsu_active = False
                    self.fire_particles.emitting = False
            
            # Render
            self.screen.fill(COLORS["bg_dark"])
            
            # Camera feed
            cam_surface = self.cv2_to_pygame(frame)
            self.screen.blit(cam_surface, (0, 0))
            
            # Fire particles (on top of camera)
            if self.show_effects:
                self.fire_particles.render(self.screen)
            
            # Icon bar
            self.render_icon_bar(self.screen, self.cam_height)
            
            # FPS counter
            self.frame_count += 1
            if time.time() - self.fps_timer >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.fps_timer = time.time()
            
            font = pygame.font.Font(None, 28)
            fps_text = font.render(f"FPS: {self.fps}", True, COLORS["success"])
            self.screen.blit(fps_text, (10, 10))
            
            # Jutsu name
            jutsu_text = font.render(self.jutsu_names[self.current_jutsu_idx], True, COLORS["accent"])
            self.screen.blit(jutsu_text, (self.cam_width - jutsu_text.get_width() - 10, 10))
            
            # Settings overlay
            self.render_settings(self.screen)
            
            pygame.display.flip()
        
        self.cleanup()
    
    def _switch_jutsu(self):
        """Switch to current jutsu."""
        name = self.jutsu_names[self.current_jutsu_idx]
        self.sequence = self.jutsu_list[name]["sequence"]
        self.current_step = 0
        self.jutsu_active = False
        self.fire_particles.emitting = False
        print(f"[*] Switched to: {name}")
    
    def cleanup(self):
        """Clean up resources."""
        self.cap.release()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default=None, help="Path to YOLO weights")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    args = parser.parse_args()
    
    weights = args.weights or get_latest_weights()
    if not weights:
        print("[-] No weights found. Train model first.")
        sys.exit(1)
    
    trainer = JutsuTrainerPygame(weights, camera_index=args.camera)
    trainer.run()


if __name__ == "__main__":
    main()
