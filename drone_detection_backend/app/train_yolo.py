"""YOLO model training script for drone detection."""

import os
import yaml
import shutil
from pathlib import Path
from ultralytics import YOLO
import numpy as np
import cv2
from typing import List, Tuple, Optional
import random


class DroneDatasetGenerator:
    """Generate synthetic drone detection dataset for training."""
    
    CLASSES = ["drone", "bird", "aircraft", "helicopter", "person", "vehicle"]
    
    def __init__(self, output_dir: str = "datasets/drone_detection"):
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.labels_dir = self.output_dir / "labels"
        
    def setup_directories(self):
        """Create dataset directory structure."""
        for split in ["train", "val"]:
            (self.images_dir / split).mkdir(parents=True, exist_ok=True)
            (self.labels_dir / split).mkdir(parents=True, exist_ok=True)
    
    def generate_synthetic_drone(
        self,
        frame: np.ndarray,
        x: int,
        y: int,
        size: int = 40
    ) -> Tuple[np.ndarray, List[float]]:
        """Draw a synthetic drone on the frame and return bbox."""
        h, w = frame.shape[:2]
        
        # Drone body
        cv2.circle(frame, (x, y), size // 3, (50, 50, 50), -1)
        
        # Arms and rotors
        for angle in [45, 135, 225, 315]:
            rad = np.radians(angle)
            arm_x = int(x + size * 0.6 * np.cos(rad))
            arm_y = int(y + size * 0.6 * np.sin(rad))
            cv2.line(frame, (x, y), (arm_x, arm_y), (80, 80, 80), 2)
            cv2.circle(frame, (arm_x, arm_y), size // 5, (100, 100, 100), -1)
        
        # Calculate YOLO format bbox (normalized)
        x1 = max(0, x - size) / w
        y1 = max(0, y - size) / h
        x2 = min(w, x + size) / w
        y2 = min(h, y + size) / h
        
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        bw = x2 - x1
        bh = y2 - y1
        
        return frame, [0, cx, cy, bw, bh]  # class_id, cx, cy, w, h
    
    def generate_synthetic_bird(
        self,
        frame: np.ndarray,
        x: int,
        y: int,
        size: int = 20
    ) -> Tuple[np.ndarray, List[float]]:
        """Draw a synthetic bird on the frame."""
        h, w = frame.shape[:2]
        
        # Simple bird shape
        pts = np.array([
            [x - size, y],
            [x - size // 2, y - size // 3],
            [x, y],
            [x + size // 2, y - size // 3],
            [x + size, y]
        ], np.int32)
        cv2.polylines(frame, [pts], False, (30, 30, 30), 2)
        
        # Bbox
        x1 = max(0, x - size) / w
        y1 = max(0, y - size // 2) / h
        x2 = min(w, x + size) / w
        y2 = min(h, y + size // 2) / h
        
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        bw = x2 - x1
        bh = y2 - y1
        
        return frame, [1, cx, cy, bw, bh]  # bird class
    
    def generate_sky_background(self, width: int = 640, height: int = 480) -> np.ndarray:
        """Generate a sky-like background."""
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Gradient sky
        for y in range(height):
            blue = int(200 - y * 0.3)
            green = int(180 - y * 0.2)
            red = int(150 - y * 0.1)
            frame[y, :] = [max(0, blue), max(0, green), max(0, red)]
        
        # Add clouds
        for _ in range(random.randint(2, 5)):
            cx = random.randint(0, width)
            cy = random.randint(0, height // 2)
            for _ in range(random.randint(3, 7)):
                ox = cx + random.randint(-50, 50)
                oy = cy + random.randint(-20, 20)
                cv2.circle(frame, (ox, oy), random.randint(20, 40), (220, 220, 230), -1)
        
        # Add noise
        noise = np.random.randint(0, 15, (height, width, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        return frame
    
    def generate_dataset(self, num_train: int = 500, num_val: int = 100):
        """Generate synthetic training dataset."""
        self.setup_directories()
        
        print(f"Generating {num_train} training images...")
        self._generate_split("train", num_train)
        
        print(f"Generating {num_val} validation images...")
        self._generate_split("val", num_val)
        
        # Create dataset YAML
        self._create_yaml()
        
        print(f"Dataset generated at {self.output_dir}")
    
    def _generate_split(self, split: str, num_images: int):
        """Generate images for a split."""
        for i in range(num_images):
            frame = self.generate_sky_background()
            labels = []
            
            # Add random number of objects
            num_drones = random.randint(0, 3)
            num_birds = random.randint(0, 2)
            
            for _ in range(num_drones):
                x = random.randint(50, 590)
                y = random.randint(50, 430)
                size = random.randint(30, 60)
                frame, label = self.generate_synthetic_drone(frame, x, y, size)
                labels.append(label)
            
            for _ in range(num_birds):
                x = random.randint(30, 610)
                y = random.randint(30, 450)
                size = random.randint(15, 30)
                frame, label = self.generate_synthetic_bird(frame, x, y, size)
                labels.append(label)
            
            # Save image
            img_path = self.images_dir / split / f"img_{i:05d}.jpg"
            cv2.imwrite(str(img_path), frame)
            
            # Save labels
            label_path = self.labels_dir / split / f"img_{i:05d}.txt"
            with open(label_path, "w") as f:
                for label in labels:
                    f.write(" ".join(map(str, label)) + "\n")
    
    def _create_yaml(self):
        """Create dataset YAML configuration."""
        config = {
            "path": str(self.output_dir.absolute()),
            "train": "images/train",
            "val": "images/val",
            "names": {i: name for i, name in enumerate(self.CLASSES)}
        }
        
        yaml_path = self.output_dir / "dataset.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return yaml_path


class DroneModelTrainer:
    """Train YOLO model for drone detection."""
    
    def __init__(
        self,
        base_model: str = "yolov8n.pt",
        output_dir: str = "models"
    ):
        self.base_model = base_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def train(
        self,
        dataset_yaml: str,
        epochs: int = 50,
        imgsz: int = 640,
        batch: int = 16,
        device: str = "cpu"
    ) -> str:
        """Train the YOLO model."""
        print(f"Loading base model: {self.base_model}")
        model = YOLO(self.base_model)
        
        print(f"Starting training for {epochs} epochs...")
        results = model.train(
            data=dataset_yaml,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            project=str(self.output_dir),
            name="drone_yolov8",
            exist_ok=True,
            verbose=True
        )
        
        # Copy best model to standard location
        best_model = self.output_dir / "drone_yolov8" / "weights" / "best.pt"
        final_model = self.output_dir / "drone_yolov8.pt"
        
        if best_model.exists():
            shutil.copy(best_model, final_model)
            print(f"Model saved to {final_model}")
            return str(final_model)
        
        return str(best_model)
    
    def export_model(self, model_path: str, format: str = "onnx"):
        """Export model to different format."""
        model = YOLO(model_path)
        model.export(format=format)


def quick_train():
    """Quick training with synthetic data for demo purposes."""
    # Generate dataset
    generator = DroneDatasetGenerator("datasets/drone_detection")
    generator.generate_dataset(num_train=100, num_val=20)
    
    # Train model
    trainer = DroneModelTrainer()
    model_path = trainer.train(
        dataset_yaml="datasets/drone_detection/dataset.yaml",
        epochs=10,
        batch=8,
        device="cpu"
    )
    
    return model_path


def full_train():
    """Full training with larger dataset."""
    # Generate dataset
    generator = DroneDatasetGenerator("datasets/drone_detection")
    generator.generate_dataset(num_train=1000, num_val=200)
    
    # Train model
    trainer = DroneModelTrainer()
    model_path = trainer.train(
        dataset_yaml="datasets/drone_detection/dataset.yaml",
        epochs=50,
        batch=16,
        device="cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
    )
    
    return model_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        full_train()
    else:
        quick_train()
