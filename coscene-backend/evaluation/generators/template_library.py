"""
Template library for USD operations.
Defines primitives, materials, transforms, and operations for procedural scene generation.
"""
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import math


# ============ Color Definitions ============

COLORS = {
    'red': (1.0, 0.0, 0.0),
    'green': (0.0, 1.0, 0.0),
    'blue': (0.0, 0.0, 1.0),
    'yellow': (1.0, 1.0, 0.0),
    'cyan': (0.0, 1.0, 1.0),
    'magenta': (1.0, 0.0, 1.0),
    'white': (1.0, 1.0, 1.0),
    'black': (0.0, 0.0, 0.0),
    'orange': (1.0, 0.5, 0.0),
    'purple': (0.5, 0.0, 0.5),
    'gray': (0.5, 0.5, 0.5),
    'brown': (0.6, 0.3, 0.0),
}

COLOR_NAMES = list(COLORS.keys())


# ============ Primitive Definitions ============

@dataclass
class PrimitiveTemplate:
    """Template for a USD primitive type."""
    type_name: str
    usd_type: str
    default_params: Dict[str, Any]
    supported_positions: List[Tuple[float, float, float]]
    supported_scales: List[float]
    supported_colors: List[str]


# Primitive type templates
PRIMITIVES = {
    'sphere': PrimitiveTemplate(
        type_name='Sphere',
        usd_type='Sphere',
        default_params={'radius': 1.0},
        supported_positions=[
            (0, 0, 0),  # center
            (2, 0, 0),  # right
            (-2, 0, 0),  # left
            (0, 2, 0),  # front
            (0, -2, 0),  # back
            (0, 0, 2),  # top
            (0, 0, -2),  # bottom
        ],
        supported_scales=[0.5, 1.0, 1.5, 2.0],
        supported_colors=COLOR_NAMES,
    ),
    'cube': PrimitiveTemplate(
        type_name='Cube',
        usd_type='Cube',
        default_params={'size': 2.0},
        supported_positions=[
            (0, 0, 0),
            (2, 0, 0),
            (-2, 0, 0),
            (0, 2, 0),
            (0, -2, 0),
            (0, 0, 2),
            (0, 0, -2),
        ],
        supported_scales=[0.5, 1.0, 1.5, 2.0],
        supported_colors=COLOR_NAMES,
    ),
    'cylinder': PrimitiveTemplate(
        type_name='Cylinder',
        usd_type='Cylinder',
        default_params={'height': 2.0, 'radius': 1.0},
        supported_positions=[
            (0, 0, 0),
            (2, 0, 0),
            (-2, 0, 0),
            (0, 2, 0),
            (0, -2, 0),
        ],
        supported_scales=[0.5, 1.0, 1.5, 2.0],
        supported_colors=COLOR_NAMES,
    ),
    'cone': PrimitiveTemplate(
        type_name='Cone',
        usd_type='Cone',
        default_params={'height': 2.0, 'radius': 1.0},
        supported_positions=[
            (0, 0, 0),
            (2, 0, 0),
            (-2, 0, 0),
        ],
        supported_scales=[0.5, 1.0, 1.5, 2.0],
        supported_colors=COLOR_NAMES,
    ),
}


# ============ Material Templates ============

@dataclass
class MaterialTemplate:
    """Template for USD material properties."""
    metallic: float
    roughness: float


MATERIAL_PRESETS = {
    'default': MaterialTemplate(metallic=0.0, roughness=0.5),
    'shiny': MaterialTemplate(metallic=1.0, roughness=0.0),
    'matte': MaterialTemplate(metallic=0.0, roughness=1.0),
    'metallic': MaterialTemplate(metallic=1.0, roughness=0.3),
}


# ============ Position Descriptors ============

POSITION_DESCRIPTORS = {
    (0, 0, 0): ['at the center', 'in the middle', 'at the origin', 'at position (0,0,0)'],
    (2, 0, 0): ['to the right', '2 units right', 'on the right side', 'at position (2,0,0)'],
    (-2, 0, 0): ['to the left', '2 units left', 'on the left side', 'at position (-2,0,0)'],
    (0, 2, 0): ['in front', '2 units forward', 'at the front', 'at position (0,2,0)'],
    (0, -2, 0): ['in back', '2 units back', 'at the back', 'at position (0,-2,0)'],
    (0, 0, 2): ['above', '2 units up', 'on top', 'at position (0,0,2)'],
    (0, 0, -2): ['below', '2 units down', 'at the bottom', 'at position (0,0,-2)'],
}

RELATIVE_POSITIONS = {
    'next to': (2, 0, 0),
    'above': (0, 0, 2),
    'below': (0, 0, -2),
    'in front of': (0, 2, 0),
    'behind': (0, -2, 0),
    'to the left of': (-2, 0, 0),
    'to the right of': (2, 0, 0),
}


# ============ Operation Templates ============

