import cv2
import numpy as np

from app.services.model_loader import detector


class RealtimeDetector:

    def detect_frame(
        self,
        image_bytes: bytes
    ):
        results = detector.detect(
            image_bytes=image_bytes
        )

        return results


realtime_detector = RealtimeDetector()