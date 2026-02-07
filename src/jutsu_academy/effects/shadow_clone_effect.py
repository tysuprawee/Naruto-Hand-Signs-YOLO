import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pygame
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from src.jutsu_academy.effects.base import BaseEffect, EffectContext


class ShadowCloneEffect(BaseEffect):
    def __init__(self, swap_xy=True):
        self.swap_xy = swap_xy
        self.sign_aliases = {
            "shadow_clone",
            "shadow clone",
            "shadow-clone",
            "kage_bunshin",
            "kage bunshin",
            "kage-bunshin",
            "kagebunshin",
            "kage_bunshin_no_jutsu",
            "kage bunshin no jutsu",
            "clone",
        }

        self.segment_width = 320
        self.mask_every_n_frames = 2
        self.alpha_thresh = 0.35
        self.edge_blur_sigma = 2.0
        self.clone_dx_ratio = 0.28
        self.clone_opacity = 0.85
        self.anim_duration_sec = 0.35
        self.fade_in = True

        self.last_alpha_full = None
        self.frame_count = 0
        self.clones_visible = False
        self.animating = False
        self.anim_start = 0.0
        self.prepared_clones = []

        self.segmenter = None
        self.enabled = self._init_segmenter()

    def _init_segmenter(self):
        try:
            model_path = Path(__file__).resolve().parents[3] / "models" / "selfie_segmenter.tflite"
            base_options = python.BaseOptions(
                model_asset_path=str(model_path),
                delegate=python.BaseOptions.Delegate.CPU,
            )
            options = vision.ImageSegmenterOptions(
                base_options=base_options,
                output_category_mask=True,
                output_confidence_masks=True,
            )
            self.segmenter = vision.ImageSegmenter.create_from_options(options)
            return True
        except Exception as e:
            print(f"[!] ShadowCloneEffect disabled (segmenter init failed): {e}")
            self.segmenter = None
            return False

    def _normalize_sign_name(self, sign_name):
        if not sign_name:
            return ""
        s = str(sign_name).strip().lower()
        s = s.replace("-", " ").replace("_", " ")
        s = " ".join(s.split())
        return s

    def _get_alpha_from_result(self, segmentation_result):
        confs = getattr(segmentation_result, "confidence_masks", None)
        if confs and len(confs) >= 2:
            person_conf = confs[1].numpy_view().astype(np.float32)
            return np.clip(person_conf, 0.0, 1.0)

        category_mask = segmentation_result.category_mask
        mask = category_mask.numpy_view()
        if mask.ndim == 3:
            mask = mask[:, :, 0]

        vals, counts = np.unique(mask, return_counts=True)
        bg_val = vals[np.argmax(counts)]
        return (mask != bg_val).astype(np.float32)

    def _smoothstep(self, t):
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    def _trigger_burst(self):
        self.anim_start = time.perf_counter()
        self.animating = True
        self.clones_visible = False

    def _prepare_surface(self, fg_crop, a_crop, opacity):
        alpha_u8 = np.clip(a_crop * max(0.0, min(1.0, opacity)) * 255.0, 0, 255).astype(np.uint8)
        rgb_crop = cv2.cvtColor(fg_crop, cv2.COLOR_BGR2RGB)
        rgba = np.dstack([rgb_crop, alpha_u8])
        return pygame.image.frombuffer(rgba.tobytes(), (rgba.shape[1], rgba.shape[0]), "RGBA")

    def on_jutsu_start(self, context: EffectContext):
        normalized = self._normalize_sign_name(context.jutsu_name)
        if (
            normalized in self.sign_aliases
            or ("shadow" in normalized and "clone" in normalized)
            or ("kage" in normalized and "bunshin" in normalized)
        ):
            self._trigger_burst()

    def on_jutsu_end(self, context: EffectContext):
        self.prepared_clones = []
        self.clones_visible = False
        self.animating = False

    def on_sign_detected(self, sign_name: str, context: EffectContext):
        normalized = self._normalize_sign_name(sign_name)
        if not normalized:
            return

        if (
            normalized in self.sign_aliases
            or ("shadow" in normalized and "clone" in normalized)
            or ("kage" in normalized and "bunshin" in normalized)
        ):
            self._trigger_burst()

    def update(self, context: EffectContext):
        self.prepared_clones = []
        if not self.enabled or context.frame_bgr is None:
            return

        frame = context.frame_bgr
        h, w = frame.shape[:2]
        self.frame_count += 1

        run_seg = (self.frame_count % self.mask_every_n_frames == 0) or (self.last_alpha_full is None)
        if run_seg:
            if self.segment_width and 0 < self.segment_width < w:
                scale = self.segment_width / float(w)
                seg_w = self.segment_width
                seg_h = max(1, int(h * scale))
                small = cv2.resize(frame, (seg_w, seg_h), interpolation=cv2.INTER_LINEAR)
                rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_small)
                result = self.segmenter.segment(mp_image)
                alpha_small = self._get_alpha_from_result(result)
                alpha_full = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
            else:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = self.segmenter.segment(mp_image)
                alpha_full = self._get_alpha_from_result(result).astype(np.float32)

            if self.edge_blur_sigma and self.edge_blur_sigma > 0:
                alpha_full = cv2.GaussianBlur(alpha_full, (0, 0), self.edge_blur_sigma)
                alpha_full = np.clip(alpha_full, 0.0, 1.0)
            self.last_alpha_full = alpha_full
        else:
            alpha_full = self.last_alpha_full

        if alpha_full is None:
            return

        mask_u8 = (alpha_full >= self.alpha_thresh).astype(np.uint8) * 255
        pts = cv2.findNonZero(mask_u8)
        if pts is None:
            self.clones_visible = False
            self.animating = False
            return

        x, y, bw, bh = cv2.boundingRect(pts)
        pad = 12
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + bw + pad)
        y2 = min(h, y + bh + pad)

        fg_crop = frame[y1:y2, x1:x2]
        a_crop = alpha_full[y1:y2, x1:x2]
        if fg_crop.size == 0:
            return

        if self.animating:
            t = (time.perf_counter() - self.anim_start) / self.anim_duration_sec
            p = self._smoothstep(t)
            if t >= 1.0:
                self.animating = False
                self.clones_visible = True
                p = 1.0

            dx_target = int(w * self.clone_dx_ratio)
            dx = int(dx_target * p)
            op = self.clone_opacity * p if self.fade_in else self.clone_opacity
        elif self.clones_visible:
            dx = int(w * self.clone_dx_ratio)
            op = self.clone_opacity
        else:
            return

        left_surface = self._prepare_surface(fg_crop, a_crop, op)
        right_surface = self._prepare_surface(fg_crop, a_crop, op)
        self.prepared_clones = [
            (left_surface, x1 - dx, y1),
            (right_surface, x1 + dx, y1),
        ]

    def render(self, screen, context: EffectContext):
        if not self.prepared_clones:
            return
        for surface, fx, fy in self.prepared_clones:
            dst_w = max(1, int(surface.get_width() * context.scale_x))
            dst_h = max(1, int(surface.get_height() * context.scale_y))
            scaled = pygame.transform.smoothscale(surface, (dst_w, dst_h))
            sx = context.cam_x + int(fx * context.scale_x)
            sy = context.cam_y + int(fy * context.scale_y)
            screen.blit(scaled, (sx, sy))
