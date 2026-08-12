from app.core.config import settings
from app.services.privacy_detector import (
    PrivacyDetector,
    MultiPrivacyDetector
)

detector = MultiPrivacyDetector([
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_KTP_PATH,
        "ktp"
    ),
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_PLAT_NOMOR_PATH,
        "plat_nomor"
    ),
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_QR_CODE_PATH,
        "qr_code"
    ),
    PrivacyDetector(
        settings.MODEL_PRIVACY_DETECTION_STRUK_PATH,
        "struk"
    )
])