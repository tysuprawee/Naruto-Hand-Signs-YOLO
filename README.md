# Shinobi Academy / Naruto Hand Signs

A full-stack project for Naruto hand-sign recognition and gameplay:
- A Python game/training stack (MediaPipe + KNN, legacy YOLO tools, Pygame academy flow)
- A Next.js web frontend (`web/`) for landing page, leaderboard, and release UI

## 🎯 Overview

This project allows you to:
1. **Train** in the **Jutsu Academy** with a modern Pygame interface (Scene-based architecture).
2. **Master** complex 2-handed jutsu sequences.
3. **Progress** your Shinobi Rank (Academy Student → Hokage) via **Quests** and **Mastery**.
4. **Inclusive Detection**: Experience a model that works for **every skin tone** using MediaPipe integration.

### Web Frontend (`web/`)
- Built with **Next.js 16** + Tailwind
- Hero page with:
  - Live **Release Countdown** to **Feb 21, 9:00 PM** (local browser time)
  - Responsive launch/countdown badge
  - Locked **DOWNLOAD** CTA until release
- Routes:
  - `/` landing page
  - `/leaderboard` leaderboard UI
  - `/play` currently redirects home

| (OLD) YOLO Detection | Jutsu Academy (NEW) |
|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/875e8229-59b6-4af2-bef4-2477125515f0" width="400"> | <img src="https://github.com/user-attachments/assets/76461e53-4c9e-4124-bd58-9d2b47caccdf" width="400"> |

### Supported Hand Signs (Classes)
- 🐯 **tiger** (key: 1)
- 🐗 **boar** (key: 2)
- 🐍 **snake** (key: 3)
- 🐏 **ram** (key: 4)
- 🐦 **bird** (key: 5)
- 🐲 **dragon** (key: 6)
- 🐕 **dog** (key: 7)
- 🐀 **rat** (key: 8)
- 🐎 **horse** (key: 9)
- 🐵 **monkey** (key: 0)
- 🐂 **ox** (key: -)
- 🐇 **hare** (key: =)

---

## 🆕 New Features (v1.1)

### 📜 Quest System & Progression
- **Daily & Weekly Quests**: Earn XP by completing tasks like "Land 25 correct signs" or "Complete 5 jutsu runs".
- **Mastery Tiers**: Achieve Bronze, Silver, and Gold mastery for each Jutsu based on your speed.
- **Save System**: Your progress (XP, Rank, Stats) is saved locally for Guest users (`player_meta.json`) or synced to the cloud for logged-in users.

### 👥 Shadow Clone Jutsu
- **Advanced Particles**: A brand new `ShadowCloneSystem` renders dynamic clone particles that spawn from your actual body position using computer vision.
- **Interactive Demo**: Run `python src/jutsu_academy/shadow_clones.py` to see the particle system in action.

### 🏗️ Modular Scene Architecture
The codebase has been refactored into a robust **Scene Manager** system, making it easier to extend:
- **MenuScene**: Main hub with smooth UI transitions.
- **DojoScene**: The core gameplay loop.
- **SettingsScene**, **AboutScene**, **LeaderboardScene**: dedicated screens for better UX.

---

## 📁 Project Structure

The project is organized into modular systems to handle the game, the AI, and the visual effects separately.

### 🎓 1. The Academy (Main Game)
*   **`src/jutsu_academy/main_pygame.py`**: **The Launcher**. The central entry point that initializes the `JutsuAcademy` application.
*   **`src/jutsu_academy/scenes/`**: **Game Logic**. Contains separate modules for each game state (`menu.py`, `dojo.py`, `settings.py`, etc.).
*   **`src/jutsu_academy/managers/`**: **Systems**. Handles `ProgressionManager`, `NetworkManager`, and other core subsystems.
*   **`src/jutsu_registry.py`**: **The Encyclopedia**. Contains all Jutsus, their required hand sign sequences, and their minimum rank/level requirements.

### 🧠 2. The AI Brain (Detection)
*   **`src/mp_trainer.py`**: **The New Way**. Converts your hand movements into 126 mathematical points and uses a KNN model to identify the signs. This ensures the model works for **all skin tones**.
*   **`src/train.py`** & **`src/process_dataset.py`**: **Legacy Trainers**. Older scripts used to train the pixel-based YOLOv8 model (kept for backward compatibility).
*   **`src/capture_dataset.py`**: **Data Collection**. A tool to quickly capture hundreds of photos of your hands to train the AI on new signs.

### 🎥 3. Effects & Visuals
*   **`src/jutsu_academy/shadow_clones.py`**: **Shadow Clone FX**. The particle system for the Shadow Clone jutsu.
*   **`src/jutsu_academy/ui/`**: **UI Components**. Reusable buttons, sliders, and modals.
*   **`src/utils/paths.py`**: **GPS**. A central utility that tells the code exactly where sounds, videos, and model weights are located.

---

## 🚀 Getting Started

### A) Web App (Next.js)

```bash
cd web
npm install
npm run dev
```

Production build:
```bash
cd web
npm run build
```

### B) Python App

#### 1. Create a Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Run the Academy

The main game is now launched via `main_pygame.py`:

```bash
# Launch the full game
python src/jutsu_academy/main_pygame.py

# Launch Shadow Clone FX Demo
python src/jutsu_academy/shadow_clones.py
```

#### 4. (Optional) Run Visualization Trainer
For the legacy interactive trainer mode:
```bash
python src/jutsu_trainer.py
```

---

## 📝 Modifying Classes

To change the hand sign classes:

1. Edit `CLASSES` list in `src/utils/paths.py`
2. Update `KEY_CLASS_MAP` in `src/utils/paths.py`
3. Update `yolo_config/data.yaml` with new class names

---

## 🐛 Troubleshooting

**Vercel shows `404: NOT_FOUND`:**
- In Vercel Project Settings, set **Root Directory** to `web`
- Do **not** use legacy root rewrites for `/web/...`
- Keep deployment config simple (no root `vercel.json` route rewrites)

**Vercel prerender/build error `supabaseUrl is required`:**
- Ensure `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set in Vercel environment variables
- The current web code guards missing envs, but leaderboard data requires them to function

**SDL Library Conflict (Mac/Linux):**
If you see errors related to `libSDL2` conflicts between `cv2` and `pygame`:
- The application has been updated to handle this in most cases.
- Ensure you are running from the virtual environment.

**Camera not detected:**
- Try different camera indices: `--camera 1`, `--camera 2`
- Check if another application is using the camera

---

## 📚 Resources

- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)
- [Roboflow Labeling Guide](https://docs.roboflow.com/)
- [MediaPipe Hands](https://developers.google.com/mediapipe/solutions/vision/hand_landmarker)

---

## 📄 License

This project is provided as-is for educational purposes.
