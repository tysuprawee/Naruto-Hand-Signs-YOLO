
import cv2
import cvzone
import time
import math
import argparse
from pathlib import Path
# from ultralytics import YOLO # Skip heavy load for quick test
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

print("Imports done.")

model_path_mp = "models/face_landmarker.task"
base_options = python.BaseOptions(model_asset_path=model_path_mp)
options = vision.FaceLandmarkerOptions(base_options=base_options, num_faces=1)
try:
    detector = vision.FaceLandmarker.create_from_options(options)
    print("Detector created successfully!")
except Exception as e:
    print(f"Detector creation failed: {e}")
