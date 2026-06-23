"""
train.py — Fine-tune YOLOv8 on Fire-Smoke Dataset
===================================================
Dataset : https://universe.roboflow.com/reyzi916/fire-smoke-det/dataset/6
Run     : python train.py [--epochs 100] [--imgsz 640] [--batch 16]

Requirements: pip install ultralytics roboflow
"""

import os
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def download_dataset(api_key: str, output_dir: str = "datasets") -> str:
    """Download Roboflow fire-smoke dataset (v6)."""
    try:
        from roboflow import Roboflow
    except ImportError:
        raise RuntimeError("Run: pip install roboflow")

    rf = Roboflow(api_key=api_key)
    project = rf.workspace("reyzi916").project("fire-smoke-det")
    dataset = project.version(6).download("yolov8", location=output_dir)
    logger.info(f"Dataset downloaded to: {dataset.location}")
    return dataset.location


def train(
    data_yaml: str,
    epochs:    int   = 100,
    imgsz:     int   = 640,
    batch:     int   = 16,
    patience:  int   = 20,
    device:    str   = "0",
    project:   str   = "runs/fire_smoke",
    name:      str   = "yolov8l_finetune",
):
    """Fine-tune YOLOv8l with optimised hyperparameters for fire/smoke."""
    from ultralytics import YOLO

    logger.info("Loading YOLOv8l base weights …")
    model = YOLO("yolov8l.pt")   # large variant → balance accuracy / speed

    logger.info(f"Starting training — epochs={epochs}, imgsz={imgsz}, batch={batch}")
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=patience,
        device=device,
        project=project,
        name=name,
        # ── Optimiser ────────────────────────────────────────────────────────
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=5,
        # ── Augmentation (boosts generalisation → accuracy) ───────────────
        mosaic=1.0,
        mixup=0.15,
        copy_paste=0.3,
        degrees=15.0,
        translate=0.1,
        scale=0.5,
        shear=5.0,
        perspective=0.001,
        flipud=0.05,
        fliplr=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        # ── Misc ─────────────────────────────────────────────────────────────
        cache=True,
        save=True,
        save_period=10,
        plots=True,
        workers=4,
        verbose=True,
        amp=True,          # mixed-precision — faster on GPU
        close_mosaic=10,   # disable mosaic last 10 epochs
        val=True,
        conf=0.45,
        iou=0.45,
        # Multi-scale training (helps detect at varying distances)
        rect=False,
    )

    # Copy best weights to models/
    best_weights = Path(project) / name / "weights" / "best.pt"
    dest = Path("models/fire_smoke_yolov8.pt")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if best_weights.exists():
        import shutil
        shutil.copy(best_weights, dest)
        logger.info(f"✅ Best weights copied to {dest}")

    logger.info(f"Training complete. mAP50: {results.results_dict.get('metrics/mAP50(B)', '?')}")
    return results


def validate(model_path: str, data_yaml: str):
    """Validate a trained model and print metrics."""
    from ultralytics import YOLO
    model = YOLO(model_path)
    metrics = model.val(data=data_yaml, conf=0.45, iou=0.45)
    logger.info("=== Validation Results ===")
    logger.info(f"mAP50   : {metrics.box.map50:.4f}")
    logger.info(f"mAP50-95: {metrics.box.map:.4f}")
    logger.info(f"Precision: {metrics.box.mp:.4f}")
    logger.info(f"Recall   : {metrics.box.mr:.4f}")
    return metrics


def export_model(model_path: str, fmt: str = "onnx"):
    """Export trained model (onnx / torchscript / tflite …)."""
    from ultralytics import YOLO
    model = YOLO(model_path)
    exported = model.export(format=fmt, dynamic=True, simplify=True)
    logger.info(f"Exported model: {exported}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fire-Smoke YOLOv8 Training")
    parser.add_argument("--api-key",   type=str,  default="",         help="Roboflow API key")
    parser.add_argument("--data",      type=str,  default="",         help="Path to data.yaml (skip download if set)")
    parser.add_argument("--epochs",    type=int,  default=100)
    parser.add_argument("--imgsz",     type=int,  default=640)
    parser.add_argument("--batch",     type=int,  default=16)
    parser.add_argument("--patience",  type=int,  default=20)
    parser.add_argument("--device",    type=str,  default="0",        help="cuda device or 'cpu'")
    parser.add_argument("--validate",  action="store_true")
    parser.add_argument("--export",    type=str,  default="",         help="Export format: onnx/torchscript")
    args = parser.parse_args()

    data_yaml = args.data
    if not data_yaml:
        if not args.api_key:
            raise ValueError("Provide --api-key or --data path")
        dataset_path = download_dataset(args.api_key)
        data_yaml = str(Path(dataset_path) / "data.yaml")

    if args.validate and Path("models/fire_smoke_yolov8.pt").exists():
        validate("models/fire_smoke_yolov8.pt", data_yaml)
    elif args.export and Path("models/fire_smoke_yolov8.pt").exists():
        export_model("models/fire_smoke_yolov8.pt", args.export)
    else:
        train(
            data_yaml=data_yaml,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=args.patience,
            device=args.device,
        )
