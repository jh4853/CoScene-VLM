"""
USD (Universal Scene Descriptor) manipulation service.
Handles creating, parsing, and modifying USD scenes.
"""
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# ============ USD Templates ============

EMPTY_SCENE_TEMPLATE = """#usda 1.0
(
    defaultPrim = "World"
    upAxis = "Z"
)

def Xform "World"
{
}
"""

BASIC_SCENE_WITH_SPHERE_TEMPLATE = """#usda 1.0
(
    defaultPrim = "World"
    upAxis = "Z"
)

def Xform "World"
{
    def Sphere "Sphere"
    {
        double radius = 1.0
        double3 xformOp:translate = (0, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]

        def Material "DefaultMaterial"
        {
            token outputs:surface.connect = </World/Sphere/DefaultMaterial/Shader.outputs:surface>

            def Shader "Shader"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.8, 0.8, 0.8)
                float inputs:metallic = 0.0
                float inputs:roughness = 0.5
                token outputs:surface
            }
        }
    }
}
"""


# ============ USD Service Class ============

class USDService:
    """Service for USD scene manipulation."""

    def __init__(self):
        """Initialize USD service."""
        # Try to import USD libraries (may not be available in all environments)
        try:
            from pxr import Usd, UsdGeom, Sdf
            self.Usd = Usd
            self.UsdGeom = UsdGeom
            self.Sdf = Sdf
            self.usd_available = True
            logger.info("USD libraries loaded successfully")
        except ImportError as e:
            logger.warning(f"USD libraries not available: {e}")
            logger.warning("Using fallback string-based USD manipulation")
            self.usd_available = False

    def create_empty_scene(self) -> str:
        """Create an empty USD scene."""
        return EMPTY_SCENE_TEMPLATE

    def create_basic_scene(self) -> str:
        """Create a basic USD scene with a sphere."""
        return BASIC_SCENE_WITH_SPHERE_TEMPLATE

    def validate_usd(self, usd_content: str) -> tuple[bool, Optional[str]]:
        """
        Validate USD content.
        Returns (is_valid, error_message).
        """
        if not usd_content or not usd_content.strip():
            return False, "USD content is empty"

        # Basic syntax check
        if not usd_content.startswith("#usda"):
            return False, "USD content must start with #usda version declaration"

        if self.usd_available:
            # Try to parse with USD library
            try:
                # Create temporary layer from string
                layer = self.Sdf.Layer.CreateAnonymous()
                layer.ImportFromString(usd_content)
                return True, None
            except Exception as e:
                return False, f"USD parsing error: {str(e)}"
        else:
            # Basic string validation when USD not available
            required_elements = ["#usda", "def"]
            for element in required_elements:
                if element not in usd_content:
                    return False, f"Missing required element: {element}"

        return True, None

    def parse_scene_structure(self, usd_content: str) -> Dict[str, Any]:
        """
        Parse USD content and extract scene structure.
        Returns dict with prims, transforms, materials, etc.
        """
        structure = {
            "prims": [],
            "transforms": {},
            "materials": {},
            "metadata": {},
        }

        if not self.usd_available:
            # Fallback: simple text parsing
            lines = usd_content.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("def "):
                    # Extract prim definition
                    parts = line.split()
                    if len(parts) >= 3:
                        prim_type = parts[1]
                        prim_name = parts[2].strip('"')
                        structure["prims"].append({
                            "type": prim_type,
                            "name": prim_name,
                        })
            return structure

        # Use USD library for proper parsing
        try:
            layer = self.Sdf.Layer.CreateAnonymous()
            layer.ImportFromString(usd_content)
            stage = self.Usd.Stage.Open(layer)

            for prim in stage.Traverse():
                prim_path = str(prim.GetPath())
                structure["prims"].append({
                    "path": prim_path,
                    "type": prim.GetTypeName(),
                    "name": prim.GetName(),
                })

                # Extract transform if available
                if self.UsdGeom.Xformable(prim):
                    xformable = self.UsdGeom.Xformable(prim)
                    ops = xformable.GetOrderedXformOps()
                    structure["transforms"][prim_path] = [
                        str(op.GetOpName()) for op in ops]

        except Exception as e:
            logger.error(f"Error parsing USD structure: {e}")

        return structure

    def apply_patch(self, base_usd: str, patch_usd: str) -> str:
        """
        Apply USD patch to base scene.
        """
        # For now, we'll use a simple approach:
        # If patch contains complete scene, use it
        # Otherwise, attempt to merge (basic implementation)

        is_valid, error = self.validate_usd(patch_usd)
        if not is_valid:
            logger.error(f"Invalid USD patch: {error}")
            return base_usd  # Return base if patch is invalid

        # If patch has complete scene structure, use it
        if "def Xform \"World\"" in patch_usd:
            return patch_usd

        logger.warning("Patch merge not fully implemented, using patch as-is")
        return patch_usd

    def extract_objects(self, usd_content: str) -> list[Dict[str, Any]]:
        """
        Extract list of objects from USD scene.
        Used for object registry and reference resolution.
        """
        objects = []
        structure = self.parse_scene_structure(usd_content)

        for prim in structure.get("prims", []):
            # Filter out utility prims (materials, shaders, etc.)
            if prim.get("type") in ["Sphere", "Cube", "Cylinder", "Mesh", "Xform"]:
                objects.append({
                    "name": prim.get("name"),
                    "type": prim.get("type"),
                    "path": prim.get("path", prim.get("name")),
                })

        return objects

    def create_sphere(
        self,
        name: str = "Sphere",
        radius: float = 1.0,
        position: tuple[float, float, float] = (0, 0, 0),
        color: tuple[float, float, float] = (0.8, 0.8, 0.8)
    ) -> str:
        """Create USD for a sphere primitive."""
        return f"""#usda 1.0
(
    defaultPrim = "World"
    upAxis = "Z"
)

def Xform "World"
{{
    def Sphere "{name}"
    {{
        double radius = {radius}
        double3 xformOp:translate = ({position[0]}, {position[1]}, {position[2]})
        uniform token[] xformOpOrder = ["xformOp:translate"]

        def Material "Material"
        {{
            token outputs:surface.connect = </World/{name}/Material/Shader.outputs:surface>

            def Shader "Shader"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({color[0]}, {color[1]}, {color[2]})
                float inputs:metallic = 0.0
                float inputs:roughness = 0.5
                token outputs:surface
            }}
        }}
    }}
}}
"""


# Singleton instance
_usd_service_instance = None


def get_usd_service() -> USDService:
    """Get singleton USD service instance."""
    global _usd_service_instance
    if _usd_service_instance is None:
        _usd_service_instance = USDService()
    return _usd_service_instance
