from dataclasses import dataclass
from typing import Any


@dataclass
class EffectContext:
    dt: float = 0.0
    jutsu_name: str = ""
    frame_bgr: Any = None
    frame_shape: Any = None
    hand_pos: Any = None
    mouth_pos: Any = None
    face_center: Any = None
    cam_x: int = 0
    cam_y: int = 0
    scale_x: float = 1.0
    scale_y: float = 1.0
    font: Any = None
    debug: bool = False


class BaseEffect:
    def on_jutsu_start(self, context: EffectContext):
        pass

    def on_jutsu_end(self, context: EffectContext):
        pass

    def on_sign_detected(self, sign_name: str, context: EffectContext):
        pass

    def update(self, context: EffectContext):
        pass

    def render(self, screen, context: EffectContext):
        pass
