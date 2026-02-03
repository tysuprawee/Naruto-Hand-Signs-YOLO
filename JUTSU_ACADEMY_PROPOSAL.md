# PROPOSAL: JUTSU ACADEMY V1.01 (DESKTOP APP)

**Objective**: Create a high-performance, Modern GUI Desktop Application for learning and battling with Ninja Hand Signs.
**Platform**: Windows (Native Python App)
**Engine**: CustomTkinter (UI) + OpenCV (Vision) + YOLOv8 (AI)

---

## 1. Architecture

We will split the application into two distinct layers:
1.  **The Launcher (UI Layer)**: Built with `CustomTkinter`. A modern, dark-themed menu system to handle navigation, settings, and matchmaking.
2.  **The Dojo (Game Layer)**: Built with `OpenCV`. A high-performance window that opens when you start a session. This ensures maximum FPS for the AI.

## 2. Modes

### A. Practice Mode ("The Dojo")
*   **Goal**: Learn the signs and master sequences.
*   **Features**:
    *   Dynamic Difficulty (Novice -> Hokage speeds).
    *   **Combo Meter**: Tracks streak of correct signs.
    *   Visual Effects: Fireball, Chidori (reused and optimized).
    *   **Mirror Mode**: Toggle to match your webcam view.

### B. Multiplayer Mode ("Dojo Duel")
*   **Goal**: 1v1 Battle against another player on the Local Network (LAN).
*   **Gameplay**:
    *   Both players connect via IP.
    *   Game announces a Jutsu (e.g., "CAST FIREBALL!").
    *   First player to complete the sequence deals damage.
    *   HP Bars displayed on screen.
*   **Tech**: Python `socket` (TCP). Simple Host/Join system.

## 3. Settings (Required)
The settings menu will be accessible from the main launcher:
*   **Camera**: Select input device (0, 1, 2...).
*   **Resolution**: 640x480 (Performance) vs 1280x720 (Quality).
*   **Audio**: Master Volume, SFX, Voice.
*   **AI Confidence**: Slider (0.4 - 0.8) to tune sensitivity.

---

## 4. Implementation Plan

### Phase 1: The New Structure
We will create a new folder `src/jutsu_academy/`.
*   `main.py`: The CustomTkinter entry point.
*   `game_engine.py`: The class that runs the OpenCV loop (refactored from `jutsu_trainer.py`).
*   `assets/`: UI images, icons, sounds.

### Phase 2: Refactoring
We will take your existing `jutsu_trainer.py` code (which is good!) and wrap it into a `GameSession` class.
*   Instead of `while True`, it will have `start()`, `update()`, `stop()`.
*   This allows the Menu to launch and close the game cleanly.

### Phase 3: Multiplayer Logic
*   Create `network_manager.py`.
*   Establish a simple protocol: `{"type": "attack", "damage": 20, "jutsu": "fireball"}`.

---

## 5. Visual Mockup (Mental)

** Launcher Window **
+--------------------------------------------------+
|  [ ICON ]  JUTSU ACADEMY                         |
|                                                  |
|       [ PRACTICE ]      [ MULTIPLAYER ]          |
|                                                  |
|                [ SETTINGS ]                      |
|                                                  |
|  Status: Ready | v1.01                           |
+--------------------------------------------------+

** Game Window (Overlay) **
+--------------------------------------------------+
|  p1 HP: [|||||||]          p2 HP: [|||||||]      |
|                                                  |
|                 ( WEBCAM FEED )                  |
|                                                  |
|             [ SNAKE ] [ RAM ] [ TIGER ]          |
+--------------------------------------------------+

---

**Approval Required:**
Shall I proceed with setting up this structure?
1.  I will install `customtkinter` (Modern UI).
2.  I will create the `JutsuAcademy` class structure.
