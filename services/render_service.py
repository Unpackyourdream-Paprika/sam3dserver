"""
3D Rendering Service
Renders 3D GLB models at specific camera angles.

Renderer priority:
  1. pyrender (high-quality, requires OpenGL / EGL on headless Linux)
  2. matplotlib (works everywhere, wireframe-style)
  3. mock (simple placeholder image)
"""

import math
import logging
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path

import trimesh

logger = logging.getLogger(__name__)


def _detect_renderer() -> str:
    """Detect the best available renderer."""
    try:
        import pyrender  # noqa: F401
        return "pyrender"
    except ImportError:
        pass

    try:
        import matplotlib  # noqa: F401
        return "matplotlib"
    except ImportError:
        pass

    return "mock"


class RenderService:
    def __init__(self):
        self.renderer = _detect_renderer()
        logger.info(f"Render Service initialized (renderer: {self.renderer})")

    async def render_angle(
        self,
        model_path: str,
        output_path: str,
        pitch: float = 12.0,
        yaw: float = 32.0,
        distance: float = 2.8,
        resolution: tuple = (1024, 1024),
    ) -> dict:
        """
        Render a 3D model at the given camera angle.

        Args:
            model_path: Path to .glb file
            output_path: Where to save the rendered PNG
            pitch: Camera elevation in degrees
            yaw: Camera azimuth in degrees
            distance: Camera distance from origin
            resolution: (width, height)

        Returns:
            dict with success status
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            if self.renderer == "pyrender":
                image = self._pyrender_render(model_path, pitch, yaw, distance, resolution)
            elif self.renderer == "matplotlib":
                image = self._matplotlib_render(model_path, pitch, yaw, distance, resolution)
            else:
                image = self._mock_render(resolution, pitch, yaw)

            image.save(output_path)
            logger.info(f"Rendered {model_path} → {output_path} (renderer={self.renderer})")
            return {"success": True, "output_path": output_path}

        except Exception as e:
            logger.error(f"Rendering failed: {e}", exc_info=True)
            # Fallback to mock on any error
            try:
                image = self._mock_render(resolution, pitch, yaw)
                image.save(output_path)
                logger.warning("Fell back to mock renderer")
                return {"success": True, "output_path": output_path}
            except Exception:
                return {"success": False, "error": str(e)}

    # ── pyrender renderer ────────────────────────────────────────────

    def _pyrender_render(
        self,
        model_path: str,
        pitch: float,
        yaw: float,
        distance: float,
        resolution: tuple,
    ) -> Image.Image:
        import pyrender

        scene = pyrender.Scene(
            bg_color=[0.15, 0.15, 0.15, 1.0],
            ambient_light=[0.3, 0.3, 0.3],
        )

        # Load mesh
        mesh_or_scene = trimesh.load(model_path)
        if isinstance(mesh_or_scene, trimesh.Scene):
            for geom in mesh_or_scene.geometry.values():
                if hasattr(geom, "vertices"):
                    scene.add(pyrender.Mesh.from_trimesh(geom))
        else:
            scene.add(pyrender.Mesh.from_trimesh(mesh_or_scene))

        # Camera
        camera = pyrender.PerspectiveCamera(yfov=math.radians(60))
        camera_pose = self._camera_pose(pitch, yaw, distance)
        scene.add(camera, pose=camera_pose)

        # Directional light from camera position
        light = pyrender.DirectionalLight(color=np.ones(3), intensity=4.0)
        scene.add(light, pose=camera_pose)

        # Render
        w, h = resolution
        renderer = pyrender.OffscreenRenderer(w, h)
        color, _ = renderer.render(scene)
        renderer.delete()

        return Image.fromarray(color)

    # ── matplotlib renderer ──────────────────────────────────────────

    def _matplotlib_render(
        self,
        model_path: str,
        pitch: float,
        yaw: float,
        distance: float,
        resolution: tuple,
    ) -> Image.Image:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        from io import BytesIO

        mesh_or_scene = trimesh.load(model_path)

        # Collect all geometry
        geometries = []
        if isinstance(mesh_or_scene, trimesh.Scene):
            for geom in mesh_or_scene.geometry.values():
                if hasattr(geom, "vertices") and hasattr(geom, "faces"):
                    geometries.append(geom)
        elif hasattr(mesh_or_scene, "vertices"):
            geometries.append(mesh_or_scene)

        w, h = resolution
        dpi = 100
        fig = plt.figure(figsize=(w / dpi, h / dpi), dpi=dpi)
        ax = fig.add_subplot(111, projection="3d")

        # Collect all vertices for auto-scaling
        all_verts = []

        for geom in geometries:
            verts = geom.vertices
            faces = geom.faces
            all_verts.append(verts)

            # Get face colors if available
            face_color = "steelblue"
            edge_color = (0.2, 0.2, 0.2, 0.1)

            if hasattr(geom, "visual") and hasattr(geom.visual, "face_colors"):
                try:
                    fc = geom.visual.face_colors
                    if fc is not None and len(fc) > 0:
                        face_color = fc[:, :3] / 255.0
                except Exception:
                    pass

            polys = [[verts[idx] for idx in face] for face in faces]
            poly_col = Poly3DCollection(polys, alpha=0.9)
            poly_col.set_facecolor(face_color)
            poly_col.set_edgecolor(edge_color)
            ax.add_collection3d(poly_col)

        # Auto-scale axes
        if all_verts:
            combined = np.concatenate(all_verts, axis=0)
            mid = combined.mean(axis=0)
            max_range = np.ptp(combined, axis=0).max() / 2 * 1.2
            ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
            ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
            ax.set_zlim(mid[2] - max_range, mid[2] + max_range)

        ax.view_init(elev=pitch, azim=yaw)
        ax.set_facecolor((0.15, 0.15, 0.15))
        fig.set_facecolor((0.15, 0.15, 0.15))
        ax.axis("off")

        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)

        return Image.open(buf).convert("RGB")

    # ── mock renderer (final fallback) ───────────────────────────────

    def _mock_render(
        self,
        resolution: tuple,
        pitch: float,
        yaw: float,
    ) -> Image.Image:
        w, h = resolution
        image = Image.new("RGB", (w, h), color=(40, 40, 40))
        draw = ImageDraw.Draw(image)

        cx, cy = w // 2, h // 2
        r = min(w, h) // 4
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(80, 120, 160), outline=(120, 160, 200), width=3)
        draw.text((20, 20), f"Pitch: {pitch:.1f}\nYaw: {yaw:.1f}\n(mock)", fill=(255, 255, 255))

        return image

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _camera_pose(pitch_deg: float, yaw_deg: float, distance: float) -> np.ndarray:
        """Build a 4x4 camera pose matrix from pitch/yaw/distance."""
        pitch = math.radians(pitch_deg)
        yaw = math.radians(yaw_deg)

        # Spherical → Cartesian
        x = distance * math.cos(pitch) * math.sin(yaw)
        y = distance * math.sin(pitch)
        z = distance * math.cos(pitch) * math.cos(yaw)

        eye = np.array([x, y, z])
        target = np.array([0.0, 0.0, 0.0])
        up = np.array([0.0, 1.0, 0.0])

        # Look-at matrix
        forward = target - eye
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, up)
        right = right / (np.linalg.norm(right) + 1e-8)
        cam_up = np.cross(right, forward)

        pose = np.eye(4)
        pose[:3, 0] = right
        pose[:3, 1] = cam_up
        pose[:3, 2] = -forward
        pose[:3, 3] = eye

        return pose
