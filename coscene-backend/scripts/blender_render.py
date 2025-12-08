"""
Blender Python script for headless rendering of USD scenes.
This script is executed by Blender in headless mode.

Usage:
    blender -b --python blender_render.py -- <usd_file> <output_file> [quality]
"""
import sys
import os
import math
import time

try:
    import bpy
    import mathutils
except ImportError:
    print("ERROR: This script must be run with Blender's Python interpreter")
    sys.exit(1)


def setup_scene():
    """Initialize clean Blender scene."""
    # Remove default objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Remove default lights
    for light in bpy.data.lights:
        bpy.data.lights.remove(light)

    # Set render engine to Cycles for better quality
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'CPU'  # Will be 'GPU' if available


def parse_usd_materials(usd_path: str):
    """
    Parse USD file to extract material definitions using the official USD API.

    This is more robust than regex parsing and handles all USD material patterns:
    1. Separate Material definitions with material:binding references
    2. Nested materials inside object definitions
    3. Inline primvars:displayColor on objects
    """
    materials = {}

    try:
        # Use the official USD library instead of regex parsing
        from pxr import Usd, UsdShade, UsdGeom, Gf

        # Open the USD stage
        stage = Usd.Stage.Open(usd_path)
        if not stage:
            print(f"ERROR: Could not open USD stage: {usd_path}")
            return materials

        # Iterate through all prims in the stage
        for prim in stage.Traverse():
            # Check if this is a geometric primitive we care about
            if not prim.IsA(UsdGeom.Gprim):
                continue

            prim_name = prim.GetName()
            color = None

            # Method 1: Check for primvars:displayColor (highest priority)
            gprim = UsdGeom.Gprim(prim)
            display_color_attr = gprim.GetDisplayColorAttr()
            if display_color_attr and display_color_attr.HasValue():
                colors = display_color_attr.Get()
                if colors and len(colors) > 0:
                    # displayColor can be an array, take the first color
                    rgb = colors[0]
                    color = (float(rgb[0]), float(rgb[1]), float(rgb[2]))
                    print(f"Found displayColor for '{prim_name}': {color}")

            # Method 2 & 3: Check material binding (handles both separate and nested materials)
            if not color:
                material_prim = None

                # Try method 2a: Explicit material binding (separate materials pattern)
                material_binding_api = UsdShade.MaterialBindingAPI(prim)
                bound_material = material_binding_api.ComputeBoundMaterial()[0]

                if bound_material and bound_material.GetPrim().IsValid():
                    material_prim = bound_material.GetPrim()
                    print(f"Found material binding for '{prim_name}'")

                # Try method 2b: Look for child Material (nested materials pattern)
                if not material_prim:
                    for child in prim.GetChildren():
                        if child.IsA(UsdShade.Material):
                            material_prim = child
                            print(f"Found nested material for '{prim_name}'")
                            break

                # Extract color from material if found
                if material_prim:
                    material = UsdShade.Material(material_prim)

                    # Get the surface shader
                    surface_output = material.GetSurfaceOutput()
                    if surface_output:
                        connected_source = surface_output.GetConnectedSource()
                        if connected_source:
                            shader = UsdShade.Shader(
                                connected_source[0].GetPrim())

                            # Get diffuseColor input
                            diffuse_input = shader.GetInput('diffuseColor')
                            if diffuse_input:
                                diffuse_value = diffuse_input.Get()
                                if diffuse_value:
                                    if isinstance(diffuse_value, Gf.Vec3f):
                                        color = (float(diffuse_value[0]),
                                                 float(diffuse_value[1]),
                                                 float(diffuse_value[2]))
                                        print(
                                            f"Found material color for '{prim_name}': {color}")

            if color:
                materials[prim_name] = color

        print(
            f"Successfully parsed {len(materials)} object materials using USD API")

    except ImportError:
        print("WARNING: USD library (pxr) not available, falling back to basic parsing")
        # Fallback to a simple regex-based parser if USD library is not available
        materials = _parse_usd_materials_fallback(usd_path)

    except Exception as e:
        print(f"Warning: Could not parse USD materials: {e}")
        import traceback
        traceback.print_exc()

    return materials


