import os
import time
import csv
from datetime import datetime

class TelemetryLogger:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(log_dir, f"session_{timestamp}.csv")
        
        self.file = open(self.filename, mode='w', newline='')
        self.writer = csv.writer(self.file)
        
        # Write CSV Header
        self.writer.writerow([
            "timestamp_iso", 
            "uptime_sec", 
            "target_color", 
            "is_detected", 
            "distance_cm", 
            "center_error_px", 
            "fsm_state", 
            "output_action",
            "yolo_confidence",
            "color_score",
            "combined_score"
        ])
        self.start_time = time.time()

    def log_step(
        self,
        target_color,
        is_detected,
        distance,
        error,
        fsm_state,
        action,
        yolo_confidence=None,
        color_score=None,
        combined_score=None,
    ):
        """
        Appends a single frame's data as a row in the CSV file safely.
        """
        now = datetime.now().isoformat()
        uptime = round(time.time() - self.start_time, 3)
        
        # Normalize missing numerics so the CSV doesn't break
        dist_val = round(distance, 2) if distance is not None else ""
        err_val = round(error, 2) if error is not None else ""
        yolo_val = round(yolo_confidence, 4) if yolo_confidence is not None else ""
        color_val = round(color_score, 4) if color_score is not None else ""
        combined_val = round(combined_score, 4) if combined_score is not None else ""

        self.writer.writerow([
            now, 
            uptime, 
            target_color, 
            is_detected, 
            dist_val, 
            err_val, 
            fsm_state, 
            action,
            yolo_val,
            color_val,
            combined_val,
        ])
        
        # Flush to disk immediately so data isn't lost if the rover crashes/loses power
        self.file.flush()

    def cleanup(self):
        self.file.close()
