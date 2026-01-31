"""YOLO-based drone detection with cross-screen tracking."""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid
import math
from collections import defaultdict

from .config import settings
from .models import BoundingBox, Detection, CrossScreenTrack


class CrossScreenTracker:
    """Tracks objects across multiple video streams with gap prediction."""
    
    def __init__(self, num_screens: int = 6, grid_cols: int = 3):
        self.num_screens = num_screens
        self.grid_cols = grid_cols
        self.tracks: Dict[int, CrossScreenTrack] = {}
        self.next_track_id = 0
        self.screen_positions = self._calculate_screen_positions()
        self.velocity_history: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
        self.last_positions: Dict[int, Dict[int, Tuple[float, float, datetime]]] = defaultdict(dict)
        
    def _calculate_screen_positions(self) -> Dict[int, Dict[str, int]]:
        """Calculate logical positions of each screen in the grid."""
        positions = {}
        for i in range(self.num_screens):
            row = i // self.grid_cols
            col = i % self.grid_cols
            positions[i] = {"row": row, "col": col}
        return positions
    
    def _get_adjacent_screens(self, screen_id: int) -> List[int]:
        """Get screens adjacent to the given screen."""
        pos = self.screen_positions[screen_id]
        adjacent = []
        
        # Check all 8 directions
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_row = pos["row"] + dr
                new_col = pos["col"] + dc
                
                # Find screen at this position
                for sid, spos in self.screen_positions.items():
                    if spos["row"] == new_row and spos["col"] == new_col:
                        adjacent.append(sid)
                        break
        
        return adjacent
    
    def _predict_exit_direction(
        self, 
        bbox: BoundingBox, 
        velocity: Tuple[float, float],
        frame_width: int,
        frame_height: int
    ) -> Optional[str]:
        """Predict which edge the object will exit from."""
        cx = (bbox.x1 + bbox.x2) / 2
        cy = (bbox.y1 + bbox.y2) / 2
        vx, vy = velocity
        
        if abs(vx) < 1 and abs(vy) < 1:
            return None
        
        # Calculate time to reach each edge
        times = {}
        
        if vx > 0:
            times["right"] = (frame_width - cx) / vx
        elif vx < 0:
            times["left"] = -cx / vx
            
        if vy > 0:
            times["bottom"] = (frame_height - cy) / vy
        elif vy < 0:
            times["top"] = -cy / vy
        
        if not times:
            return None
            
        return min(times, key=times.get)
    
    def _direction_to_screen(self, current_screen: int, direction: str) -> Optional[int]:
        """Convert exit direction to target screen ID."""
        pos = self.screen_positions[current_screen]
        
        direction_map = {
            "left": (0, -1),
            "right": (0, 1),
            "top": (-1, 0),
            "bottom": (1, 0),
        }
        
        if direction not in direction_map:
            return None
            
        dr, dc = direction_map[direction]
        new_row = pos["row"] + dr
        new_col = pos["col"] + dc
        
        for sid, spos in self.screen_positions.items():
            if spos["row"] == new_row and spos["col"] == new_col:
                return sid
        
        return None
    
    def update_track(
        self,
        track_id: int,
        screen_id: int,
        bbox: BoundingBox,
        frame_width: int,
        frame_height: int
    ) -> CrossScreenTrack:
        """Update or create a track with new detection."""
        now = datetime.utcnow()
        cx = (bbox.x1 + bbox.x2) / 2
        cy = (bbox.y1 + bbox.y2) / 2
        
        # Calculate velocity from history
        velocity = (0.0, 0.0)
        if track_id in self.last_positions and screen_id in self.last_positions[track_id]:
            last_x, last_y, last_time = self.last_positions[track_id][screen_id]
            dt = (now - last_time).total_seconds()
            if dt > 0:
                velocity = ((cx - last_x) / dt, (cy - last_y) / dt)
                self.velocity_history[track_id].append(velocity)
                # Keep only last 10 velocity samples
                self.velocity_history[track_id] = self.velocity_history[track_id][-10:]
        
        # Average velocity for smoother prediction
        if self.velocity_history[track_id]:
            avg_vx = sum(v[0] for v in self.velocity_history[track_id]) / len(self.velocity_history[track_id])
            avg_vy = sum(v[1] for v in self.velocity_history[track_id]) / len(self.velocity_history[track_id])
            velocity = (avg_vx, avg_vy)
        
        self.last_positions[track_id][screen_id] = (cx, cy, now)
        
        # Predict next screens
        predicted_screens = []
        exit_dir = self._predict_exit_direction(bbox, velocity, frame_width, frame_height)
        if exit_dir:
            next_screen = self._direction_to_screen(screen_id, exit_dir)
            if next_screen is not None:
                predicted_screens.append(next_screen)
        
        # Create detection
        detection = Detection(
            id=str(uuid.uuid4()),
            timestamp=now,
            stream_id=screen_id,
            bounding_box=bbox,
            velocity={"vx": velocity[0], "vy": velocity[1]},
            predicted_next_screen=predicted_screens[0] if predicted_screens else None
        )
        
        if track_id not in self.tracks:
            self.tracks[track_id] = CrossScreenTrack(
                track_id=track_id,
                detections=[detection],
                current_screen=screen_id,
                predicted_screens=predicted_screens,
                velocity_vector={"vx": velocity[0], "vy": velocity[1]},
                last_seen=now,
                total_screens_crossed=0
            )
        else:
            track = self.tracks[track_id]
            # Check if screen changed
            if track.current_screen != screen_id:
                track.total_screens_crossed += 1
            track.detections.append(detection)
            track.current_screen = screen_id
            track.predicted_screens = predicted_screens
            track.velocity_vector = {"vx": velocity[0], "vy": velocity[1]}
            track.last_seen = now
            # Keep only last 100 detections per track
            track.detections = track.detections[-100:]
        
        return self.tracks[track_id]
    
    def predict_entry_point(
        self,
        track_id: int,
        target_screen: int,
        frame_width: int,
        frame_height: int
    ) -> Optional[Tuple[float, float]]:
        """Predict where an object will enter a target screen."""
        if track_id not in self.tracks:
            return None
            
        track = self.tracks[track_id]
        if not track.detections:
            return None
        
        last_detection = track.detections[-1]
        source_screen = last_detection.stream_id
        
        source_pos = self.screen_positions[source_screen]
        target_pos = self.screen_positions[target_screen]
        
        # Determine entry edge based on relative positions
        dr = target_pos["row"] - source_pos["row"]
        dc = target_pos["col"] - source_pos["col"]
        
        # Calculate entry point
        last_bbox = last_detection.bounding_box
        cx = (last_bbox.x1 + last_bbox.x2) / 2
        cy = (last_bbox.y1 + last_bbox.y2) / 2
        
        entry_x, entry_y = frame_width / 2, frame_height / 2
        
        if dc < 0:  # Entering from right
            entry_x = frame_width
            entry_y = cy
        elif dc > 0:  # Entering from left
            entry_x = 0
            entry_y = cy
        elif dr < 0:  # Entering from bottom
            entry_x = cx
            entry_y = frame_height
        elif dr > 0:  # Entering from top
            entry_x = cx
            entry_y = 0
        
        return (entry_x, entry_y)
    
    def get_active_tracks(self, max_age_seconds: float = 5.0) -> List[CrossScreenTrack]:
        """Get all tracks that have been seen recently."""
        now = datetime.utcnow()
        active = []
        for track in self.tracks.values():
            age = (now - track.last_seen).total_seconds()
            if age <= max_age_seconds:
                active.append(track)
        return active


