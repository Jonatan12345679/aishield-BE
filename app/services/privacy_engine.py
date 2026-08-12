from app.services.model_loader import (
    ktp_detector,
    plat_nomor_detector,
    qr_code_detector,
    struk_detector,
)


class PrivacyEngine:

    def detect(self, image_bytes: bytes):

        detections = []

        detections.extend(
            ktp_detector.detect(image_bytes)
        )

        detections.extend(
            plat_nomor_detector.detect(image_bytes)
        )

        detections.extend(
            qr_code_detector.detect(image_bytes)
        )

        detections.extend(
            struk_detector.detect(image_bytes)
        )

        return detections


privacy_engine = PrivacyEngine()