"""
Meta SAM 3D Service via fal.ai API
Handles 2D image → 3D model conversion using Meta's SAM 3D Objects
https://fal.ai/models/fal-ai/sam-3/3d-objects
"""

import os
import asyncio
import logging
from pathlib import Path

import httpx
import trimesh

logger = logging.getLogger(__name__)


class SAM3DService:
    """
    Converts 2D images to 3D GLB models using Meta SAM 3D Objects via fal.ai API.
    Requires FAL_KEY environment variable.
    """

    FAL_ENDPOINT = "fal-ai/sam-3/3d-objects"

    def __init__(self):
        self.fal_key = os.environ.get("FAL_KEY", "")
        if not self.fal_key:
            logger.warning(
                "FAL_KEY not set! Set it in .env or environment. "
                "Get your key at https://fal.ai/dashboard/keys"
            )
        logger.info("SAM3D Service initialized (fal.ai API)")

    async def convert_2d_to_3d(
        self,
        image_path: str,
        output_path: str,
        prompt: str = "object",
        seed: int = 42,
    ) -> dict:
        """
        Convert a 2D image to a 3D GLB model.

        Args:
            image_path: Path to input image file
            output_path: Path to save the output .glb file
            prompt: Text prompt for auto-segmentation (e.g. "car", "chair")
            seed: Random seed for reproducibility

        Returns:
            dict with success, vertices_count, faces_count, model_path
        """
        if not self.fal_key:
            return {
                "success": False,
                "error": "FAL_KEY not configured. Get your key at https://fal.ai/dashboard/keys",
            }

        try:
            import fal_client

            logger.info(f"Converting {image_path} to 3D via fal.ai SAM 3D Objects...")

            # Step 1: Upload image to fal.ai storage
            image_url = await asyncio.to_thread(fal_client.upload_file, image_path)
            logger.info(f"Image uploaded to fal.ai: {image_url}")

            # Step 2: Call SAM 3D Objects API (try with low detection threshold first)
            result = await self._call_fal_api(
                fal_client, image_url, prompt, seed, detection_threshold=0.15
            )

            # If auto-segmentation fails, retry without prompt (use whole image)
            if result is None:
                logger.warning("Auto-segmentation failed, retrying without prompt...")
                result = await self._call_fal_api(
                    fal_client, image_url, None, seed, detection_threshold=0.05
                )

            if result is None:
                return {
                    "success": False,
                    "error": "SAM 3D could not detect objects in this image. Try a different image with a clearer subject.",
                }

            logger.info(f"SAM 3D API response keys: {list(result.keys())}")

            # Step 3: Extract GLB URL from response
            glb_url = self._extract_glb_url(result)
            if not glb_url:
                return {
                    "success": False,
                    "error": "No GLB model in SAM 3D response. Check image quality or prompt.",
                }

            # Step 4: Download GLB file
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(glb_url)
                resp.raise_for_status()
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(resp.content)

            logger.info(f"GLB downloaded ({len(resp.content)} bytes) → {output_path}")

            # Step 5: Get mesh statistics
            vertices_count, faces_count = self._get_mesh_stats(output_path)

            return {
                "success": True,
                "vertices_count": vertices_count,
                "faces_count": faces_count,
                "model_path": output_path,
            }

        except ImportError:
            logger.error("fal-client not installed. Run: pip install fal-client")
            return {"success": False, "error": "fal-client package not installed"}

        except Exception as e:
            logger.error(f"SAM 3D conversion failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _call_fal_api(self, fal_client, image_url, prompt, seed, detection_threshold=0.15):
        """Call fal.ai SAM 3D API with given parameters. Returns result dict or None on failure."""
        try:
            arguments = {
                "image_url": image_url,
                "seed": seed,
                "export_textured_glb": True,
                "detection_threshold": detection_threshold,
            }
            if prompt:
                arguments["prompt"] = prompt

            def _run():
                return fal_client.subscribe(
                    self.FAL_ENDPOINT,
                    arguments=arguments,
                    with_logs=True,
                )

            return await asyncio.to_thread(_run)
        except Exception as e:
            error_msg = str(e)
            if "no masks" in error_msg.lower() or "Auto-segmentation" in error_msg:
                logger.warning(f"SAM 3D segmentation failed: {error_msg}")
                return None
            raise

    def _extract_glb_url(self, result: dict) -> str | None:
        """Extract the best GLB URL from fal.ai response."""
        # Try individual GLBs first (per-object, higher quality)
        individual_glbs = result.get("individual_glbs")
        if individual_glbs and len(individual_glbs) > 0:
            first = individual_glbs[0]
            if isinstance(first, dict) and "url" in first:
                return first["url"]
            if isinstance(first, str):
                return first

        # Try combined model GLB
        model_glb = result.get("model_glb")
        if model_glb:
            if isinstance(model_glb, dict) and "url" in model_glb:
                return model_glb["url"]
            if isinstance(model_glb, str):
                return model_glb

        return None

    def _get_mesh_stats(self, glb_path: str) -> tuple[int, int]:
        """Read mesh statistics from a GLB file."""
        try:
            mesh = trimesh.load(glb_path)
            vertices = 0
            faces = 0

            if isinstance(mesh, trimesh.Scene):
                for geom in mesh.geometry.values():
                    if hasattr(geom, "vertices"):
                        vertices += len(geom.vertices)
                    if hasattr(geom, "faces"):
                        faces += len(geom.faces)
            elif hasattr(mesh, "vertices"):
                vertices = len(mesh.vertices)
                faces = len(mesh.faces) if hasattr(mesh, "faces") else 0

            return vertices, faces
        except Exception as e:
            logger.warning(f"Could not read mesh stats: {e}")
            return 0, 0