@dataclass
class OperationTemplate:
    """Template for a USD edit operation."""
    operation_type: str
    description: str
    complexity: str  # 'simple', 'medium', 'complex'
    required_params: List[str]
    optional_params: List[str]


OPERATIONS = {
    'add_primitive': OperationTemplate(
        operation_type='add_primitive',
        description='Add a new primitive object to the scene',
        complexity='simple',
        required_params=['primitive_type', 'color', 'position'],
        optional_params=['scale', 'material_preset'],
    ),
    'change_color': OperationTemplate(
        operation_type='change_color',
        description='Change the color of an existing object',
        complexity='simple',
        required_params=['object_name', 'new_color'],
        optional_params=[],
    ),
    'move_object': OperationTemplate(
        operation_type='move_object',
        description='Move an object to a new position',
        complexity='medium',
        required_params=['object_name', 'new_position'],
        optional_params=[],
    ),
    'scale_object': OperationTemplate(
        operation_type='scale_object',
        description='Change the scale of an object',
        complexity='medium',
        required_params=['object_name', 'new_scale'],
        optional_params=[],
    ),
    'rotate_object': OperationTemplate(
        operation_type='rotate_object',
        description='Rotate an object',
        complexity='medium',
        required_params=['object_name', 'rotation_degrees'],
        optional_params=['axis'],
    ),
    'delete_object': OperationTemplate(
        operation_type='delete_object',
        description='Remove an object from the scene',
        complexity='simple',
        required_params=['object_name'],
        optional_params=[],
    ),
    'add_multiple_objects': OperationTemplate(
        operation_type='add_multiple_objects',
        description='Add multiple objects at once',
        complexity='medium',
        required_params=['objects'],  # List of object specs
        optional_params=[],
    ),
    'create_pattern': OperationTemplate(
        operation_type='create_pattern',
        description='Create a pattern of objects (grid, circle, etc.)',
        complexity='complex',
        required_params=['pattern_type', 'primitive_type', 'count'],
        optional_params=['spacing', 'color'],
    ),
}


# ============ USD Generation Helpers ============

def generate_usd_header() -> str:
    """Generate standard USD header."""
    return """#usda 1.0
(
    defaultPrim = "World"
    upAxis = "Z"
)

def Xform "World"
{
"""


def generate_usd_footer() -> str:
    """Generate USD footer."""
    return "}\n"


def generate_sphere_usd(name: str, color: Tuple[float, float, float],
                        position: Tuple[float, float, float] = (0, 0, 0),
                        scale: float = 1.0, radius: float = 1.0,
                        metallic: float = 0.0, roughness: float = 0.5) -> str:
    """Generate USD code for a sphere."""
    r, g, b = color
    x, y, z = position

    return f"""    def Sphere "{name}"
    {{
        double radius = {radius}
        double3 xformOp:translate = ({x}, {y}, {z})
        double3 xformOp:scale = ({scale}, {scale}, {scale})
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

        def Material "Material"
        {{
            token outputs:surface.connect = </World/{name}/Material/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({r}, {g}, {b})
                float inputs:metallic = {metallic}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}
    }}
"""


def generate_cube_usd(name: str, color: Tuple[float, float, float],
                      position: Tuple[float, float, float] = (0, 0, 0),
                      scale: float = 1.0, size: float = 2.0,
                      metallic: float = 0.0, roughness: float = 0.5) -> str:
    """Generate USD code for a cube."""
    r, g, b = color
    x, y, z = position

    return f"""    def Cube "{name}"
    {{
        double size = {size}
        double3 xformOp:translate = ({x}, {y}, {z})
        double3 xformOp:scale = ({scale}, {scale}, {scale})
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

        def Material "Material"
        {{
            token outputs:surface.connect = </World/{name}/Material/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({r}, {g}, {b})
                float inputs:metallic = {metallic}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}
    }}
"""


def generate_cylinder_usd(name: str, color: Tuple[float, float, float],
                          position: Tuple[float, float, float] = (0, 0, 0),
                          scale: float = 1.0, height: float = 2.0, radius: float = 1.0,
                          metallic: float = 0.0, roughness: float = 0.5) -> str:
    """Generate USD code for a cylinder."""
    r, g, b = color
    x, y, z = position

    return f"""    def Cylinder "{name}"
    {{
        double height = {height}
        double radius = {radius}
        double3 xformOp:translate = ({x}, {y}, {z})
        double3 xformOp:scale = ({scale}, {scale}, {scale})
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

        def Material "Material"
        {{
            token outputs:surface.connect = </World/{name}/Material/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({r}, {g}, {b})
                float inputs:metallic = {metallic}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}
    }}
"""


def generate_cone_usd(name: str, color: Tuple[float, float, float],
                      position: Tuple[float, float, float] = (0, 0, 0),
                      scale: float = 1.0, height: float = 2.0, radius: float = 1.0,
                      metallic: float = 0.0, roughness: float = 0.5) -> str:
    """Generate USD code for a cone."""
    r, g, b = color
    x, y, z = position

    return f"""    def Cone "{name}"
    {{
        double height = {height}
        double radius = {radius}
        double3 xformOp:translate = ({x}, {y}, {z})
        double3 xformOp:scale = ({scale}, {scale}, {scale})
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

        def Material "Material"
        {{
            token outputs:surface.connect = </World/{name}/Material/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({r}, {g}, {b})
                float inputs:metallic = {metallic}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}
    }}
"""


