"""
Stage Node API Router
Handles 2D → 3D conversion and rendering endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
import os
from pathlib import Path
from datetime import datetime
import logging

from services.sam3d_service import SAM3DService
from services.render_service import RenderService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
sam3d_service = SAM3DService()
render_service = RenderService()

STORAGE_DIR = Path("storage")

# Request/Response models
class ConvertRequest(BaseModel):
    image_base64: str
    node_id: str
    user_id: str | None = None
    prompt: str = "object"  # Text prompt for SAM 3D auto-segmentation

class ConvertResponse(BaseModel):
    success: bool
    model_id: str
    model_url: str
    preview_url: str
    vertices_count: int | None = None
    faces_count: int | None = None
    message: str | None = None

class RenderRequest(BaseModel):
    model_id: str
    pitch: float
    yaw: float
    distance: float
    resolution: dict = {"width": 1024, "height": 1024}

class RenderResponse(BaseModel):
    success: bool
    image_base64: str
    render_time_ms: int
    message: str | None = None


@router.post("/convert", response_model=ConvertResponse)
async def convert_2d_to_3d(request: ConvertRequest):
    """
    Convert 2D image to 3D model using Meta SAM 3D

    Args:
        request: ConvertRequest with base64 image data

    Returns:
        ConvertResponse with model URL and metadata
    """
    try:
        logger.info(f"Converting image for node {request.node_id}")

        # Decode base64 image
        if "," in request.image_base64:
            # Remove data:image/...;base64, prefix
            image_data = request.image_base64.split(",")[1]
        else:
            image_data = request.image_base64

        image_bytes = base64.b64decode(image_data)

        # Generate unique model ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"model_{request.node_id}_{timestamp}"

        # Save uploaded image
        upload_path = STORAGE_DIR / "uploads" / f"{model_id}.png"
        with open(upload_path, "wb") as f:
            f.write(image_bytes)

        logger.info(f"Saved upload to {upload_path}")

        # Convert to 3D via SAM 3D
        model_path = STORAGE_DIR / "models" / f"{model_id}.glb"
        result = await sam3d_service.convert_2d_to_3d(
            image_path=str(upload_path),
            output_path=str(model_path),
            prompt=request.prompt,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"3D conversion failed: {result.get('error', 'Unknown error')}"
            )

        # Generate preview image
        preview_path = STORAGE_DIR / "renders" / f"{model_id}_preview.png"
        preview_result = await render_service.render_angle(
            str(model_path),
            str(preview_path),
            pitch=12,
            yaw=32,
            distance=2.8,
            resolution=(512, 512)
        )

        # Get base URL (from environment or use localhost)
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")

        return ConvertResponse(
            success=True,
            model_id=model_id,
            model_url=f"{base_url}/models/{model_id}.glb",
            preview_url=f"{base_url}/renders/{model_id}_preview.png",
            vertices_count=result.get("vertices_count"),
            faces_count=result.get("faces_count"),
            message="Conversion successful"
        )

    except Exception as e:
        logger.error(f"Conversion error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Conversion failed: {str(e)}"
        )


@router.post("/render", response_model=RenderResponse)
async def render_3d_model(request: RenderRequest):
    """
    Render 3D model at specific angle

    Args:
        request: RenderRequest with model ID and camera parameters

    Returns:
        RenderResponse with rendered image in base64
    """
    try:
        logger.info(f"Rendering model {request.model_id} at pitch={request.pitch}, yaw={request.yaw}")

        # Find model file
        model_path = STORAGE_DIR / "models" / f"{request.model_id}.glb"

        if not model_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {request.model_id}"
            )

        # Generate unique render filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        render_filename = f"{request.model_id}_p{int(request.pitch)}_y{int(request.yaw)}_{timestamp}.png"
        render_path = STORAGE_DIR / "renders" / render_filename

        # Render
        start_time = datetime.now()

        result = await render_service.render_angle(
            str(model_path),
            str(render_path),
            pitch=request.pitch,
            yaw=request.yaw,
            distance=request.distance,
            resolution=(request.resolution["width"], request.resolution["height"])
        )

        render_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Rendering failed: {result.get('error', 'Unknown error')}"
            )

        # Read rendered image and convert to base64
        with open(render_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"

        return RenderResponse(
            success=True,
            image_base64=image_base64,
            render_time_ms=render_time_ms,
            message="Rendering successful"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rendering error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Rendering failed: {str(e)}"
        )


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    """
    Serve 3D model file for preview

    Args:
        model_id: Model identifier

    Returns:
        FileResponse with .glb file
    """
    model_path = STORAGE_DIR / "models" / f"{model_id}.glb"

    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not found")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(model_path),
        media_type="model/gltf-binary",
        filename=f"{model_id}.glb"
    )