class DroneDetector:
    """YOLO-based drone detector with cross-screen tracking."""
    
    # Classes we care about for drone detection
    DRONE_CLASSES = ["drone", "quadcopter", "uav", "aircraft", "helicopter", "bird"]
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.model: Optional[YOLO] = None
        self.tracker = CrossScreenTracker(
            num_screens=settings.MAX_VIDEO_STREAMS,
            grid_cols=3
        )
        self.detection_count = 0
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model, falling back to pretrained if custom not found."""
        try:
            self.model = YOLO(self.model_path)
            print(f"Loaded custom model from {self.model_path}")
        except Exception:
            # Fall back to pretrained YOLOv8
            print("Custom model not found, using pretrained YOLOv8n")
            self.model = YOLO("yolov8n.pt")
    
    def detect(
        self,
        frame: np.ndarray,
        stream_id: int,
        track: bool = True
    ) -> List[Detection]:
        """Run detection on a frame."""
        if self.model is None:
            return []
        
        # Run YOLO inference with tracking
        if track:
            results = self.model.track(
                frame,
                persist=True,
                conf=settings.YOLO_CONFIDENCE_THRESHOLD,
                iou=settings.YOLO_IOU_THRESHOLD,
                verbose=False
            )
        else:
            results = self.model(
                frame,
                conf=settings.YOLO_CONFIDENCE_THRESHOLD,
                iou=settings.YOLO_IOU_THRESHOLD,
                verbose=False
            )
        
        detections = []
        frame_height, frame_width = frame.shape[:2]
        
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for i, box in enumerate(boxes):
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.model.names[cls_id]
                
                # Get track ID if available
                track_id = None
                if hasattr(box, 'id') and box.id is not None:
                    track_id = int(box.id[0].cpu().numpy())
                else:
                    track_id = self.detection_count
                    self.detection_count += 1
                
                bbox = BoundingBox(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    confidence=conf,
                    class_name=cls_name,
                    track_id=track_id
                )
                
                # Update cross-screen tracker
                cross_track = self.tracker.update_track(
                    track_id=track_id,
                    screen_id=stream_id,
                    bbox=bbox,
                    frame_width=frame_width,
                    frame_height=frame_height
                )
                
                # Generate simulated coordinates
                lat, lon = self._generate_coordinates(stream_id, bbox, frame_width, frame_height)
                
                detection = Detection(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    stream_id=stream_id,
                    bounding_box=bbox,
                    latitude=lat,
                    longitude=lon,
                    altitude=100 + np.random.uniform(-20, 20),
                    velocity=cross_track.velocity_vector,
                    predicted_next_screen=cross_track.predicted_screens[0] if cross_track.predicted_screens else None,
                    metadata={
                        "total_screens_crossed": cross_track.total_screens_crossed,
                        "track_history_length": len(cross_track.detections)
                    }
                )
                detections.append(detection)
        
        return detections
    
    def _generate_coordinates(
        self,
        stream_id: int,
        bbox: BoundingBox,
        frame_width: int,
        frame_height: int
    ) -> Tuple[float, float]:
        """Generate simulated GPS coordinates based on screen position and bbox."""
        # Base coordinates offset by stream position
        row = stream_id // 3
        col = stream_id % 3
        
        base_lat = settings.DEFAULT_LAT + (row * settings.COORDINATE_VARIANCE)
        base_lon = settings.DEFAULT_LON + (col * settings.COORDINATE_VARIANCE)
        
        # Offset within frame
        cx = (bbox.x1 + bbox.x2) / 2 / frame_width
        cy = (bbox.y1 + bbox.y2) / 2 / frame_height
        
        lat = base_lat + (cy - 0.5) * settings.COORDINATE_VARIANCE
        lon = base_lon + (cx - 0.5) * settings.COORDINATE_VARIANCE
        
        return lat, lon
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        show_predictions: bool = True
    ) -> np.ndarray:
        """Draw detection boxes and tracking info on frame."""
        annotated = frame.copy()
        
        for det in detections:
            bbox = det.bounding_box
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)
            
            # Color based on class
            color = (0, 255, 0)  # Green default
            if "drone" in bbox.class_name.lower() or "aircraft" in bbox.class_name.lower():
                color = (0, 0, 255)  # Red for drones
            elif "person" in bbox.class_name.lower():
                color = (255, 0, 0)  # Blue for people
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Label with track ID and class
            label = f"ID:{bbox.track_id} {bbox.class_name} {bbox.confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
            cv2.putText(annotated, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Draw velocity vector
            if det.velocity and show_predictions:
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                vx = det.velocity.get("vx", 0) * 0.5  # Scale for visibility
                vy = det.velocity.get("vy", 0) * 0.5
                end_x = int(cx + vx)
                end_y = int(cy + vy)
                cv2.arrowedLine(annotated, (cx, cy), (end_x, end_y), (255, 255, 0), 2)
            
            # Show predicted next screen
            if det.predicted_next_screen is not None and show_predictions:
                pred_text = f"-> Screen {det.predicted_next_screen}"
                cv2.putText(annotated, pred_text, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
        
        return annotated
    
    def get_cross_screen_tracks(self) -> List[CrossScreenTrack]:
        """Get all active cross-screen tracks."""
        return self.tracker.get_active_tracks()
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
