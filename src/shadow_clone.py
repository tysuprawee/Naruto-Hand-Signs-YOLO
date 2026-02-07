import cv2
import mediapipe as mp
import numpy as np
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# -----------------------
# Config (tune these)
# -----------------------
MODEL_PATH = "models/selfie_segmenter.tflite"

# Speed knobs:
SEGMENT_WIDTH = 320          # lower = faster (try 256/320/480). 0 disables downscale.
MASK_EVERY_N_FRAMES = 2      # run segmentation every N frames (1 = every frame)
ALPHA_THRESH = 0.35          # bbox threshold
EDGE_BLUR_SIGMA = 2.0        # soft edges; 0 to disable

# Clone look:
CLONE_DX_RATIO = 0.28        # target horizontal spacing relative to frame width
CLONE_OPACITY = 0.85         # final opacity of clones

# Animation:
ANIM_DURATION_SEC = 0.35     # how fast clones "burst out"
FADE_IN = True               # fade in during burst

# -----------------------
# Helpers
# -----------------------
def get_alpha_from_result(segmentation_result):
    """
    Returns alpha mask float32 in [0..1], shape (H,W).
    Prefers confidence masks when available; falls back to category mask.
    """
    confs = getattr(segmentation_result, "confidence_masks", None)
    if confs and len(confs) >= 2:
        # Typically [background, person]
        person_conf = confs[1].numpy_view().astype(np.float32)
        return np.clip(person_conf, 0.0, 1.0)

    category_mask = segmentation_result.category_mask
    mask = category_mask.numpy_view()
    if mask.ndim == 3:
        mask = mask[:, :, 0]

    vals, counts = np.unique(mask, return_counts=True)
    bg_val = vals[np.argmax(counts)]
    alpha = (mask != bg_val).astype(np.float32)
    return alpha

def alpha_paste(dst, fg, a, x, y, opacity=1.0):
    """
    Boundary-safe alpha paste.
    dst: HxWx3 uint8
    fg:  hxwx3 uint8
    a:   hxw float32 in [0..1]
    x,y: top-left paste location on dst
    """
    H, W = dst.shape[:2]
    h, w = fg.shape[:2]

    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(W, x + w), min(H, y + h)
    if x1 >= x2 or y1 >= y2:
        return

    sx1, sy1 = x1 - x, y1 - y
    sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)

    roi = dst[y1:y2, x1:x2].astype(np.float32)
    fg_crop = fg[sy1:sy2, sx1:sx2].astype(np.float32)

    a_crop = a[sy1:sy2, sx1:sx2].astype(np.float32) * opacity
    a_crop = np.clip(a_crop, 0.0, 1.0)
    a3 = a_crop[:, :, None]

    out = fg_crop * a3 + roi * (1.0 - a3)
    dst[y1:y2, x1:x2] = out.astype(np.uint8)

