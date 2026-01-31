"""Video stream processing with multi-stream support."""

import cv2
import numpy as np
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import threading
import queue
from dataclasses import dataclass
import base64

from .config import settings
from .models import StreamConfig, Detection


@dataclass
class FrameData:
    """Container for frame data."""
    frame: np.ndarray
    stream_id: int
    timestamp: datetime
    frame_number: int


class VideoStream:
    """Single video stream handler."""
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.frame_queue: queue.Queue = queue.Queue(maxsize=10)
        self.thread: Optional[threading.Thread] = None
        self.frame_count = 0
        self.fps = 30
        self.width = 640
        self.height = 480
    
    def start(self) -> bool:
        """Start the video stream."""
        if self.config.source == "webcam":
            self.cap = cv2.VideoCapture(0)
        elif self.config.source.startswith("rtsp://") or self.config.source.startswith("http"):
            self.cap = cv2.VideoCapture(self.config.source)
        elif self.config.source == "simulated":
            # Simulated stream - generate synthetic frames
            self.cap = None
            self.running = True
            self.thread = threading.Thread(target=self._simulated_capture_loop, daemon=True)
            self.thread.start()
            return True
        else:
            # File path
            self.cap = cv2.VideoCapture(self.config.source)
        
        if self.cap is not None:
            if not self.cap.isOpened():
                return False
            
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
        
        return True
    
    def _capture_loop(self):
        """Background thread for capturing frames."""
        while self.running and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret:
                # Loop video file
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            self.frame_count += 1
            
            # Skip frames for performance
            if self.frame_count % settings.FRAME_SKIP != 0:
                continue
            
            # Resize for consistency
            frame = cv2.resize(frame, (640, 480))
            
            frame_data = FrameData(
                frame=frame,
                stream_id=self.config.stream_id,
                timestamp=datetime.utcnow(),
                frame_number=self.frame_count
            )
            
            try:
                self.frame_queue.put_nowait(frame_data)
            except queue.Full:
                # Drop oldest frame
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame_data)
                except queue.Empty:
                    pass
    
    def _simulated_capture_loop(self):
        """Generate simulated drone footage."""
        # Create a moving object simulation
        obj_x, obj_y = 100, 100
        vel_x, vel_y = 5, 3
        
        while self.running:
            # Create frame with gradient background (sky-like)
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            for y in range(480):
                blue = int(200 - y * 0.3)
                frame[y, :] = [blue, blue + 20, blue + 50]
            
            # Add some noise for realism
            noise = np.random.randint(0, 20, (480, 640, 3), dtype=np.uint8)
            frame = cv2.add(frame, noise)
            
            # Draw simulated drone (quadcopter shape)
            obj_x += vel_x + np.random.randint(-2, 3)
            obj_y += vel_y + np.random.randint(-2, 3)
            
            # Bounce off edges or exit to simulate cross-screen
            if obj_x < 0 or obj_x > 640:
                vel_x = -vel_x
                obj_x = max(0, min(640, obj_x))
            if obj_y < 0 or obj_y > 480:
                vel_y = -vel_y
                obj_y = max(0, min(480, obj_y))
            
            # Draw drone body
            cv2.circle(frame, (int(obj_x), int(obj_y)), 15, (50, 50, 50), -1)
            # Draw arms
            for angle in [45, 135, 225, 315]:
                rad = np.radians(angle)
                arm_x = int(obj_x + 25 * np.cos(rad))
                arm_y = int(obj_y + 25 * np.sin(rad))
                cv2.line(frame, (int(obj_x), int(obj_y)), (arm_x, arm_y), (80, 80, 80), 3)
                # Rotors
                cv2.circle(frame, (arm_x, arm_y), 8, (100, 100, 100), -1)
            
            # Add timestamp overlay
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cv2.putText(frame, f"Stream {self.config.stream_id} | {timestamp}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            self.frame_count += 1
            
            frame_data = FrameData(
                frame=frame,
                stream_id=self.config.stream_id,
                timestamp=datetime.utcnow(),
                frame_number=self.frame_count
            )
            
            try:
                self.frame_queue.put_nowait(frame_data)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame_data)
                except queue.Empty:
                    pass
            
            # Control frame rate
            import time
            time.sleep(1/30)
    
    def get_frame(self) -> Optional[FrameData]:
        """Get the latest frame."""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop(self):
        """Stop the video stream."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()


class MultiStreamProcessor:
    """Manages multiple video streams for the 6-screen grid."""
    
    def __init__(self, detector):
        self.streams: Dict[int, VideoStream] = {}
        self.detector = detector
        self.running = False
        self.callbacks: List[Callable[[int, np.ndarray, List[Detection]], Any]] = []
        self.latest_frames: Dict[int, np.ndarray] = {}
        self.latest_detections: Dict[int, List[Detection]] = {}
    
    def add_stream(self, config: StreamConfig) -> bool:
        """Add a video stream."""
        if config.stream_id in self.streams:
            self.streams[config.stream_id].stop()
        
        stream = VideoStream(config)
        if stream.start():
            self.streams[config.stream_id] = stream
            return True
        return False
    
    def remove_stream(self, stream_id: int):
        """Remove a video stream."""
        if stream_id in self.streams:
            self.streams[stream_id].stop()
            del self.streams[stream_id]
    
    def add_callback(self, callback: Callable[[int, np.ndarray, List[Detection]], Any]):
        """Add a callback for processed frames."""
        self.callbacks.append(callback)
    
    async def process_streams(self):
        """Process all streams and run detection."""
        self.running = True
        
        while self.running:
            for stream_id, stream in self.streams.items():
                if not stream.config.active:
                    continue
                
                frame_data = stream.get_frame()
                if frame_data is None:
                    continue
                
                # Run detection
                detections = self.detector.detect(
                    frame_data.frame,
                    stream_id=stream_id,
                    track=True
                )
                
                # Draw detections
                annotated_frame = self.detector.draw_detections(
                    frame_data.frame,
                    detections,
                    show_predictions=True
                )
                
                # Store latest
                self.latest_frames[stream_id] = annotated_frame
                self.latest_detections[stream_id] = detections
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(stream_id, annotated_frame, detections)
                    except Exception as e:
                        print(f"Callback error: {e}")
            
            await asyncio.sleep(0.01)  # Small delay to prevent CPU overload
    
    def get_frame_base64(self, stream_id: int) -> Optional[str]:
        """Get latest frame as base64 encoded JPEG."""
        if stream_id not in self.latest_frames:
            return None
        
        frame = self.latest_frames[stream_id]
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buffer).decode('utf-8')
    
    def get_all_detections(self) -> List[Detection]:
        """Get all current detections across all streams."""
        all_detections = []
        for detections in self.latest_detections.values():
            all_detections.extend(detections)
        return all_detections
    
    def stop(self):
        """Stop all streams."""
        self.running = False
        for stream in self.streams.values():
            stream.stop()
    
    def initialize_simulated_streams(self):
        """Initialize 6 simulated streams for demo."""
        for i in range(6):
            config = StreamConfig(
                stream_id=i,
                source="simulated",
                name=f"Drone Cam {i + 1}",
                position={"row": i // 3, "col": i % 3},
                active=True
            )
            self.add_stream(config)
