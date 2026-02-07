import math
import time
import random
import pygame


class ShadowClone:
    def __init__(self, x, y, vx, vy, lifetime=0.9, scale=1.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.lifetime = float(lifetime)
        self.max_lifetime = float(lifetime)
        self.scale = float(scale)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        # tiny wobble so it feels alive
        self.x += math.sin(time.time() * 8 + self.y * 0.01) * 25 * dt

    def alive(self):
        return self.lifetime > 0

    def alpha(self):
        t = max(0.0, min(1.0, self.lifetime / self.max_lifetime))
        return int(255 * t)

    def render(self, surface):
        a = self.alpha()
        if a <= 0:
            return

        w = int(42 * self.scale)
        h = int(78 * self.scale)

        clone = pygame.Surface((w * 2, h * 2), pygame.SRCALPHA)

        body_col = (120, 190, 255, min(210, a))
        edge_col = (200, 240, 255, min(180, a))

        cx = w
        cy = h

        # glow
        pygame.draw.ellipse(
            clone,
            (120, 190, 255, max(0, a - 170)),
            (cx - w - 6, cy - h - 6, (w * 2) + 12, (h * 2) + 12),
        )

        # head
        pygame.draw.circle(clone, body_col, (cx, cy - int(h * 0.55)), int(14 * self.scale))
        pygame.draw.circle(clone, edge_col, (cx, cy - int(h * 0.55)), int(14 * self.scale), 2)

        # torso
        torso_rect = pygame.Rect(0, 0, int(34 * self.scale), int(38 * self.scale))
        torso_rect.center = (cx, cy - int(h * 0.15))
        pygame.draw.rect(clone, body_col, torso_rect, border_radius=int(10 * self.scale))
        pygame.draw.rect(clone, edge_col, torso_rect, 2, border_radius=int(10 * self.scale))

        # legs
        leg_w = int(12 * self.scale)
        leg_h = int(28 * self.scale)
        left_leg = pygame.Rect(cx - leg_w - int(4 * self.scale), cy + int(h * 0.15), leg_w, leg_h)
        right_leg = pygame.Rect(cx + int(4 * self.scale), cy + int(h * 0.15), leg_w, leg_h)
        pygame.draw.rect(clone, body_col, left_leg, border_radius=int(6 * self.scale))
        pygame.draw.rect(clone, body_col, right_leg, border_radius=int(6 * self.scale))

        # fade at bottom
        fade = pygame.Surface((w * 2, h), pygame.SRCALPHA)
        for yy in range(h):
            aa = int(a * (1.0 - yy / max(1, h)))
            pygame.draw.line(fade, (0, 0, 0, 255 - aa), (0, yy), (w * 2, yy))
        clone.blit(fade, (0, h), special_flags=pygame.BLEND_RGBA_SUB)

        surface.blit(clone, (int(self.x - cx), int(self.y - cy)))


class ShadowCloneSystem:
    """
    Owns:
      - clone particles
      - debug anchors (FACE/MOUTH/HAND/BODY) with labeled points
      - jutsu/sign triggers

    IMPORTANT:
      Your cv2_to_pygame uses rot90 + flipud, which swaps x/y:
        display_x = frame_y
        display_y = frame_x
      This system assumes that transform by default (swap_xy=True).
    """

    SHADOW_CLONE_JUTSU_NAMES = {"shadow_clone", "shadowclone", "kage_bunshin", "kagebunshin", "shadow clone"}
    SHADOW_CLONE_SIGN_NAMES  = {"shadow_clone", "shadowclone", "kage_bunshin", "kagebunshin", "shadow clone"}

    def __init__(self, *, swap_xy=True):
        self.swap_xy = swap_xy

        self.shadow_clones = []
        self.clone_cooldown = 0.35
        self.last_clone_time = 0.0

        self.prev_detected_sign = None

        # Anchors in FRAME pixel coords
        self.face_center = None
        self.mouth_pos = None
        self.hand_pos = None

        # Body in SCREEN coords (computed by caller each frame)
        self.body_pos_screen = None

    # --------------------------
    # Coordinate transforms
    # --------------------------
    def frame_px_to_display_px(self, fx, fy):
        """Map original frame pixel coords -> displayed camera-surface pixel coords."""
        if self.swap_xy:
            return (int(fy), int(fx))
        return (int(fx), int(fy))

    def display_px_to_screen_px(self, dx, dy, cam_x, cam_y, scale_x, scale_y):
        """Map displayed camera-surface px -> screen px."""
        return (cam_x + int(dx * scale_x), cam_y + int(dy * scale_y))

    def frame_px_to_screen_px(self, fx, fy, cam_x, cam_y, scale_x, scale_y):
        dx, dy = self.frame_px_to_display_px(fx, fy)
        return self.display_px_to_screen_px(dx, dy, cam_x, cam_y, scale_x, scale_y)

    # --------------------------
    # Anchors / body estimate
    # --------------------------
    def set_anchors(self, *, face_center=None, mouth_pos=None, hand_pos=None):
        if face_center is not None:
            self.face_center = face_center
        if mouth_pos is not None:
            self.mouth_pos = mouth_pos
        if hand_pos is not None:
            self.hand_pos = hand_pos

    def estimate_body_screen_pos(self, frame_shape, cam_x, cam_y, scale_x, scale_y):
        """
        Uses face_center when available, drops down ~30% frame height.
        Returns SCREEN coords.
        """
        h, w = frame_shape[:2]

        if self.face_center:
            fx, fy = self.face_center
            bx = fx
            by = int(fy + 0.30 * h)
        else:
            bx = w // 2
            by = int(h * 0.65)

        sx, sy = self.frame_px_to_screen_px(bx, by, cam_x, cam_y, scale_x, scale_y)
        self.body_pos_screen = (sx, sy)
        return self.body_pos_screen

    # --------------------------
    # Spawn triggers
    # --------------------------
    def spawn_shadow_clones(self, count=6):
        now = time.time()
        if now - self.last_clone_time < self.clone_cooldown:
            return
        self.last_clone_time = now

        x, y = self.body_pos_screen if self.body_pos_screen else (512, 384)

        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(220, 380)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd * 0.65
            life = random.uniform(0.6, 1.05)
            sc = random.uniform(0.85, 1.2)
            self.shadow_clones.append(ShadowClone(x, y, vx, vy, lifetime=life, scale=sc))

    def maybe_spawn_from_jutsu(self, jutsu_name):
        name = (jutsu_name or "").lower().strip()
        if name in self.SHADOW_CLONE_JUTSU_NAMES:
            self.spawn_shadow_clones(count=6)

    def maybe_spawn_from_sign(self, detected_sign):
        if not detected_sign:
            self.prev_detected_sign = None
            return

        s = str(detected_sign).lower().strip()
        if s in self.SHADOW_CLONE_SIGN_NAMES and self.prev_detected_sign != s:
            self.spawn_shadow_clones(count=6)

        self.prev_detected_sign = s

    # --------------------------
    # Update / render
    # --------------------------
    def update(self, dt):
        if not self.shadow_clones:
            return
        for c in self.shadow_clones:
            c.update(dt)
        self.shadow_clones = [c for c in self.shadow_clones if c.alive()]

    def render(self, screen):
        for c in self.shadow_clones:
            c.render(screen)

    # --------------------------
    # Debug anchors
    # --------------------------
    def _draw_labeled_point(self, screen, sx, sy, label, font, color=(255, 255, 255), r=6, y_off=-18):
        pygame.draw.circle(screen, color, (int(sx), int(sy)), r)
        pygame.draw.circle(screen, (0, 0, 0), (int(sx), int(sy)), r + 2, 2)

        txt = font.render(label, True, color)
        pad = 4
        bg = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad * 2), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (int(sx) + 10, int(sy) + y_off))
        screen.blit(txt, (int(sx) + 10 + pad, int(sy) + y_off + pad))

    def debug_draw_anchors(self, *, screen, font, frame_shape, cam_x, cam_y, scale_x, scale_y, enabled=False):
        """
        Call AFTER you blit the scaled camera to screen.
        scale_x/scale_y must match how you scaled the camera surface to the screen.
        """
        if not enabled:
            return

        # camera origin marker (screen-space)
        self._draw_labeled_point(
            screen, cam_x, cam_y,
            f"CAM ORIGIN (sx={cam_x}, sy={cam_y})",
            font, color=(180, 180, 180), r=4, y_off=-22
        )

        # face
        if self.face_center:
            fx, fy = self.face_center
            sx, sy = self.frame_px_to_screen_px(fx, fy, cam_x, cam_y, scale_x, scale_y)
            self._draw_labeled_point(
                screen, sx, sy,
                f"FACE frame({fx},{fy}) -> screen({sx},{sy})",
                font, color=(255, 200, 80)
            )

        # mouth
        if self.mouth_pos:
            mx, my = self.mouth_pos
            sx, sy = self.frame_px_to_screen_px(mx, my, cam_x, cam_y, scale_x, scale_y)
            self._draw_labeled_point(
                screen, sx, sy,
                f"MOUTH frame({mx},{my}) -> screen({sx},{sy})",
                font, color=(255, 120, 120)
            )

        # hand
        if self.hand_pos:
            hx, hy = self.hand_pos
            sx, sy = self.frame_px_to_screen_px(hx, hy, cam_x, cam_y, scale_x, scale_y)
            self._draw_labeled_point(
                screen, sx, sy,
                f"HAND frame({int(hx)},{int(hy)}) -> screen({sx},{sy})",
                font, color=(120, 255, 120)
            )

        # body (screen-space already)
        if self.body_pos_screen:
            bx, by = self.body_pos_screen
            self._draw_labeled_point(
                screen, bx, by,
                f"BODY screen({bx},{by})",
                font, color=(120, 190, 255), r=7, y_off=-26
            )
