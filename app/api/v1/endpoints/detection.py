from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi.responses import Response


from app.services.model_loader import detector

router = APIRouter()


@router.post("/scan")
async def scan(
    image: UploadFile = File(...)
):
    image_bytes = await image.read()

    result = detector.detect_with_boxes(
        image_bytes
    )

    return {
        "success": True,
        "message": "Privacy detection completed",
        "detections": result["detections"],
        "image": result["image"]
    }

@router.post("/blur")
async def blur(
    image: UploadFile = File(...)
):
    image_bytes = await image.read()

    result_image = detector.blur_image(
        image_bytes
    )

    return {
        "success": True,
        "message": "Privacy blur completed",
        "image": result_image
    }