from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi.responses import Response

from app.services.model_loader import detector

router = APIRouter()


@router.post("/detect")
async def detect(
    file: UploadFile = File(...)
):
    image_bytes = await file.read()

    results = detector.detect(
        image_bytes
    )

    return {
        "count": len(results),
        "detections": results
    }


@router.post("/blur")
async def blur(
    file: UploadFile = File(...)
):
    image_bytes = await file.read()

    result = detector.blur_image(
        image_bytes
    )

    return Response(
        content=result,
        media_type="image/jpeg"
    )