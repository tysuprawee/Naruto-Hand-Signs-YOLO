import time
import random
from dataclasses import dataclass
import cv2
import numpy as np

@dataclass
class Burn:
    x: float
    y: float
    h: float
    w: float
    speed: float
    heat: bool

class FireEffect:
    def __init__(self, fire_size=400, burn_count=40):
        self.fire_size = fire_size
        self.burn_count = burn_count
        self.burn_size = 100  # Relative to fire size roughly
        
        # Style params
        self.blur_px = 20
        self.contrast = 30.0
        self.scale_x = 0.45
        
        # Colors (BGR)
        self.bottom_color = np.array([0, 153, 255], dtype=np.float32)   # Orange-ish
        self.top_color    = np.array([0, 230, 255], dtype=np.float32)   # Yellow-ish
        
        # Initialize particles
        self.burns = [self._make_burn(True) for _ in range(self.burn_count)] + \
                     [self._make_burn(False) for _ in range(self.burn_count)]
                     
        self.last_time = time.perf_counter()

    def _make_burn(self, heat: bool) -> Burn:
        # Adapted from user snippet
        h = random.uniform(1, 10) if heat else random.uniform(6, self.burn_size / 2)
        w = self.burn_size

        duration = random.uniform(0.8, 2.0) # Faster than original for more energy
        distance = self.fire_size + self.burn_size
        speed = distance / duration

        x = random.uniform(-self.fire_size / 2, self.fire_size / 2)
        y = random.uniform(-self.burn_size, self.fire_size)

        return Burn(x=x, y=y, h=h, w=w, speed=speed, heat=heat)

    def update(self):
        """Update particle positions based on delta time."""
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now
        
        # Cap dt to prevent huge jumps if frame lagged
        if dt > 0.1: dt = 0.1

        for i, b in enumerate(self.burns):
            b.y -= b.speed * dt
            # Reset if moved too far up
            if b.y < -self.burn_size:
                self.burns[i] = self._make_burn(b.heat)

    def render(self):
        """Render the fire effect and return an RGBA image."""
        # 1. Build Mask
        mask = np.zeros((self.fire_size, self.fire_size), dtype=np.float32)
        
        # center coords
        cx_base = self.fire_size // 2
        cy_base = self.fire_size // 2
        
        # Base flame blob
        axes = (max(1, int((self.fire_size * self.scale_x) / 2)), self.fire_size // 2)
        cv2.ellipse(mask, (cx_base, cy_base), axes, 0, 0, 360, 1.0, thickness=-1)

        # Carve rising "burn" ellipses (subtractive)
        for b in self.burns:
            cx = int(self.fire_size / 2 + b.x + random.uniform(-1.5, 1.5))
            cy = int(b.y)
            ax = int(b.w / 2)
            ay = max(1, int(b.h / 2))
            
            # Draw black ellipses to "eat" away the base
            cv2.ellipse(mask, (cx, cy), (ax, ay), 0, 0, 360, 0.0, thickness=-1)

        # 2. Blur & Contrast (Blobby effect)
        # Using a smaller kernel size if fire_size is small to save perf
        ksize = (self.blur_px * 2) + 1
        blurred = cv2.GaussianBlur(mask, (ksize, ksize), 0)
        contrasted = np.clip((blurred - 0.5) * self.contrast + 0.5, 0.0, 1.0)

        # 3. Colorize
        # Create gradient cache if needed, but doing it live is fine for now
        y = np.linspace(0.0, 1.0, self.fire_size, dtype=np.float32).reshape(self.fire_size, 1, 1)
        gradient = self.top_color * (1.0 - y) + self.bottom_color * y
        
        flame_bgr = gradient * contrasted[..., None]
        
        # 4. Create RGBA
        # Alpha is essentially the contrasted mask
        alpha = (contrasted * 255).astype(np.uint8)
        bgr = np.clip(flame_bgr, 0, 255).astype(np.uint8)
        
        rgba = cv2.merge([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2], alpha])
        
        return rgba
