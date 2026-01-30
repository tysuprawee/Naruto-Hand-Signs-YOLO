# Naruto Hand Signs YOLO

A complete Python project for training and running a YOLO model to recognize Naruto hand signs from a webcam.

## 🎯 Overview

This project allows you to:
1. **Capture** images of hand signs using your webcam
2. **Label** images externally (e.g., with Roboflow)
3. **Train** a YOLO model on your custom dataset
4. **Detect** hand signs in real-time with bounding boxes and labels

| YOLO Detection | Jutsu Trainer |
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

## 📁 Project Structure

```
naruto_handsigns_yolo/
├── src/
│   ├── capture_dataset.py   # Webcam capture script
│   ├── manual_labeler.py    # Native labeling tool (OpenCV based)
│   ├── process_dataset.py   # Auto-labeling & dataset splitting
│   ├── check_labels.py      # Label verification tool
│   ├── train.py             # YOLO training script
│   ├── detect_webcam.py     # Real-time detection script
│   ├── jutsu_trainer.py     # Interactive Jutsu Trainer (main feature!)
│   ├── recipe.txt           # Configurable Jutsu logic & sequences
│   ├── pics/                # Hand sign icons for UI
│   ├── sounds/              # Sound effects (jutsu sounds, feedback)
│   ├── chidori/             # Chidori video and sound effect resources
│   └── utils/
│       ├── paths.py         # Centralized path handling
│       ├── visualization.py # Drawing helpers
│       └── fire_effect.py   # Procedural fire effect rendering
├── dataset/
│   ├── images/
│   │   ├── raw/             # Initial captures (organized by class)
│   │   ├── train/           # Training images (processed)
│   │   └── val/             # Validation images (processed)
│   └── labels/
│       ├── train/           # Training labels (.txt files)
│       └── val/             # Validation labels (.txt files)
├── yolo_config/
│   └── data.yaml            # YOLO dataset configuration
├── models/
│   ├── runs/                # Training results and weights
│   ├── face_landmarker.task # MediaPipe face model (optional)
│   └── hand_landmarker.task # MediaPipe hand model (optional)
├── requirements.txt
└── README.md
```

### Example Training Results
Here is an example of validation batch predictions showing the model confidently detecting hand signs.
<img src="https://github.com/user-attachments/assets/875e8229-59b6-4af2-bef4-2477125515f0" width="800" alt="Training Validation Results"/>

#### Training Metrics
<img src="models/runs/handsigns_yolov8n_20260129_002620/results.png" width="800" alt="Training Metrics"/>

---

## 🚀 Getting Started

### 1. Create a Virtual Environment

**Windows:**
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate
```

**macOS / Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Make sure you're in the project root directory
pip install -r requirements.txt
```

