from ultralytics import YOLO

model = YOLO("models/runs/handsigns_yolov8n_20260129_002620/weights/best.pt")
success = model.export(format="onnx", imgsz=640, opset=12)
print(f"Export finished: {success}")
