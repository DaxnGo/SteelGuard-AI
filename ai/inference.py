import os
import time
import logging
from typing import List, Optional

import cv2
import numpy as np
from ultralytics import YOLO

from app.schemas import BoundingBox, Detection

logger = logging.getLogger(__name__)

# Class name mapping for NEU-DET defect types
CLASS_NAMES = {
    0: "crazing",
    1: "inclusion",
    2: "patches",
    3: "pitted_surface",
    4: "rolled-in_scale",
    5: "scratches",
}


class ModelEngine:
    """Singleton YOLOv8 inference engine.

    Loads the model once at startup and reuses it for all predictions.
    Thread-safe for synchronous FastAPI usage.
    """

    _instance: Optional["ModelEngine"] = None

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.conf_threshold = float(os.getenv("CONF_THRESHOLD", "0.25"))
        self.iou_threshold = float(os.getenv("IOU_THRESHOLD", "0.45"))

        logger.info("Loading YOLOv8 model from %s ...", model_path)
        start = time.perf_counter()
        self.model = YOLO(model_path)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("Model loaded in %.1f ms", elapsed)

        # Override class names from model if available
        if hasattr(self.model, "names") and self.model.names:
            self.class_names = self.model.names
        else:
            self.class_names = CLASS_NAMES

        logger.info("Classes: %s", self.class_names)

    @classmethod
    def get_instance(cls, model_path: str = "") -> "ModelEngine":
        """Get or create the singleton model engine."""
        if cls._instance is None:
            if not model_path:
                model_path = os.getenv("MODEL_PATH", "/app/model/best.pt")
            cls._instance = cls(model_path)
        return cls._instance

    def predict(self, image_bytes: bytes) -> dict:
        """Run inference on raw image bytes.

        Args:
            image_bytes: Raw image file bytes.

        Returns:
            dict with keys: detections, inference_time_ms, image_width, image_height
        """
        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image. Ensure it is a valid image file.")

        h, w = img.shape[:2]

        # Run inference
        start = time.perf_counter()
        results = self.model.predict(
            source=img,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )
        inference_ms = (time.perf_counter() - start) * 1000

        # Parse detections
        detections: List[Detection] = []
        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes
                for i in range(len(boxes)):
                    xyxy = boxes.xyxy[i].tolist()
                    conf = float(boxes.conf[i])
                    cls_id = int(boxes.cls[i])
                    cls_name = self.class_names.get(cls_id, f"class_{cls_id}")

                    detections.append(
                        Detection(
                            class_id=cls_id,
                            class_name=cls_name,
                            confidence=round(conf, 4),
                            bbox=BoundingBox(
                                x_min=round(xyxy[0], 2),
                                y_min=round(xyxy[1], 2),
                                x_max=round(xyxy[2], 2),
                                y_max=round(xyxy[3], 2),
                            ),
                        )
                    )

        return {
            "detections": detections,
            "inference_time_ms": round(inference_ms, 2),
            "image_width": w,
            "image_height": h,
        }

    def predict_annotated(self, image_bytes: bytes) -> bytes:
        """Run inference and return annotated image as JPEG bytes.

        Args:
            image_bytes: Raw image file bytes.

        Returns:
            JPEG-encoded annotated image bytes.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image. Ensure it is a valid image file.")

        results = self.model.predict(
            source=img,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )

        # Draw annotations on image
        annotated = results[0].plot()

        # Encode as JPEG
        _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buffer.tobytes()
