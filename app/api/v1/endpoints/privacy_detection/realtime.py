from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

from app.services.realtime_detector import realtime_detector

router = APIRouter()


@router.post("/realtime")
async def realtime(
    image: UploadFile = File(...)
):
    image_bytes = await image.read()

    result = realtime_detector.detect_frame(
        image_bytes=image_bytes
    )

    return result