import sys
import cv2
import urllib.request
from datasets import load_dataset
from fall_detector import FallDetector

print("Loading dataset...")
ds = load_dataset("dooxhuy/fall-detection", split="test", streaming=True)
sample = next(iter(ds))

print("Keys in sample:", sample.keys())
# The sample usually has an 'image' feature which is a PIL image
image = sample['image']

# convert PIL image to opencv format
import numpy as np
cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
cv2.imwrite("test_fall.jpg", cv_image)
print("Saved test_fall.jpg")

print("Running detector...")
detector = FallDetector("model.pt", conf=0.1)
results = detector.detect(cv_image)
print("Detected:", results)
