"""
train.py - Training script for Naruto hand signs YOLO model.

This script trains a YOLO model using Ultralytics on the custom
hand signs dataset. It accepts command-line arguments for model
configuration and saves results to models/runs/.

Usage:
    python train.py
    python train.py --model yolov8n.pt --epochs 100 --img-size 640
    python train.py --model yolov8s.pt --epochs 50 --batch 16

Arguments:
    --model: Base YOLO model to fine-tune (default: yolov8n.pt)
    --epochs: Number of training epochs (default: 100)
    --img-size: Image size for training (default: 640)
    --batch: Batch size (default: 16, use -1 for auto)
    --patience: Early stopping patience (default: 50)
    --device: Device to train on (default: auto-detect)
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Ultralytics YOLO imports
from ultralytics import YOLO

# Add the parent directory to path to import from utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.paths import (
    get_data_yaml_path,
    get_runs_dir,
    ensure_directories_exist,
    get_class_names,
)


def validate_dataset() -> bool:
    """
    Validate that the dataset is properly set up before training.
    
    Returns:
        True if dataset looks valid, False otherwise.
    """
    from src.utils.paths import (
        get_train_images_dir,
        get_val_images_dir,
        get_train_labels_dir,
        get_val_labels_dir,
    )
    
    print("[*] Validating dataset structure...")
    
    # Check directories exist
    train_img_dir = get_train_images_dir()
    val_img_dir = get_val_images_dir()
    train_lbl_dir = get_train_labels_dir()
    val_lbl_dir = get_val_labels_dir()
    
    errors = []
    
    if not train_img_dir.exists():
        errors.append(f"Training images directory not found: {train_img_dir}")
    elif len(list(train_img_dir.glob("*.*"))) == 0:
        errors.append(f"No images found in training directory: {train_img_dir}")
    
    if not val_img_dir.exists():
        errors.append(f"Validation images directory not found: {val_img_dir}")
    elif len(list(val_img_dir.glob("*.*"))) == 0:
        errors.append(f"No images found in validation directory: {val_img_dir}")
    
    if not train_lbl_dir.exists():
        errors.append(f"Training labels directory not found: {train_lbl_dir}")
    elif len(list(train_lbl_dir.glob("*.txt"))) == 0:
        errors.append(f"No label files found in training directory: {train_lbl_dir}")
    
    if not val_lbl_dir.exists():
        errors.append(f"Validation labels directory not found: {val_lbl_dir}")
    elif len(list(val_lbl_dir.glob("*.txt"))) == 0:
        errors.append(f"No label files found in validation directory: {val_lbl_dir}")
    
    # Check data.yaml exists
    data_yaml = get_data_yaml_path()
    if not data_yaml.exists():
        errors.append(f"data.yaml not found: {data_yaml}")
    
    if errors:
        print("[-] Dataset validation failed:")
        for error in errors:
            print(f"    - {error}")
        print("\n[*] Please ensure you have:")
        print("    1. Captured images using capture_dataset.py")
        print("    2. Labeled them with Roboflow or similar tool")
        print("    3. Exported in YOLO format and placed files in:")
        print("       - dataset/images/train/")
        print("       - dataset/images/val/")
        print("       - dataset/labels/train/")
        print("       - dataset/labels/val/")
        return False
    
    # Count files
    train_images = len(list(train_img_dir.glob("*.*")))
    val_images = len(list(val_img_dir.glob("*.*")))
    train_labels = len(list(train_lbl_dir.glob("*.txt")))
    val_labels = len(list(val_lbl_dir.glob("*.txt")))
    
    print(f"    Training: {train_images} images, {train_labels} labels")
    print(f"    Validation: {val_images} images, {val_labels} labels")
    print("[+] Dataset validation passed!")
    
    return True


def main():
    """Main function to run YOLO training."""
    
    # =========================================================================
    # STEP 1: Parse command-line arguments
    # =========================================================================
    parser = argparse.ArgumentParser(
        description="Train YOLO model on Naruto hand signs dataset"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="yolov8n.pt",
        help="Base YOLO model to fine-tune (default: yolov8n.pt)"
    )
    parser.add_argument(
        "--epochs", "-e",
        type=int,
        default=100,
        help="Number of training epochs (default: 100)"
    )
    parser.add_argument(
        "--img-size", "--imgsz",
        type=int,
        default=640,
        help="Image size for training (default: 640)"
    )
    parser.add_argument(
        "--batch", "-b",
        type=int,
        default=16,
        help="Batch size, -1 for auto (default: 16)"
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=50,
        help="Early stopping patience (default: 50)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="",
        help="Device to train on: 'cpu', '0', '0,1', etc. (default: auto)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from last checkpoint"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of dataloader workers (default: 8)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="",
        help="Custom name for this training run"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip dataset validation check"
    )

    # Augmentation Arguments
    parser.add_argument("--hsv-h", type=float, default=0.015, help="HSV-Hue augmentation (fraction)")
    parser.add_argument("--hsv-s", type=float, default=0.7, help="HSV-Saturation augmentation (fraction)")
    parser.add_argument("--hsv-v", type=float, default=0.4, help="HSV-Value augmentation (fraction)")
    parser.add_argument("--degrees", type=float, default=15.0, help="Image rotation (+/- deg)")
    parser.add_argument("--translate", type=float, default=0.1, help="Image translation (+/- fraction)")
    parser.add_argument("--scale", type=float, default=0.5, help="Image scale gain (+/- gain)")
    parser.add_argument("--shear", type=float, default=0.0, help="Image shear (+/- deg)")
    parser.add_argument("--perspective", type=float, default=0.0005, help="Image perspective (+/- fraction), range 0-0.001")
    parser.add_argument("--fliplr", type=float, default=0.5, help="Image flip left-right (probability)")
    parser.add_argument("--mosaic", type=float, default=1.0, help="Image mosaic (probability)")
    parser.add_argument("--mixup", type=float, default=0.1, help="Image mixup (probability)")
    parser.add_argument("--copy-paste", type=float, default=0.1, help="Segment copy-paste (probability)")
    
    args = parser.parse_args()
    
    # =========================================================================
    # STEP 2: Setup and validation
    # =========================================================================
    print("=" * 60)
    print("Naruto Hand Signs - YOLO Training")
    print("=" * 60)
    print(f"\nClasses: {get_class_names()}")
    print(f"Model: {args.model}")
    print(f"Epochs: {args.epochs}")
    print(f"Image size: {args.img_size}")
    print(f"Batch size: {args.batch}")
    print(f"Patience: {args.patience}")
    print(f"Device: {args.device if args.device else 'auto'}")
    print()
    
    # Ensure directories exist
    ensure_directories_exist()
    
    # Validate dataset unless skipped
    if not args.skip_validation:
        if not validate_dataset():
            print("\n[-] Training aborted due to dataset issues.")
            print("[*] Use --skip-validation to bypass this check.")
            return 1
    
    # =========================================================================
    # STEP 3: Initialize YOLO model
    # =========================================================================
    print(f"\n[*] Loading model: {args.model}")
    
    try:
        model = YOLO(args.model)
    except Exception as e:
        print(f"[-] Error loading model: {e}")
        print("[*] Available models: yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.")
        return 1
    
    # =========================================================================
    # STEP 4: Configure training parameters
    # =========================================================================
    data_yaml = get_data_yaml_path()
    runs_dir = get_runs_dir()
    
    # Generate run name if not provided
    if args.name:
        run_name = args.name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = Path(args.model).stem
        run_name = f"handsigns_{model_name}_{timestamp}"
    
    print(f"\n[*] Training configuration:")
    print(f"    Data config: {data_yaml}")
    print(f"    Output directory: {runs_dir}")
    print(f"    Run name: {run_name}")
    
    # =========================================================================
    # STEP 5: Start training
    # =========================================================================
    print("\n[*] Starting training...")
    print("=" * 60)
    
    try:
        # Train the model
        # Note: Ultralytics will print detailed progress during training
        results = model.train(
            data=str(data_yaml),
            epochs=args.epochs,
            imgsz=args.img_size,
            batch=args.batch,
            patience=args.patience,
            device=args.device if args.device else None,
            workers=args.workers,
            project=str(runs_dir),
            name=run_name,
            exist_ok=True,
            pretrained=True,
            verbose=True,
            resume=args.resume,
            # Augmentation settings (from CLI args)
            hsv_h=args.hsv_h,
            hsv_s=args.hsv_s,
            hsv_v=args.hsv_v,
            degrees=args.degrees,
            translate=args.translate,
            scale=args.scale,
            shear=args.shear,
            perspective=args.perspective,
            fliplr=args.fliplr,
            mosaic=args.mosaic,
            mixup=args.mixup,
            copy_paste=args.copy_paste,
        )
        
    except KeyboardInterrupt:
        print("\n[*] Training interrupted by user")
        return 1
    except Exception as e:
        print(f"\n[-] Training error: {e}")
        return 1
    
    # =========================================================================
    # STEP 6: Report results
    # =========================================================================
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    
    # Find the best weights
    best_weights = runs_dir / run_name / "weights" / "best.pt"
    last_weights = runs_dir / run_name / "weights" / "last.pt"
    
    print(f"\n[+] Results saved to: {runs_dir / run_name}")
    
    if best_weights.exists():
        print(f"[+] Best weights: {best_weights}")
        print(f"\n[*] To run detection with trained model:")
        print(f"    python src/detect_webcam.py --weights \"{best_weights}\"")
    
    if last_weights.exists():
        print(f"[+] Last weights: {last_weights}")
    
    print("\n[*] Check the results folder for:")
    print("    - results.csv: Training metrics over time")
    print("    - confusion_matrix.png: Class confusion matrix")
    print("    - results.png: Training curves visualization")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
