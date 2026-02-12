"""
Image-to-3D Service via fal.ai API
Handles 2D image → 3D model conversion using TripoSR
https://fal.ai/models/fal-ai/triposr
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
    Converts 2D images to 3D GLB models using TripoSR via fal.ai API.
    Requires FAL_KEY environment variable.
    """

    FAL_ENDPOINT = "fal-ai/triposr"

    def __init__(self):
        self.fal_key = os.environ.get("FAL_KEY", "")
        if not self.fal_key:
            logger.warning(
                "FAL_KEY not set! Set it in .env or environment. "
                "Get your key at https://fal.ai/dashboard/keys"
            )
        logger.info("Image-to-3D Service initialized (fal.ai TripoSR)")

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
            prompt: Unused (kept for API compatibility)
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

            logger.info(f"Converting {image_path} to 3D via fal.ai TripoSR...")

            # Step 1: Upload image to fal.ai storage
            image_url = await asyncio.to_thread(fal_client.upload_file, image_path)
            logger.info(f"Image uploaded to fal.ai: {image_url}")

            # Step 2: Call TripoSR API
            arguments = {
                "image_url": image_url,
                "output_format": "glb",
                "do_remove_background": True,
                "foreground_ratio": 0.9,
                "mc_resolution": 256,
            }

            def _run():
                return fal_client.subscribe(
                    self.FAL_ENDPOINT,
                    arguments=arguments,
                    with_logs=True,
                )

            result = await asyncio.to_thread(_run)

            logger.info(f"TripoSR API response keys: {list(result.keys())}")

            # Step 3: Extract GLB URL from response
            glb_url = self._extract_glb_url(result)
            if not glb_url:
                return {
                    "success": False,
                    "error": "No 3D model in TripoSR response.",
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
            logger.error(f"3D conversion failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _extract_glb_url(self, result: dict) -> str | None:
        """Extract GLB URL from fal.ai TripoSR response."""
        # TripoSR returns model_mesh as a File object with url
        model_mesh = result.get("model_mesh")
        if model_mesh:
            if isinstance(model_mesh, dict) and "url" in model_mesh:
                return model_mesh["url"]
            if isinstance(model_mesh, str):
                return model_mesh

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