# ============ Helper Functions ============

def get_color_rgb(color_name: str) -> Tuple[float, float, float]:
    """Get RGB tuple for a color name."""
    return COLORS.get(color_name.lower(), COLORS['white'])


def get_position_descriptors(position: Tuple[float, float, float]) -> List[str]:
    """Get natural language descriptors for a position."""
    return POSITION_DESCRIPTORS.get(position, [f'at position {position}'])


def get_relative_offset(relation: str) -> Tuple[float, float, float]:
    """Get position offset for a relative position descriptor."""
    return RELATIVE_POSITIONS.get(relation, (0, 0, 0))


def check_collision(pos1: Tuple[float, float, float],
                    pos2: Tuple[float, float, float],
                    min_distance: float = 1.5) -> bool:
    """
    Check if two positions are too close (collision).

    Args:
        pos1: First position (x, y, z)
        pos2: Second position (x, y, z)
        min_distance: Minimum allowed distance

    Returns:
        True if collision detected, False otherwise
    """
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
    return distance < min_distance


def generate_grid_positions(rows: int, cols: int, spacing: float = 2.0,
                            center: Tuple[float, float, float] = (0, 0, 0)) -> List[Tuple[float, float, float]]:
    """
    Generate positions for a grid pattern.

    Args:
        rows: Number of rows
        cols: Number of columns
        spacing: Distance between adjacent positions
        center: Center point of the grid

    Returns:
        List of (x, y, z) positions
    """
    positions = []
    start_x = center[0] - (cols - 1) * spacing / 2
    start_y = center[1] - (rows - 1) * spacing / 2

    for row in range(rows):
        for col in range(cols):
            x = start_x + col * spacing
            y = start_y + row * spacing
            z = center[2]
            positions.append((x, y, z))

    return positions


def generate_circle_positions(num_objects: int, radius: float = 3.0,
                              center: Tuple[float, float, float] = (0, 0, 0)) -> List[Tuple[float, float, float]]:
    """
    Generate positions for a circle pattern.

    Args:
        num_objects: Number of objects to place in circle
        radius: Radius of the circle
        center: Center point of the circle

    Returns:
        List of (x, y, z) positions
    """
    positions = []
    angle_step = 2 * math.pi / num_objects

    for i in range(num_objects):
        angle = i * angle_step
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        z = center[2]
        positions.append((x, y, z))

    return positions


def generate_line_positions(num_objects: int, spacing: float = 2.0,
                            direction: str = 'horizontal',
                            center: Tuple[float, float, float] = (0, 0, 0)) -> List[Tuple[float, float, float]]:
    """
    Generate positions for a line pattern.

    Args:
        num_objects: Number of objects to place in line
        spacing: Distance between adjacent objects
        direction: 'horizontal', 'vertical', or 'diagonal'
        center: Center point of the line

    Returns:
        List of (x, y, z) positions
    """
    positions = []
    start_offset = -(num_objects - 1) * spacing / 2

    for i in range(num_objects):
        offset = start_offset + i * spacing
        if direction == 'horizontal':
            pos = (center[0] + offset, center[1], center[2])
        elif direction == 'vertical':
            pos = (center[0], center[1] + offset, center[2])
        elif direction == 'diagonal':
            pos = (center[0] + offset, center[1] + offset, center[2])
        else:
            pos = (center[0] + offset, center[1], center[2])
        positions.append(pos)

    return positions


def get_random_safe_position(existing_positions: List[Tuple[float, float, float]],
                             candidate_positions: List[Tuple[float, float, float]],
                             min_distance: float = 1.5) -> Tuple[float, float, float]:
    """
    Get a random position that doesn't collide with existing objects.

    Args:
        existing_positions: List of occupied positions
        candidate_positions: List of potential positions to choose from
        min_distance: Minimum allowed distance between objects

    Returns:
        Safe position, or (0, 0, 0) if no safe position found
    """
    import random
    for pos in candidate_positions:
        safe = True
        for existing_pos in existing_positions:
            if check_collision(pos, existing_pos, min_distance):
                safe = False
                break
        if safe:
            return pos

    # If no safe position found, return first candidate
    return candidate_positions[0] if candidate_positions else (0, 0, 0)


# For testing
if __name__ == "__main__":
    # Test USD generation
    print("Testing USD generation...")
    print(generate_usd_header())
    print(generate_sphere_usd("RedSphere", get_color_rgb("red"), position=(0, 0, 0)))
    print(generate_cube_usd("BlueCube", get_color_rgb("blue"), position=(2, 0, 0)))
    print(generate_usd_footer())
