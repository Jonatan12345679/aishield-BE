import base64

import cv2
import numpy as np
import onnxruntime as ort


class PrivacyDetector:

    def __init__(
        self,
        model_path: str,
        class_name: str | None = None,
        threshold: float = 0.5,
        class_names: dict | None = None
    ):
        self.model_path = model_path
        self.class_name = class_name
        self.threshold = threshold

        # Digunakan apabila model mempunyai
        # beberapa class.
        #
        # Contoh:
        # 0 = ktp
        # 1 = struk
        self.class_names = class_names or {
            0: "ktp",
            1: "ktp",
            2: "struk",
        }

        self.session = ort.InferenceSession(
            model_path,
            providers=[
                "CPUExecutionProvider"
            ]
        )

    def _prepare_image(
        self,
        image_bytes: bytes
    ):
        img = cv2.imdecode(
            np.frombuffer(
                image_bytes,
                np.uint8
            ),
            cv2.IMREAD_COLOR
        )

        if img is None:
            raise ValueError(
                "Failed to decode image"
            )

        original_h, original_w = (
            img.shape[:2]
        )

        resized = cv2.resize(
            img,
            (640, 640)
        )

        rgb = cv2.cvtColor(
            resized,
            cv2.COLOR_BGR2RGB
        )

        tensor = (
            rgb.astype(np.float32)
            / 255.0
        )

        tensor = np.transpose(
            tensor,
            (2, 0, 1)
        )

        tensor = np.expand_dims(
            tensor,
            axis=0
        )

        return (
            img,
            original_w,
            original_h,
            tensor
        )

    def detect(
        self,
        image_bytes: bytes
    ):
        (
            _,
            original_w,
            original_h,
            tensor
        ) = self._prepare_image(
            image_bytes
        )

        outputs = self.session.run(
            None,
            {
                "images": tensor
            }
        )

        detections = []

        for det in outputs[0][0]:

            x1, y1, x2, y2, conf, cls = det

            confidence = float(conf)

            if confidence < self.threshold:
                continue

            # Class ID dari model ONNX
            class_id = int(cls)

            # Jika class_name diberikan,
            # berarti detector ini adalah
            # detector single-class lama.
            #
            # Jika tidak diberikan,
            # gunakan class dari model.
            if self.class_name is not None:

                class_name = (
                    self.class_name
                )

            else:

                class_name = (
                    self.class_names.get(
                        class_id,
                        f"class_{class_id}"
                    )
                )

            # Convert koordinat model
            # 640x640 ke ukuran gambar asli.
            x1 = max(
                0,
                int(
                    x1 /
                    640 *
                    original_w
                )
            )

            y1 = max(
                0,
                int(
                    y1 /
                    640 *
                    original_h
                )
            )

            x2 = min(
                original_w,
                int(
                    x2 /
                    640 *
                    original_w
                )
            )

            y2 = min(
                original_h,
                int(
                    y2 /
                    640 *
                    original_h
                )
            )

            if (
                x2 <= x1
                or y2 <= y1
            ):
                continue

            detections.append({
                "class": class_name,

                "class_id": class_id,

                "confidence": round(
                    confidence,
                    4
                ),

                "box": {
                    "x": x1,
                    "y": y1,
                    "width": (
                        x2 - x1
                    ),
                    "height": (
                        y2 - y1
                    )
                }
            })

        return detections


class MultiPrivacyDetector:

    def __init__(
        self,
        detectors: list[PrivacyDetector]
    ):
        self.detectors = detectors

    def detect(
        self,
        image_bytes: bytes
    ):
        detections = []

        for detector in self.detectors:

            detections.extend(
                detector.detect(
                    image_bytes
                )
            )

        return detections

    def detect_with_boxes(
        self,
        image_bytes: bytes
    ):
        detections = self.detect(
            image_bytes
        )

        img = cv2.imdecode(
            np.frombuffer(
                image_bytes,
                np.uint8
            ),
            cv2.IMREAD_COLOR
        )

        if img is None:
            raise ValueError(
                "Failed to decode image"
            )

        for detection in detections:

            box = detection["box"]

            x = box["x"]
            y = box["y"]

            width = box["width"]
            height = box["height"]

            class_name = (
                detection["class"]
            )

            confidence = (
                detection["confidence"]
            )

            cv2.rectangle(
                img,
                (x, y),
                (
                    x + width,
                    y + height
                ),
                (0, 0, 255),
                2
            )

            cv2.putText(
                img,
                (
                    f"{class_name} "
                    f"{confidence:.2f}"
                ),
                (
                    x,
                    max(
                        20,
                        y - 10
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

        _, buffer = cv2.imencode(
            ".jpg",
            img,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                98
            ]
        )

        image_base64 = (
            base64.b64encode(
                buffer.tobytes()
            ).decode("utf-8")
        )

        return {
            "detections": detections,
            "image": (
                "data:image/jpeg;base64,"
                f"{image_base64}"
            )
        }

    def blur_image(
        self,
        image_bytes: bytes
    ):
        img = cv2.imdecode(
            np.frombuffer(
                image_bytes,
                np.uint8
            ),
            cv2.IMREAD_COLOR
        )

        if img is None:
            raise ValueError(
                "Failed to decode image"
            )

        detections = self.detect(
            image_bytes
        )

        for detection in detections:

            box = detection["box"]

            x1 = box["x"]
            y1 = box["y"]

            x2 = (
                x1 +
                box["width"]
            )

            y2 = (
                y1 +
                box["height"]
            )

            roi = img[
                y1:y2,
                x1:x2
            ]

            if roi.size == 0:
                continue

            h = y2 - y1
            w = x2 - x1

            kernel = max(
                15,
                min(h, w) // 4
            )

            if kernel % 2 == 0:
                kernel += 1

            blurred = cv2.GaussianBlur(
                roi,
                (kernel, kernel),
                30
            )

            img[
                y1:y2,
                x1:x2
            ] = blurred

        _, buffer = cv2.imencode(
            ".jpg",
            img,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                98
            ]
        )

        image_base64 = (
            base64.b64encode(
                buffer.tobytes()
            ).decode("utf-8")
        )

        return (
            "data:image/jpeg;base64,"
            f"{image_base64}"
        )