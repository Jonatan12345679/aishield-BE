import cv2
import numpy as np
import onnxruntime as ort


class PrivacyDetector:

    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )

    # pendeteksi privacy nya bedasarkan model
    def detect(self, image_bytes: bytes):

        img = cv2.imdecode(
            np.frombuffer(image_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        img = cv2.resize(
            img,
            (640, 640)
        )

        img = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2RGB
        )

        img = img.astype(np.float32) / 255.0

        img = np.transpose(
            img,
            (2, 0, 1)
        )

        img = np.expand_dims(
            img,
            axis=0
        )

        outputs = self.session.run(
            None,
            {"images": img}
        )

        detections = []

        for det in outputs[0][0]:

            x1, y1, x2, y2, conf, cls = det

            if conf < 0.5:
                continue

            detections.append({
                "bbox": [
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2)
                ],
                "confidence": float(conf),
                "class_id": int(cls)
            })

        return detections

    # digunakan untuk menglakukan pengebluran di image
    def blur_image(self, image_bytes: bytes):

        # tingkat ke yakinan jika ingin di blur
        CONFIDENCE_THRESHOLD = 0.4

        # White List yang digunakan jika hanya ingin melakukan blur
        # pada beberapa class saja
        # PRIVACY_CLASSES = {
        #     0,  # plat_nomor
        #     1,  # QR_CODE
        #     2,  # qr_code
        #     3,  # qrcode
        #     8   # ktp
        # }

        img = cv2.imdecode(
            np.frombuffer(image_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        original_h, original_w = img.shape[:2]

        resized = cv2.resize(
            img,
            (640, 640)
        )

        rgb = cv2.cvtColor(
            resized,
            cv2.COLOR_BGR2RGB
        )

        input_tensor = rgb.astype(np.float32) / 255.0

        input_tensor = np.transpose(
            input_tensor,
            (2, 0, 1)
        )

        input_tensor = np.expand_dims(
            input_tensor,
            axis=0
        )

        outputs = self.session.run(
            None,
            {"images": input_tensor}
        )

        detections = outputs[0][0]

        for det in detections:

            x1, y1, x2, y2, conf, cls = det

            if conf < CONFIDENCE_THRESHOLD:
                continue

            # if int(cls) not in PRIVACY_CLASSES:
            #     continue

            x1 = max(
                0,
                int(x1 / 640 * original_w)
            )

            y1 = max(
                0,
                int(y1 / 640 * original_h)
            )

            x2 = min(
                original_w,
                int(x2 / 640 * original_w)
            )

            y2 = min(
                original_h,
                int(y2 / 640 * original_h)
            )

            if x2 <= x1 or y2 <= y1:
                continue

            roi = img[y1:y2, x1:x2]

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

            img[y1:y2, x1:x2] = blurred

        _, buffer = cv2.imencode(
            ".jpg",
            img
        )

        return buffer.tobytes()