**Note for GPU users:** If you have an NVIDIA GPU and want faster training, install PyTorch with CUDA support from [pytorch.org](https://pytorch.org/).

### 3. Capture Dataset Images

Run the capture script to collect images of your hand signs:

```bash
# Windows
python src\capture_dataset.py

# macOS / Linux
python3 src/capture_dataset.py
```

**Controls:**
- Press `1` to capture "tiger"
- Press `2` to capture "boar"
- Press `3` to capture "snake"
- Press `4` to capture "ram"
- Press `5` to capture "bird"
- Press `6` to capture "dragon"
- Press `7` to capture "dog"
- Press `8` to capture "rat"
- Press `9` to capture "horse"
- Press `0` to capture "monkey"
- Press `-` to capture "ox"
- Press `=` to capture "hare"
- Press `q` to quit

**Tips for good dataset:**
- Capture 50-100+ images per class
- Vary lighting conditions
- Vary hand positions and angles
- Use different backgrounds
- Include both close-up and distant shots

Images are saved to `dataset/images/raw/<class_name>/`

### 4. Label & Process Dataset

This project includes built-in tools to label and prepare your data, so you don't need external software.

#### Step A: Label Images (Manual)
Use the included manual labeler to draw bounding boxes around the hand signs.

```bash
python src/manual_labeler.py
```

**Controls:**
- **Mouse Drag**: Draw a box around the hand.
- **Space**: Save label and go to next image.
- **X**: Trash image (delete poor quality captures).
- **R**: Reset current box.
- **Q**: Quit.

#### Step B: Process & Split (Auto)
Run the processing script to organize your raw data into Training and Validation sets.

```bash
python src/process_dataset.py
```

*Feature:* This script attempts to **auto-label** images using skin-tone detection if you skipped manual labeling for some images. It handles the 80/20 train-val split automatically.

#### Step C: Verify Labels
Before training, it's good practice to visually verify that your labels are correct.

```bash
python src/check_labels.py
```

This will generate sample images with boxes drawn on them in `dataset/debug_labels/`. Open that folder and check a few images to ensure accuracy.

### 5. Train the Model

Once your labeled dataset is in place:

```bash
# Basic training (uses YOLOv8 nano model)
python src/train.py

# With custom options
python src/train.py --model yolov8s.pt --epochs 30 --batch 16
```

**Available arguments:**
| Argument | Default | Description |
|----------|---------|-------------|
| `--model` | yolov8n.pt | Base model (n=nano, s=small, m=medium) |
| `--epochs` | 30 | Number of training epochs |
| `--img-size` | 640 | Image size for training |
| `--batch` | 16 | Batch size (-1 for auto) |
| `--patience` | 50 | Early stopping patience |
| `--device` | auto | Device: 'cpu', '0' (GPU), etc. |

Training results are saved to `models/runs/<run_name>/`

### 6. Run Real-time Detection

After training, run detection with your trained model:

```bash
# Auto-find latest trained weights
python src/detect_webcam.py

# Specify weights file
python src/detect_webcam.py --weights models/runs/<run_name>/weights/best.pt
```

**Available arguments:**
| Argument | Default | Description |
|----------|---------|-------------|
| `--weights` | auto | Path to trained weights |
| `--camera` | 0 | Camera index |
| `--conf` | 0.5 | Confidence threshold |
| `--no-fps` | false | Hide FPS counter |

Press `q` to quit detection.

---

## 🔌 Raspberry Pi Integration

The detection script includes a stub function `send_prediction_to_pi()` in `detect_webcam.py`. To enable sending predictions:

1. Uncomment the relevant package in `requirements.txt`:
   - `pyserial` for serial/UART
   - `paho-mqtt` for MQTT
   - `requests` for HTTP

2. Edit `send_prediction_to_pi()` in `src/detect_webcam.py` with your implementation

3. Run detection with the `--send-to-pi` flag:
   ```bash
   python src/detect_webcam.py --send-to-pi
   ```

---

## 📝 Modifying Classes

To change the hand sign classes:

1. Edit `CLASSES` list in `src/utils/paths.py`
2. Update `KEY_CLASS_MAP` in `src/utils/paths.py`
3. Update `yolo_config/data.yaml` with new class names

---

## 🐛 Troubleshooting

**Camera not detected:**
- Try different camera indices: `--camera 1`, `--camera 2`
- Check if another application is using the camera

**CUDA out of memory:**
- Reduce batch size: `--batch 8` or `--batch 4`
- Use smaller model: `--model yolov8n.pt`

**Poor detection accuracy:**
- Collect more training images (aim for 100+ per class)
- Ensure labels are accurate
- Train for more epochs
- Try a larger model (yolov8s or yolov8m)

---

## 📚 Resources

- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)
- [Roboflow Labeling Guide](https://docs.roboflow.com/)
- [YOLO Format Explanation](https://roboflow.com/formats/yolo-darknet-txt)

---

## 🔥 Jutsu Trainer Mode (Interactive)

Become a ninja master! This interactive mode uses **YOLO** for hand sign recognition and **MediaPipe** for advanced face/hand tracking to guide you through jutsu sequences with real-time visual and audio effects.

### Available Jutsu

| Jutsu | Effect | Hand Sign Sequence |
|-------|--------|-------------------|
| 🔥 **Fireball** | Fire from mouth | Horse → Snake → Ram → Monkey → Boar → Horse → Tiger |
| ⚡ **Chidori** | Lightning on hand | Ox → Hare → Monkey |
| 🌊 **Water Dragon** | Water effect | Ox → Monkey → Hare → Rat → Boar → Bird → Ox → Horse → Bird |
| 👥 **Shadow Clone** | Clone text | Ram → Snake → Tiger |
| 🔥 **Phoenix Flower** | Fire effect | Rat → Tiger → Dog → Ox → Hare → Tiger |

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Download MediaPipe models (optional, for advanced tracking)
# Place face_landmarker.task and hand_landmarker.task in models/

# Run the Trainer
python src/jutsu_trainer.py
```

### Controls

| Key/Action | Function |
|------------|----------|
| **Settings Button** | Click top-right to open settings menu |
| **Q** | Quit the trainer |

### Settings Menu

The in-app settings menu provides:

**Toggle Options:**
- **Boxes**: Show/hide YOLO detection bounding boxes
- **Face Mesh**: Show/hide MediaPipe face landmark wireframe
- **Hand Mesh**: Show/hide MediaPipe hand landmark wireframe
- **Detect Zone**: Show/hide detection region overlay
- **Effects**: Enable/disable visual jutsu effects

**Volume Sliders:**
- **Master**: Overall volume control
- **Each**: Sound for each correct hand sign
- **Done**: Completion sound
- **Sign**: Signature jutsu sound (fireball, chidori, etc.)

**Jutsu Selection:**
- Use `<` and `>` arrows to switch between available jutsu
- **Reset**: Reset current sequence progress
- **Exit**: Close the application

### How It Works
1. **Perform Signs**: Match the highlighted hand sign shown in the icon bar
2. **Feedback**: Icons turn **grey** as you complete each step, with audio cue
3. **Completion**: When all signs are done, the jutsu effect triggers!
   - **Fireball/Phoenix**: Procedural fire renders from your mouth
   - **Chidori**: Lightning effect appears on your hand
   - **Water Dragon**: Water effect on hand
   - **Shadow Clone**: Clone effect around face

---

## 📄 License

This project is provided as-is for educational purposes.