def _parse_usd_materials_fallback(usd_path: str):
    """
    Fallback regex-based parser for when USD library is not available.
    This is less robust but doesn't require external dependencies.
    """
    materials = {}
    import re

    try:
        with open(usd_path, 'r') as f:
            content = f.read()

        # Simple fallback: look for any diffuseColor in the file
        # and try to associate it with nearby object definitions
        # This is crude but better than nothing

        lines = content.split('\n')
        current_object = None

        for i, line in enumerate(lines):
            # Look for object definitions
            obj_match = re.match(
                r'\s*def\s+(Cylinder|Sphere|Cube|Mesh|Cone|Capsule)\s+"([^"]+)"', line)
            if obj_match:
                current_object = obj_match.group(2)

            # Look for colors within a reasonable window of the object
            if current_object:
                color_match = re.search(
                    r'inputs:diffuseColor\s*=\s*\(([^)]+)\)', line)
                if color_match:
                    values = [float(x.strip())
                              for x in color_match.group(1).split(',')]
                    if len(values) >= 3 and current_object not in materials:
                        materials[current_object] = tuple(values[:3])
                        print(
                            f"Fallback: Found color for '{current_object}': {materials[current_object]}")

        print(f"Fallback parser found {len(materials)} materials")

    except Exception as e:
        print(f"Fallback parser error: {e}")

    return materials


def apply_materials_to_meshes(materials_dict):
    """Apply materials to all mesh objects."""
    if not materials_dict:
        print("No materials found, using default colors")
        materials_dict = {'default': (0.8, 0.2, 0.2)}  # Red as fallback

    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            # Create material if not exists
            mat_name = f"{obj.name}_Material"
            mat = bpy.data.materials.get(mat_name)

            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True

            # Get BSDF node
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                # Try to find matching material by object name
                # Blender may import with exact name or with slight variations
                color = None

                # First try exact match
                if obj.name in materials_dict:
                    color = materials_dict[obj.name]
                else:
                    # Try partial match (Blender may add prefixes/suffixes)
                    for material_name, material_color in materials_dict.items():
                        if material_name in obj.name or obj.name in material_name:
                            color = material_color
                            break

                # Fallback to default if no match found
                if color is None:
                    color = materials_dict.get('default', (0.8, 0.2, 0.2))
                    print(
                        f"No material match for {obj.name}, using default color")

                bsdf.inputs['Base Color'].default_value = (*color, 1.0)
                bsdf.inputs['Metallic'].default_value = 0.0
                bsdf.inputs['Roughness'].default_value = 0.4
                print(f"Applied material to {obj.name} with color {color}")

            # Assign material to object
            if not obj.data.materials:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat


def import_usd(usd_path: str):
    """Import USD file into Blender."""
    if not os.path.exists(usd_path):
        print(f"ERROR: USD file not found: {usd_path}")
        return False

    try:
        # Parse materials from USD file first
        materials = parse_usd_materials(usd_path)

        # Blender 3.0+ has native USD import
        # USD uses centimeters by default, Blender uses meters
        # Scale factor of 100 converts cm to m, but USD seems to import at 0.01 scale
        bpy.ops.wm.usd_import(
            filepath=usd_path,
            import_materials=True,
            import_usd_preview=True,
            set_material_blend=True,
            scale=100.0  # Scale up to compensate for unit conversion
        )
        print(f"Successfully imported USD from {usd_path}")

        # Apply materials manually since Blender's importer doesn't always work
        apply_materials_to_meshes(materials)

        # Debug: Print what was imported
        print(f"Objects in scene: {len(bpy.data.objects)}")
        for obj in bpy.data.objects:
            print(f"  - {obj.name} (type: {obj.type})")
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat:
                        print(f"    Material: {mat.name}")

        return True
    except AttributeError:
        print("ERROR: USD import not available in this Blender version")
        print("Attempting to create simple scene as fallback...")
        create_fallback_scene()
        return True
    except Exception as e:
        print(f"ERROR importing USD: {e}")
        create_fallback_scene()
        return True


