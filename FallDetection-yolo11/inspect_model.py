from ultralytics import YOLO
import sys
try:
    model = YOLO('model.pt')
    print("Model names:", model.names)
except Exception as e:
    print("Error:", e)