def smoothstep(t: float) -> float:
    """0..1 easing"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

# -----------------------
# Init MediaPipe segmenter (Tasks API)
# -----------------------
print(f"Loading model from {MODEL_PATH}...")
try:
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.ImageSegmenterOptions(
        base_options=base_options,
        output_category_mask=True,
        output_confidence_masks=True,
    )
    segmenter = vision.ImageSegmenter.create_from_options(options)
    print("Segmenter loaded successfully.")
except Exception as e:
    print(f"Error loading segmenter: {e}")
    raise SystemExit(1)

# -----------------------
# Camera
# -----------------------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("Error: Could not open camera.")
    raise SystemExit(1)

print("Option A: Real you stays center (live background).")
print("Press SPACE to burst clones outward.")
print("ESC quit | [ / ] spacing | - / = opacity")

# State
last_alpha_full = None
frame_count = 0

dx_ratio = CLONE_DX_RATIO
clone_opacity = CLONE_OPACITY

clones_visible = False
animating = False
anim_start = 0.0

while True:
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    frame_count += 1

    # Canvas is the LIVE frame (keeps real you in middle)
    canvas = frame.copy()

    # --- Segmentation (downscale + reuse every N frames) ---
    run_seg = (frame_count % MASK_EVERY_N_FRAMES == 0) or (last_alpha_full is None)

    if run_seg:
        if SEGMENT_WIDTH and 0 < SEGMENT_WIDTH < w:
            scale = SEGMENT_WIDTH / float(w)
            seg_w = SEGMENT_WIDTH
            seg_h = max(1, int(h * scale))
            small = cv2.resize(frame, (seg_w, seg_h), interpolation=cv2.INTER_LINEAR)

            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_small)

            result = segmenter.segment(mp_image)
            alpha_small = get_alpha_from_result(result)
            alpha_full = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        else:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            result = segmenter.segment(mp_image)
            alpha_full = get_alpha_from_result(result).astype(np.float32)

        if EDGE_BLUR_SIGMA and EDGE_BLUR_SIGMA > 0:
            alpha_full = cv2.GaussianBlur(alpha_full, (0, 0), EDGE_BLUR_SIGMA)
            alpha_full = np.clip(alpha_full, 0.0, 1.0)

        last_alpha_full = alpha_full
    else:
        alpha_full = last_alpha_full

    # --- Detect bbox for person ROI ---
    mask_u8 = (alpha_full >= ALPHA_THRESH).astype(np.uint8) * 255
    pts = cv2.findNonZero(mask_u8)

    if pts is None:
        cv2.putText(canvas, "No person detected (lighting / move in frame)", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        clones_visible = False
        animating = False
    else:
        x, y, bw, bh = cv2.boundingRect(pts)

        # Padding
        pad = 12
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + bw + pad)
        y2 = min(h, y + bh + pad)

        # Extract ONE cutout ROI (live pixels + alpha)
        fg_crop = frame[y1:y2, x1:x2]
        a_crop = alpha_full[y1:y2, x1:x2]

        # If clones are enabled/animating, compute animated dx + opacity
        if animating:
            t = (time.perf_counter() - anim_start) / ANIM_DURATION_SEC
            p = smoothstep(t)
            if t >= 1.0:
                animating = False
                clones_visible = True
                p = 1.0

            dx_target = int(w * dx_ratio)
            dx = int(dx_target * p)

            if FADE_IN:
                op = clone_opacity * p
            else:
                op = clone_opacity

            # Paste clones that "come out" from body
            alpha_paste(canvas, fg_crop, a_crop, x1 - dx, y1, opacity=op)  # left
            alpha_paste(canvas, fg_crop, a_crop, x1 + dx, y1, opacity=op)  # right

        elif clones_visible:
            dx = int(w * dx_ratio)
            alpha_paste(canvas, fg_crop, a_crop, x1 - dx, y1, opacity=clone_opacity)  # left
            alpha_paste(canvas, fg_crop, a_crop, x1 + dx, y1, opacity=clone_opacity)  # right
        else:
            # clones not visible yet: do nothing (only real you)
            pass

    # UI
    cv2.putText(canvas, "Shadow Clone Jutsu (Option A)", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 140, 255), 2)

    status = "READY (press SPACE)" if (not clones_visible and not animating) else ("BURSTING..." if animating else "CLONES OUT (press SPACE to burst again)")
    cv2.putText(canvas, status, (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(canvas, f"[ / ] spacing: {dx_ratio:.2f}   -/= opacity: {clone_opacity:.2f}   SPACE burst   ESC quit",
                (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    cv2.imshow("Shadow Clones", canvas)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break

    # Controls
    elif key == ord('['):
        dx_ratio = max(0.05, dx_ratio - 0.02)
    elif key == ord(']'):
        dx_ratio = min(0.80, dx_ratio + 0.02)
    elif key == ord('-'):
        clone_opacity = max(0.10, clone_opacity - 0.05)
    elif key == ord('=') or key == ord('+'):
        clone_opacity = min(1.00, clone_opacity + 0.05)

    # SPACE: trigger burst animation
    elif key == 32:
        anim_start = time.perf_counter()
        animating = True
        clones_visible = False  # reset so it re-bursts cleanly

cap.release()
segmenter.close()
cv2.destroyAllWindows()
