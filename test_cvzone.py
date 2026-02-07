from cvzone.SelfieSegmentationModule import SelfieSegmentation
import cv2

try:
    seg = SelfieSegmentation()
    print("cvzone SelfieSegmentation initialized successfully")
except Exception as e:
    print(f"cvzone initialization failed: {e}")
