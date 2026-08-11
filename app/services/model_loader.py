from app.core.config import settings
from app.services.privacy_detector import PrivacyDetector

detector = PrivacyDetector(
    settings.MODEL_PRIVACY_DETECTION_PATH
)