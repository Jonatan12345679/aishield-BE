import base64
import cv2
import numpy as np
import onnxruntime as ort

class PrivacyDetector:

    CLASS_NAMES = {
        0: "plat-nomor",
        1: "QR_CODE",
        2: "qr_code",
        3: "qrcode",
        4: "daftar_barang",
        5: "struk_belanja",
        6: "total",
        7: "waktu",
        8: "ktp"
    }

    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )


    # pendeteksi privacy berdasarkan model
    def detect(self, image_bytes: bytes):

        original_img = cv2.imdecode(
            np.frombuffer(image_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        original_h, original_w = original_img.shape[:2]

        img = cv2.resize(
            original_img,
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

            x1 = int(x1 / 640 * original_w)
            y1 = int(y1 / 640 * original_h)

            x2 = int(x2 / 640 * original_w)
            y2 = int(y2 / 640 * original_h)

            detections.append({
                "class": self.CLASS_NAMES.get(
                    int(cls),
                    f"class_{int(cls)}"
                ),
                "confidence": round(
                    float(conf),
                    4
                ),
                "box": {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }
            })

        return detections


    def detect_with_boxes(self, image_bytes: bytes):
        detections = self.detect(
            image_bytes
        )

        img = cv2.imdecode(
            np.frombuffer(image_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        for detection in detections:

            box = detection["box"]

            x = box["x"]
            y = box["y"]

            width = box["width"]
            height = box["height"]

            class_name = detection["class"]

            confidence = detection["confidence"]

            cv2.rectangle(
                img,
                (x, y),
                (x + width, y + height),
                (0, 0, 255),
                2
            )

            cv2.putText(
                img,
                f"{class_name} {confidence:.2f}",
                (x, max(20, y - 10)),
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

        image_base64 = base64.b64encode(
            buffer
        ).decode("utf-8")

        return {
            "detections": detections,
            "image": f"data:image/jpeg;base64,{image_base64}"
        }

    
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
                img,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    98
                ]
            )

            image_base64 = base64.b64encode(
                buffer.tobytes()
            ).decode("utf-8")

            return f"data:image/jpeg;base64,{image_base64}"