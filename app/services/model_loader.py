from app.core.config import settings
from app.services.privacy_detector import (
    PrivacyDetector,
    MultiPrivacyDetector
)

detector = MultiPrivacyDetector([
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_KTP_PATH,
        "ktp",
        threshold=0.80
    ),
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_PLAT_NOMOR_PATH,
        "plat_nomor",
        threshold=0.80
    ),
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_QR_CODE_PATH,
        "qr_code",
        threshold=0.90
    ),
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_STRUK_PATH,
        "struk",
        threshold=0.90
    )
])