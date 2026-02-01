
import time
import random
import cv2
import numpy as np

class FireEffect:
    def __init__(self, fire_size=400, particle_count=150):
        self.fire_size = fire_size
        self.particle_count = particle_count
        
        # 1. Pre-compute the Particle "Sprite" (A glowing Gaussian blob)
        # This is much faster than drawing circles every frame
        self.sprite_size = 32
        self.half_sprite = self.sprite_size // 2
        
        # Create a radial gradient (Gaussian)
        # X and Y grids
        x = np.linspace(-1, 1, self.sprite_size)
        y = np.linspace(-1, 1, self.sprite_size)
        xv, yv = np.meshgrid(x, y)
        d = np.sqrt(xv**2 + yv**2)
        
        # Gaussian falloff: exp(-k * d^2)
        blob = np.exp(-4 * d**2)
        blob = np.clip(blob, 0, 1)
        self.particle_sprite = (blob * 255).astype(np.float32)

        # 2. Create the Color Lookup Table (Heatmap)
        # Maps Heat (0-255) to Color (Black -> Red -> Orange -> Yellow -> White)
        self.color_map = np.zeros((256, 3), dtype=np.uint8)
        for i in range(256):
            if i < 64: # Black to Red
                val = i * 4
                self.color_map[i] = [0, 0, val] # BGR
            elif i < 128: # Red to Orange/Yellow
                val = (i - 64) * 4
                self.color_map[i] = [0, val, 255]
            elif i < 192: # Yellow to White (brighten Blue)
                val = (i - 128) * 4
                self.color_map[i] = [val, 255, 255]
            else: # Pure White bloom
                self.color_map[i] = [255, 255, 255]

        # 3. Initialize Particles System
        # Columns: [x, y, vx, vy, life, max_life, size_scale, noise_offset]
        self.particles = np.zeros((self.particle_count, 8), dtype=np.float32)
        
        # Initialize randomly
        for i in range(self.particle_count):
            self._respawn_particle(i, initial=True)

        self.last_time = time.perf_counter()

    def _respawn_particle(self, i, initial=False):
        # Spawn at bottom center with random spread
        angle = random.uniform(-0.9, 0.9) # Cone angle (Wider spread for tail)
        speed = random.uniform(80, 180)    # Pixels per second
        
        # X position: Centered with variance
        self.particles[i, 0] = self.fire_size / 2 + random.uniform(-20, 20)
        
        # Y position: Start near center (Mouth)
        if initial:
            self.particles[i, 1] = random.uniform(self.fire_size // 2, self.fire_size // 2 + 50)
        else:
            self.particles[i, 1] = self.fire_size // 2 + 40 + random.uniform(0, 20)
            
        # Velocity
        self.particles[i, 2] = speed * np.sin(angle) * 0.4 # vx (Wider angle influence)
        self.particles[i, 3] = -speed # vy (up)
        
        # Life properties
        life = random.uniform(0.5, 1.2)
        self.particles[i, 4] = life
        self.particles[i, 5] = life # max_life
        
        # Size variation
        self.particles[i, 6] = random.uniform(0.5, 2.0)
        
        # Perlin-ish noise phase
        self.particles[i, 7] = random.uniform(0, 100)

    def update(self, wind_x=0.0):
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now
        if dt > 0.1: dt = 0.1 # Lag prevention
        
        # Vectorized updates
        
        # 1. Update positions
        # apply inherent velocity + wind force
        self.particles[:, 0] += (self.particles[:, 2] + wind_x) * dt # X += Vx + Wind
        self.particles[:, 1] += self.particles[:, 3] * dt # Y += Vy
        self.particles[:, 4] -= dt # Life -= dt
        
        # 2. Apply Turbulence (Sine wave "Wind")
        # x += sin(time + y_pos * scale) * strength
        self.particles[:, 0] += np.sin(now * 3 + self.particles[:, 7]) * 40 * dt
        
        # 3. Handle Death/Respawn
        # Boolean mask of dead particles
        dead_indices = np.where(self.particles[:, 4] <= 0)[0]
        # Respawn with slight bias towards wind source? No, keep source centered.
        for idx in dead_indices:
            self._respawn_particle(idx)

    def render(self):
        # Create a black "Heat" canvas (Float32 for accumulation)
        heat_map = np.zeros((self.fire_size, self.fire_size), dtype=np.float32)
        
        # Blit particles
        # This part is performance critical.
        
        pad = self.half_sprite
        w, h = self.fire_size, self.fire_size
        
        # Cast to int for indexing
        px = self.particles[:, 0].astype(int)
        py = self.particles[:, 1].astype(int)
        scales = self.particles[:, 6]
        lifes = self.particles[:, 4] / self.particles[:, 5] # Normalized 0-1
        
        # Create a scaled, faded sprite for each particle
        # Optimization: Just use one sprite size but modulate intensity
        
        # For Python speed, let's just use the global sprite and loop
        # Slicing numpy arrays is fast
        
        sprite_h, sprite_w = self.particle_sprite.shape
        
        for i in range(self.particle_count):
            x, y = px[i], py[i]
            
            # Boundary check
            if x < -pad or x >= w + pad or y < -pad or y >= h + pad:
                continue
                
            # Intensity fades with life
            intensity = lifes[i]
            
            # Simple bounds clamping for the sprite blit
            # Calculate intersection
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(w, x + pad)
            y2 = min(h, y + pad)
            
            # Sprite offsets
            sx1 = max(0, pad - x)
            sy1 = max(0, pad - y)
            sx2 = sx1 + (x2 - x1)
            sy2 = sy1 + (y2 - y1)
            
            if sx2 <= sx1 or sy2 <= sy1: continue

            # Additive blending!
            heat_map[y1:y2, x1:x2] += self.particle_sprite[sy1:sy2, sx1:sx2] * intensity

        # 4. Post-Process
        # Clip heat to byte range
        heat_map = np.clip(heat_map, 0, 255).astype(np.uint8)
        
        # Apply Color Map (LUT) using NumPy indexing
        # heat_map (H, W) -> indices into color_map (256, 3) -> (H, W, 3)
        bgr = self.color_map[heat_map]
        
        # Create Alpha channel based on heat
        # Low heat = transparent. High heat = opaque.
        # We curve it so faint heat falls off quickly (clean edges)
        alpha = np.clip(heat_map * 2.0, 0, 255).astype(np.uint8)
        
        # Merge RGBA
        rgba = cv2.merge([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2], alpha])
        
        return rgba