def create_fallback_scene():
    """Create a simple fallback scene if USD import fails."""
    # Add a simple sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
    sphere = bpy.context.active_object
    sphere.name = "Sphere"

    # Add material
    mat = bpy.data.materials.new(name="DefaultMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.5

    sphere.data.materials.append(mat)
    print("Created fallback sphere scene")


def setup_camera(
    location=(7.5, -7.5, 5.5),
    rotation_euler=(math.radians(63), 0, math.radians(46))
):
    """Setup camera with specific viewpoint."""
    camera_data = bpy.data.cameras.new(name='Camera')
    camera_object = bpy.data.objects.new('Camera', camera_data)
    bpy.context.scene.collection.objects.link(camera_object)

    camera_object.location = location
    camera_object.rotation_euler = rotation_euler

    bpy.context.scene.camera = camera_object
    print(f"Camera positioned at {location}")

    return camera_object


def calculate_scene_bounds():
    """
    Calculate the bounding box of all mesh objects in the scene.

    Returns:
        Tuple of (min_corner, max_corner, center, size) where:
        - min_corner: (x, y, z) minimum coordinates
        - max_corner: (x, y, z) maximum coordinates
        - center: (x, y, z) center of bounding box
        - size: (x, y, z) dimensions of bounding box
    """
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

    if not mesh_objects:
        print("WARNING: No mesh objects found in scene")
        return (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)

    # Initialize with first object's bounds
    first_obj = mesh_objects[0]
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    # Get world-space bounding box for all objects
    for obj in mesh_objects:
        # Get the 8 corners of the bounding box in world coordinates
        bbox_corners = [obj.matrix_world @
                        mathutils.Vector(corner) for corner in obj.bound_box]

        for corner in bbox_corners:
            min_x = min(min_x, corner.x)
            min_y = min(min_y, corner.y)
            min_z = min(min_z, corner.z)
            max_x = max(max_x, corner.x)
            max_y = max(max_y, corner.y)
            max_z = max(max_z, corner.z)

    min_corner = (min_x, min_y, min_z)
    max_corner = (max_x, max_y, max_z)
    center = ((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2)
    size = (max_x - min_x, max_y - min_y, max_z - min_z)

    print(f"Scene bounds: min={min_corner}, max={max_corner}")
    print(f"Scene center: {center}, size: {size}")

    return min_corner, max_corner, center, size


def calculate_camera_distance(bbox_size, angle, fov=50.0, padding=1.2):
    """
    Calculate appropriate camera distance to fit all objects in frame.

    Args:
        bbox_size: (x, y, z) dimensions of scene bounding box
        angle: Camera angle ('perspective', 'front', 'top', 'side')
        fov: Camera field of view in degrees
        padding: Multiplier for extra space (1.2 = 20% padding)

    Returns:
        Distance from scene center to camera
    """
    # Determine which dimensions matter for each view
    if angle == 'front':
        # Looking along Y axis, see X and Z
        relevant_size = max(bbox_size[0], bbox_size[2])
    elif angle == 'top':
        # Looking along Z axis, see X and Y
        relevant_size = max(bbox_size[0], bbox_size[1])
    elif angle == 'side':
        # Looking along X axis, see Y and Z
        relevant_size = max(bbox_size[1], bbox_size[2])
    else:  # perspective
        # Isometric view, consider all dimensions
        relevant_size = max(bbox_size)

    # Add some minimum size to avoid getting too close
    relevant_size = max(relevant_size, 1.0)

    # Calculate distance based on FOV
    # Distance = (size / 2) / tan(fov / 2)
    fov_rad = math.radians(fov)
    distance = (relevant_size / 2) / math.tan(fov_rad / 2)

    # Apply padding
    distance *= padding

    # Add some minimum distance
    distance = max(distance, 5.0)

    print(
        f"Camera '{angle}': bbox_size={bbox_size}, relevant_size={relevant_size:.2f}, distance={distance:.2f}")

    return distance


def setup_camera_angle(angle='perspective', auto_frame=True):
    """
    Setup camera for specific viewing angle.

    Args:
        angle: One of 'perspective', 'front', 'top', 'side'
        auto_frame: If True, automatically calculate distance to fit all objects

    Returns:
        Camera object
    """
    camera_data = bpy.data.cameras.new(name=f'Camera_{angle}')
    camera_object = bpy.data.objects.new(f'Camera_{angle}', camera_data)
    bpy.context.scene.collection.objects.link(camera_object)

    # Set camera FOV
    camera_data.lens_unit = 'FOV'
    camera_data.angle = math.radians(50.0)  # 50 degree FOV

    # Calculate scene bounds and appropriate distance
    if auto_frame:
        min_corner, max_corner, center, size = calculate_scene_bounds()
        distance = calculate_camera_distance(size, angle)
    else:
        center = (0, 0, 0)
        distance = 10.0

    # Define camera positions and rotations for each angle
    if angle == 'perspective':
        # Perspective view (isometric-ish) - offset from center
        offset_distance = distance * 0.75
        camera_object.location = (
            center[0] + offset_distance,
            center[1] - offset_distance,
            center[2] + offset_distance * 0.73
        )
        # Point camera at center
        direction = mathutils.Vector(
            center) - mathutils.Vector(camera_object.location)
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera_object.rotation_euler = rot_quat.to_euler()

    elif angle == 'front':
        # Front view (looking along +Y axis)
        camera_object.location = (center[0], center[1] - distance, center[2])
        camera_object.rotation_euler = (math.radians(90), 0, 0)

    elif angle == 'top':
        # Top view (looking down along -Z axis)
        camera_object.location = (center[0], center[1], center[2] + distance)
        camera_object.rotation_euler = (0, 0, 0)

    elif angle == 'side':
        # Side view (looking along +X axis)
        camera_object.location = (center[0] + distance, center[1], center[2])
        camera_object.rotation_euler = (math.radians(90), 0, math.radians(90))

    else:
        print(f"WARNING: Unknown camera angle '{angle}', using perspective")
        camera_object.location = (
            center[0] + 7.5, center[1] - 7.5, center[2] + 5.5)
        camera_object.rotation_euler = (math.radians(63), 0, math.radians(46))

    bpy.context.scene.camera = camera_object
    print(f"Camera '{angle}' positioned at {camera_object.location}")

    return camera_object


def setup_lighting(preset='default'):
    """Setup scene lighting."""
    # Add sun light with stronger energy
    light_data = bpy.data.lights.new(name="Sun", type='SUN')
    light_data.energy = 5.0  # Increased from 2.0
    light_object = bpy.data.objects.new(name="Sun", object_data=light_data)
    bpy.context.scene.collection.objects.link(light_object)
    light_object.location = (5, 5, 10)
    light_object.rotation_euler = (math.radians(45), 0, math.radians(45))

    # Add fill light with stronger energy
    fill_light_data = bpy.data.lights.new(name="Fill", type='AREA')
    fill_light_data.energy = 300  # Increased from 100
    fill_light_object = bpy.data.objects.new(
        name="Fill", object_data=fill_light_data)
    bpy.context.scene.collection.objects.link(fill_light_object)
    fill_light_object.location = (-5, -5, 5)

    # Set world background
    world = bpy.context.scene.world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get('Background')
    if bg_node:
        if preset == 'sunset':
            bg_node.inputs[0].default_value = (1.0, 0.6, 0.3, 1.0)
            bg_node.inputs[1].default_value = 1.5
        else:  # default - brighter background
            bg_node.inputs[0].default_value = (0.5, 0.5, 0.5, 1.0)
            bg_node.inputs[1].default_value = 1.0

    print(f"Lighting setup complete ({preset} preset)")


def configure_render_settings(quality='preview', width=512, height=512):
    """Configure render settings based on quality tier."""
    scene = bpy.context.scene

    # Resolution
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100

    # Quality presets
    if quality == 'preview':
        scene.cycles.samples = 32
        scene.cycles.max_bounces = 4
        # Disabled - Debian Blender lacks OpenImageDenoise
        scene.cycles.use_denoising = False
        # Tile size only for Blender < 4.0
        if hasattr(scene.render, 'tile_x'):
            scene.render.tile_x = 128
            scene.render.tile_y = 128
    elif quality == 'verification':
        scene.cycles.samples = 64
        scene.cycles.max_bounces = 6
        # Disabled - Debian Blender lacks OpenImageDenoise
        scene.cycles.use_denoising = False
        if hasattr(scene.render, 'tile_x'):
            scene.render.tile_x = 256
            scene.render.tile_y = 256
    elif quality == 'final':
        scene.cycles.samples = 256
        scene.cycles.max_bounces = 12
        # Disabled - Debian Blender lacks OpenImageDenoise
        scene.cycles.use_denoising = False
        if hasattr(scene.render, 'tile_x'):
            scene.render.tile_x = 256
            scene.render.tile_y = 256
    else:
        print(f"Unknown quality '{quality}', using preview")
        quality = 'preview'
        scene.cycles.samples = 32

    # Output format
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    print(
        f"Render settings: {quality} @ {width}x{height}, {scene.cycles.samples} samples")


def render(output_path: str):
    """Render scene to file."""
    scene = bpy.context.scene
    scene.render.filepath = output_path

    print(f"Starting render to {output_path}...")
    start_time = time.time()

    try:
        bpy.ops.render.render(write_still=True)
        render_time = int((time.time() - start_time) * 1000)
        print(f"Render complete in {render_time}ms")
        return render_time
    except Exception as e:
        print(f"ERROR during rendering: {e}")
        return -1


def main():
    """Main rendering pipeline."""
    # Parse command line arguments
    # Blender passes args after '--'
    try:
        argv = sys.argv
        argv = argv[argv.index("--") + 1:]  # Get args after --
    except ValueError:
        print("ERROR: No arguments provided after '--'")
        print(
            "Usage: blender -b --python blender_render.py -- <usd_file> <output_file> [quality] [camera_angle]")
        sys.exit(1)

    if len(argv) < 2:
        print("ERROR: Insufficient arguments")
        print(
            "Usage: blender -b --python blender_render.py -- <usd_file> <output_file> [quality] [camera_angle]")
        sys.exit(1)

    usd_file = argv[0]
    output_file = argv[1]
    quality = argv[2] if len(argv) > 2 else 'preview'
    camera_angle = argv[3] if len(argv) > 3 else 'perspective'

    print(f"=== Blender Render Script ===")
    print(f"USD File: {usd_file}")
    print(f"Output: {output_file}")
    print(f"Quality: {quality}")
    print(f"Camera Angle: {camera_angle}")
    print(f"Blender Version: {bpy.app.version_string}")

    # Create output directory if needed
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Rendering pipeline
    setup_scene()
    import_usd(usd_file)
    setup_camera_angle(angle=camera_angle, auto_frame=True)
    setup_lighting()

    # Determine resolution from quality
    resolution_map = {
        'preview': (256, 256),
        'verification': (512, 512),
        'final': (1920, 1080),
    }
    width, height = resolution_map.get(quality, (512, 512))

    configure_render_settings(quality, width, height)
    render_time = render(output_file)

    if render_time > 0:
        print(f"SUCCESS: Rendered in {render_time}ms")
        sys.exit(0)
    else:
        print("FAILED: Render did not complete")
        sys.exit(1)


if __name__ == "__main__":
    main()
