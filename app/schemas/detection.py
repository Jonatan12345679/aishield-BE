from pydantic import BaseModel


class DetectionResult(BaseModel):

    class_name: str

    confidence: float

    bbox: list[float]