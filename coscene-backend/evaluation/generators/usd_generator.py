"""
USD Generator for creating procedural test cases.
Generates before/after USD pairs with known edit operations.
"""
import random
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
import json

from evaluation.generators.template_library import (
    PRIMITIVES,
    COLORS,
    COLOR_NAMES,
    MATERIAL_PRESETS,
    OPERATIONS,
    generate_usd_header,
    generate_usd_footer,
    generate_sphere_usd,
    generate_cube_usd,
    generate_cylinder_usd,
    generate_cone_usd,
    get_color_rgb,
    check_collision,
    get_random_safe_position,
    generate_grid_positions,
    generate_circle_positions,
    generate_line_positions,
)


@dataclass
class USDObject:
    """Represents a 3D object in a USD scene."""
    name: str
    primitive_type: str  # 'sphere', 'cube', 'cylinder', 'cone'
    color: Tuple[float, float, float]
    color_name: str
    position: Tuple[float, float, float]
    scale: float
    radius: Optional[float] = None  # For sphere, cylinder, cone
    size: Optional[float] = None  # For cube
    height: Optional[float] = None  # For cylinder, cone
    metallic: float = 0.0
    roughness: float = 0.5


@dataclass
class EditOperation:
    """Represents an edit operation on a USD scene."""
    operation_type: str
    parameters: Dict[str, Any]
    description: str


@dataclass
class USDScenePair:
    """Represents a before/after USD scene pair with edit operation."""
    test_case_id: str
    complexity: str
    initial_scene: List[USDObject]
    target_scene: List[USDObject]
    edit_operation: EditOperation
    initial_usd: str
    target_usd: str
    expected_metrics: Dict[str, Any]


class USDGenerator:
    """Generate procedural USD scenes and edit operations."""

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize USD generator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        self.object_counter = 0

    def _get_unique_name(self, primitive_type: str, color_name: str) -> str:
        """Generate a unique object name."""
        self.object_counter += 1
        return f"{color_name.capitalize()}{primitive_type.capitalize()}_{self.object_counter}"

    def _scene_to_usd(self, objects: List[USDObject]) -> str:
        """Convert a list of objects to USD format."""
        usd_parts = [generate_usd_header()]

        for obj in objects:
            if obj.primitive_type == 'sphere':
                usd_parts.append(generate_sphere_usd(
                    name=obj.name,
                    color=obj.color,
                    position=obj.position,
                    scale=obj.scale,
                    radius=obj.radius or 1.0,
                    metallic=obj.metallic,
                    roughness=obj.roughness,
                ))
            elif obj.primitive_type == 'cube':
                usd_parts.append(generate_cube_usd(
                    name=obj.name,
                    color=obj.color,
                    position=obj.position,
                    scale=obj.scale,
                    size=obj.size or 2.0,
                    metallic=obj.metallic,
                    roughness=obj.roughness,
                ))
            elif obj.primitive_type == 'cylinder':
                usd_parts.append(generate_cylinder_usd(
                    name=obj.name,
                    color=obj.color,
                    position=obj.position,
                    scale=obj.scale,
                    height=obj.height or 2.0,
                    radius=obj.radius or 1.0,
                    metallic=obj.metallic,
                    roughness=obj.roughness,
                ))
            elif obj.primitive_type == 'cone':
                usd_parts.append(generate_cone_usd(
                    name=obj.name,
                    color=obj.color,
                    position=obj.position,
                    scale=obj.scale,
                    height=obj.height or 2.0,
                    radius=obj.radius or 1.0,
                    metallic=obj.metallic,
                    roughness=obj.roughness,
                ))

        usd_parts.append(generate_usd_footer())
        return "".join(usd_parts)

    def generate_empty_scene(self) -> List[USDObject]:
        """Generate an empty scene."""
        return []

    def generate_simple_scene(self, num_objects: int = 1) -> List[USDObject]:
        """
        Generate a simple scene with 1-2 objects.

        Args:
            num_objects: Number of objects (1-2)

        Returns:
            List of USDObject instances
        """
        objects = []
        used_positions = set()

        for _ in range(min(num_objects, 2)):
            # Random primitive type
            primitive_type = random.choice(['sphere', 'cube', 'cylinder'])
            template = PRIMITIVES[primitive_type]

            # Random color
            color_name = random.choice(template.supported_colors)
            color = get_color_rgb(color_name)

            # Random position (avoid collisions)
            available_positions = [
                p for p in template.supported_positions if p not in used_positions
            ]
            position = random.choice(available_positions)
            used_positions.add(position)

            # Random scale
            scale = random.choice(template.supported_scales)

            # Create object
            obj = USDObject(
                name=self._get_unique_name(primitive_type, color_name),
                primitive_type=primitive_type,
                color=color,
                color_name=color_name,
                position=position,
                scale=scale,
                radius=template.default_params.get('radius'),
                size=template.default_params.get('size'),
                height=template.default_params.get('height'),
            )
            objects.append(obj)

        return objects

    def generate_add_primitive_edit(self) -> USDScenePair:
        """
        Generate a simple 'add primitive' edit operation.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: empty or 1 object
        initial_objects = self.generate_simple_scene(num_objects=random.choice([0, 1]))

        # Operation: add a new primitive
        primitive_type = random.choice(['sphere', 'cube', 'cylinder'])
        template = PRIMITIVES[primitive_type]

        color_name = random.choice(template.supported_colors)
        color = get_color_rgb(color_name)

        # Choose position (avoid existing objects)
        used_positions = {obj.position for obj in initial_objects}
        available_positions = [p for p in template.supported_positions if p not in used_positions]
        position = random.choice(available_positions) if available_positions else (0, 0, 0)

        scale = random.choice(template.supported_scales)

        # Create new object
        new_object = USDObject(
            name=self._get_unique_name(primitive_type, color_name),
            primitive_type=primitive_type,
            color=color,
            color_name=color_name,
            position=position,
            scale=scale,
            radius=template.default_params.get('radius'),
            size=template.default_params.get('size'),
            height=template.default_params.get('height'),
        )

        # Target scene: initial + new object
        target_objects = initial_objects + [new_object]

        # Create edit operation
        operation = EditOperation(
            operation_type='add_primitive',
            parameters={
                'primitive_type': primitive_type,
                'color_name': color_name,
                'color': color,
                'position': position,
                'scale': scale,
            },
            description=f"Add a {color_name} {primitive_type}",
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'new_object_type': primitive_type,
            'new_object_color': color,
            'new_object_position': position,
        }

        return USDScenePair(
            test_case_id=f"simple_add_{primitive_type}_{self.object_counter}",
            complexity='simple',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_change_color_edit(self) -> USDScenePair:
        """
        Generate a 'change color' edit operation.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: 1 object
        initial_objects = self.generate_simple_scene(num_objects=1)

        if not initial_objects:
            # Fallback to add primitive if scene generation failed
            return self.generate_add_primitive_edit()

        # Target object
        target_obj = initial_objects[0]

        # New color (different from current)
        available_colors = [c for c in COLOR_NAMES if c != target_obj.color_name]
        new_color_name = random.choice(available_colors)
        new_color = get_color_rgb(new_color_name)

        # Create modified object
        modified_obj = USDObject(
            name=target_obj.name,
            primitive_type=target_obj.primitive_type,
            color=new_color,
            color_name=new_color_name,
            position=target_obj.position,
            scale=target_obj.scale,
            radius=target_obj.radius,
            size=target_obj.size,
            height=target_obj.height,
            metallic=target_obj.metallic,
            roughness=target_obj.roughness,
        )

        target_objects = [modified_obj]

        # Create edit operation
        operation = EditOperation(
            operation_type='change_color',
            parameters={
                'object_name': target_obj.name,
                'old_color_name': target_obj.color_name,
                'new_color_name': new_color_name,
                'new_color': new_color,
            },
            description=f"Change the {target_obj.color_name} {target_obj.primitive_type} to {new_color_name}",
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'object_name': target_obj.name,
            'new_color': new_color,
        }

        return USDScenePair(
            test_case_id=f"simple_change_color_{self.object_counter}",
            complexity='simple',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_simple_edit(self) -> USDScenePair:
        """
        Generate a random simple edit operation.

        Returns:
            USDScenePair
        """
        operation_type = random.choice(['add_primitive', 'change_color'])

        if operation_type == 'add_primitive':
            return self.generate_add_primitive_edit()
        elif operation_type == 'change_color':
            return self.generate_change_color_edit()

        return self.generate_add_primitive_edit()  # Fallback

    # ============ Medium Complexity Methods ============

    def generate_medium_scene(self, num_objects: int = 3) -> List[USDObject]:
        """
        Generate a medium complexity scene with 2-4 objects.

        Args:
            num_objects: Number of objects (2-4)

        Returns:
            List of USDObject instances
        """
        objects = []
        used_positions = set()
        num_objects = max(2, min(num_objects, 4))  # Clamp to 2-4

        for _ in range(num_objects):
            # Random primitive type
            primitive_type = random.choice(['sphere', 'cube', 'cylinder', 'cone'])
            template = PRIMITIVES[primitive_type]

            # Random color
            color_name = random.choice(template.supported_colors)
            color = get_color_rgb(color_name)

            # Random position (avoid collisions)
            available_positions = [
                p for p in template.supported_positions if p not in used_positions
            ]
            if not available_positions:
                break  # No more positions available
            position = random.choice(available_positions)
            used_positions.add(position)

            # Random scale
            scale = random.choice(template.supported_scales)

            # Create object
            obj = USDObject(
                name=self._get_unique_name(primitive_type, color_name),
                primitive_type=primitive_type,
                color=color,
                color_name=color_name,
                position=position,
                scale=scale,
                radius=template.default_params.get('radius'),
                size=template.default_params.get('size'),
                height=template.default_params.get('height'),
            )
            objects.append(obj)

        return objects

    def generate_move_object_edit(self) -> USDScenePair:
        """
        Generate a 'move object' edit operation.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: 2-3 objects
        initial_objects = self.generate_medium_scene(num_objects=random.choice([2, 3]))

        if len(initial_objects) < 1:
            # Fallback to add primitive if scene generation failed
            return self.generate_add_primitive_edit()

        # Select object to move
        target_obj = random.choice(initial_objects)
        target_idx = initial_objects.index(target_obj)

        # Choose new position (avoid existing objects)
        template = PRIMITIVES[target_obj.primitive_type]
        used_positions = {obj.position for obj in initial_objects}
        available_positions = [p for p in template.supported_positions if p not in used_positions]

        if not available_positions:
            # If no positions available, use a different position anyway
            available_positions = [p for p in template.supported_positions if p != target_obj.position]

        new_position = random.choice(available_positions) if available_positions else (0, 0, 0)

        # Create modified object
        moved_obj = USDObject(
            name=target_obj.name,
            primitive_type=target_obj.primitive_type,
            color=target_obj.color,
            color_name=target_obj.color_name,
            position=new_position,
            scale=target_obj.scale,
            radius=target_obj.radius,
            size=target_obj.size,
            height=target_obj.height,
            metallic=target_obj.metallic,
            roughness=target_obj.roughness,
        )

        # Create target scene
        target_objects = initial_objects.copy()
        target_objects[target_idx] = moved_obj

        # Create edit operation
        operation = EditOperation(
            operation_type='move_object',
            parameters={
                'object_name': target_obj.name,
                'object_color': target_obj.color_name,
                'object_type': target_obj.primitive_type,
                'old_position': target_obj.position,
                'new_position': new_position,
            },
            description=f"Move the {target_obj.color_name} {target_obj.primitive_type} to a new position",
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'moved_object': target_obj.name,
            'new_position': new_position,
            'position_tolerance': 0.1,
        }

        return USDScenePair(
            test_case_id=f"medium_move_object_{self.object_counter}",
            complexity='medium',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_scale_object_edit(self) -> USDScenePair:
        """
        Generate a 'scale object' edit operation.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: 2-3 objects
        initial_objects = self.generate_medium_scene(num_objects=random.choice([2, 3]))

        if len(initial_objects) < 1:
            return self.generate_add_primitive_edit()

        # Select object to scale
        target_obj = random.choice(initial_objects)
        target_idx = initial_objects.index(target_obj)

        # Choose new scale (different from current)
        template = PRIMITIVES[target_obj.primitive_type]
        available_scales = [s for s in template.supported_scales if s != target_obj.scale]
        new_scale = random.choice(available_scales) if available_scales else 1.5

        # Create scaled object
        scaled_obj = USDObject(
            name=target_obj.name,
            primitive_type=target_obj.primitive_type,
            color=target_obj.color,
            color_name=target_obj.color_name,
            position=target_obj.position,
            scale=new_scale,
            radius=target_obj.radius,
            size=target_obj.size,
            height=target_obj.height,
            metallic=target_obj.metallic,
            roughness=target_obj.roughness,
        )

        # Create target scene
        target_objects = initial_objects.copy()
        target_objects[target_idx] = scaled_obj

        # Create edit operation
        operation = EditOperation(
            operation_type='scale_object',
            parameters={
                'object_name': target_obj.name,
                'object_color': target_obj.color_name,
                'object_type': target_obj.primitive_type,
                'old_scale': target_obj.scale,
                'new_scale': new_scale,
            },
            description=f"Scale the {target_obj.color_name} {target_obj.primitive_type}",
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'scaled_object': target_obj.name,
            'new_scale': new_scale,
        }

        return USDScenePair(
            test_case_id=f"medium_scale_object_{self.object_counter}",
            complexity='medium',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_delete_object_edit(self) -> USDScenePair:
        """
        Generate a 'delete object' edit operation.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: 2-3 objects (ensure at least 2 so we can delete one)
        initial_objects = self.generate_medium_scene(num_objects=random.choice([2, 3]))

        if len(initial_objects) < 2:
            # Need at least 2 objects to delete one
            return self.generate_add_primitive_edit()

        # Select object to delete
        target_obj = random.choice(initial_objects)

        # Create target scene (without the deleted object)
        target_objects = [obj for obj in initial_objects if obj.name != target_obj.name]

        # Create edit operation
        operation = EditOperation(
            operation_type='delete_object',
            parameters={
                'object_name': target_obj.name,
                'object_color': target_obj.color_name,
                'object_type': target_obj.primitive_type,
                'position': target_obj.position,
            },
            description=f"Delete the {target_obj.color_name} {target_obj.primitive_type}",
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'deleted_object': target_obj.name,
        }

        return USDScenePair(
            test_case_id=f"medium_delete_object_{self.object_counter}",
            complexity='medium',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_add_multiple_objects_edit(self) -> USDScenePair:
        """
        Generate an 'add multiple objects' edit operation.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: 0-2 objects
        initial_objects = self.generate_simple_scene(num_objects=random.choice([0, 1, 2]))

        # Add 2-3 new objects
        num_new_objects = random.choice([2, 3])
        new_objects = []

        used_positions = {obj.position for obj in initial_objects}

        for _ in range(num_new_objects):
            # Random primitive type
            primitive_type = random.choice(['sphere', 'cube', 'cylinder'])
            template = PRIMITIVES[primitive_type]

            # Random color
            color_name = random.choice(template.supported_colors)
            color = get_color_rgb(color_name)

            # Random position (avoid collisions)
            available_positions = [p for p in template.supported_positions if p not in used_positions]
            if not available_positions:
                break  # No more positions available
            position = random.choice(available_positions)
            used_positions.add(position)

            # Random scale
            scale = random.choice(template.supported_scales)

            # Create new object
            obj = USDObject(
                name=self._get_unique_name(primitive_type, color_name),
                primitive_type=primitive_type,
                color=color,
                color_name=color_name,
                position=position,
                scale=scale,
                radius=template.default_params.get('radius'),
                size=template.default_params.get('size'),
                height=template.default_params.get('height'),
            )
            new_objects.append(obj)

        if not new_objects:
            return self.generate_add_primitive_edit()

        # Target scene: initial + new objects
        target_objects = initial_objects + new_objects

        # Create edit operation
        operation = EditOperation(
            operation_type='add_multiple_objects',
            parameters={
                'num_objects': len(new_objects),
                'objects': [
                    {
                        'type': obj.primitive_type,
                        'color': obj.color_name,
                        'position': obj.position,
                        'scale': obj.scale,
                    }
                    for obj in new_objects
                ],
            },
            description=f"Add {len(new_objects)} objects to the scene",
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'added_objects': [obj.name for obj in new_objects],
            'num_added': len(new_objects),
        }

        return USDScenePair(
            test_case_id=f"medium_add_multiple_{self.object_counter}",
            complexity='medium',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_medium_edit(self) -> USDScenePair:
        """
        Generate a random medium complexity edit operation.

        Returns:
            USDScenePair
        """
        operation_type = random.choice([
            'move_object',
            'scale_object',
            'delete_object',
            'add_multiple_objects',
        ])

        if operation_type == 'move_object':
            return self.generate_move_object_edit()
        elif operation_type == 'scale_object':
            return self.generate_scale_object_edit()
        elif operation_type == 'delete_object':
            return self.generate_delete_object_edit()
        elif operation_type == 'add_multiple_objects':
            return self.generate_add_multiple_objects_edit()

        return self.generate_move_object_edit()  # Fallback

    # ============ Complex Complexity Methods ============

    def generate_complex_scene(self, num_objects: int = 6) -> List[USDObject]:
        """
        Generate a complex scene with 5-8 objects.

        Args:
            num_objects: Number of objects (5-8)

        Returns:
            List of USDObject instances
        """
        objects = []
        used_positions = set()
        num_objects = max(5, min(num_objects, 8))  # Clamp to 5-8

        for _ in range(num_objects):
            # Random primitive type
            primitive_type = random.choice(['sphere', 'cube', 'cylinder', 'cone'])
            template = PRIMITIVES[primitive_type]

            # Random color
            color_name = random.choice(template.supported_colors)
            color = get_color_rgb(color_name)

            # Random position (avoid collisions)
            available_positions = [
                p for p in template.supported_positions if p not in used_positions
            ]
            if not available_positions:
                break  # No more positions available
            position = random.choice(available_positions)
            used_positions.add(position)

            # Random scale
            scale = random.choice(template.supported_scales)

            # Create object
            obj = USDObject(
                name=self._get_unique_name(primitive_type, color_name),
                primitive_type=primitive_type,
                color=color,
                color_name=color_name,
                position=position,
                scale=scale,
                radius=template.default_params.get('radius'),
                size=template.default_params.get('size'),
                height=template.default_params.get('height'),
            )
            objects.append(obj)

        return objects

    def generate_create_pattern_edit(self) -> USDScenePair:
        """
        Generate a 'create pattern' edit operation.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: empty or minimal
        initial_objects = self.generate_simple_scene(num_objects=random.choice([0, 1]))

        # Choose pattern type
        pattern_type = random.choice(['grid', 'circle', 'line'])

        # Choose primitive and color
        primitive_type = random.choice(['sphere', 'cube', 'cylinder'])
        template = PRIMITIVES[primitive_type]

        # Generate pattern positions
        if pattern_type == 'grid':
            rows, cols = random.choice([(2, 3), (3, 3), (2, 2)])
            positions = generate_grid_positions(rows, cols, spacing=2.0)
            pattern_desc = f"{rows}x{cols} grid"
        elif pattern_type == 'circle':
            num_objects = random.choice([6, 7, 8])
            positions = generate_circle_positions(num_objects, radius=3.0)
            pattern_desc = f"circle of {num_objects} objects"
        else:  # line
            num_objects = random.choice([4, 5, 6])
            direction = random.choice(['horizontal', 'vertical'])
            positions = generate_line_positions(num_objects, spacing=2.0, direction=direction)
            pattern_desc = f"{direction} line of {num_objects} objects"

        # Create objects for pattern
        new_objects = []
        color_scheme = random.choice(['single', 'varied'])

        for i, position in enumerate(positions):
            if color_scheme == 'single':
                color_name = random.choice(template.supported_colors)
            else:
                color_name = random.choice(template.supported_colors)

            color = get_color_rgb(color_name)
            scale = random.choice([1.0, 1.0, 1.0, 1.5])  # Mostly uniform scale

            obj = USDObject(
                name=self._get_unique_name(primitive_type, color_name),
                primitive_type=primitive_type,
                color=color,
                color_name=color_name,
                position=position,
                scale=scale,
                radius=template.default_params.get('radius'),
                size=template.default_params.get('size'),
                height=template.default_params.get('height'),
            )
            new_objects.append(obj)

        # Target scene
        target_objects = initial_objects + new_objects

        # Create edit operation
        operation = EditOperation(
            operation_type='create_pattern',
            parameters={
                'pattern_type': pattern_type,
                'primitive_type': primitive_type,
                'num_objects': len(new_objects),
                'color_scheme': color_scheme,
            },
            description=f"Create a {pattern_desc} of {primitive_type}s",
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'pattern_type': pattern_type,
            'pattern_objects': len(new_objects),
        }

        return USDScenePair(
            test_case_id=f"complex_create_pattern_{pattern_type}_{self.object_counter}",
            complexity='complex',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_compositional_edit(self) -> USDScenePair:
        """
        Generate a compositional edit with multiple steps.

        Returns:
            USDScenePair with before/after scenes
        """
        # Initial scene: 2-4 objects
        initial_objects = self.generate_medium_scene(num_objects=random.choice([2, 3, 4]))

        # Choose composition type
        composition_type = random.choice(['arrangement', 'creation', 'transformation'])

        steps = []
        target_objects = initial_objects.copy()

        if composition_type == 'arrangement':
            # Arrange existing objects in a line
            num_to_arrange = min(3, len(initial_objects))
            objects_to_arrange = random.sample(initial_objects, num_to_arrange)
            line_positions = generate_line_positions(num_to_arrange, spacing=2.5, direction='horizontal')

            for obj, new_pos in zip(objects_to_arrange, line_positions):
                # Find and update object in target_objects
                for i, target_obj in enumerate(target_objects):
                    if target_obj.name == obj.name:
                        moved_obj = USDObject(
                            name=obj.name,
                            primitive_type=obj.primitive_type,
                            color=obj.color,
                            color_name=obj.color_name,
                            position=new_pos,
                            scale=obj.scale,
                            radius=obj.radius,
                            size=obj.size,
                            height=obj.height,
                            metallic=obj.metallic,
                            roughness=obj.roughness,
                        )
                        target_objects[i] = moved_obj
                        steps.append({
                            'op': 'move_object',
                            'target': obj.name,
                            'new_pos': new_pos,
                        })
                        break

            description = f"Arrange {num_to_arrange} objects in a line"

        elif composition_type == 'creation':
            # Add multiple diverse objects
            num_new = random.choice([3, 4])
            used_positions = {obj.position for obj in target_objects}

            for _ in range(num_new):
                primitive_type = random.choice(['sphere', 'cube', 'cylinder'])
                template = PRIMITIVES[primitive_type]
                color_name = random.choice(template.supported_colors)
                color = get_color_rgb(color_name)

                available_positions = [p for p in template.supported_positions if p not in used_positions]
                if not available_positions:
                    break
                position = random.choice(available_positions)
                used_positions.add(position)

                obj = USDObject(
                    name=self._get_unique_name(primitive_type, color_name),
                    primitive_type=primitive_type,
                    color=color,
                    color_name=color_name,
                    position=position,
                    scale=1.0,
                    radius=template.default_params.get('radius'),
                    size=template.default_params.get('size'),
                    height=template.default_params.get('height'),
                )
                target_objects.append(obj)
                steps.append({
                    'op': 'add_primitive',
                    'type': primitive_type,
                    'color': color_name,
                    'pos': position,
                })

            description = f"Create a colorful scene with {num_new} new objects"

        else:  # transformation
            # Scale all objects
            scale_factor = random.choice([1.5, 2.0])
            for i, obj in enumerate(target_objects):
                scaled_obj = USDObject(
                    name=obj.name,
                    primitive_type=obj.primitive_type,
                    color=obj.color,
                    color_name=obj.color_name,
                    position=obj.position,
                    scale=scale_factor,
                    radius=obj.radius,
                    size=obj.size,
                    height=obj.height,
                    metallic=obj.metallic,
                    roughness=obj.roughness,
                )
                target_objects[i] = scaled_obj
                steps.append({
                    'op': 'scale_object',
                    'target': obj.name,
                    'new_scale': scale_factor,
                })

            description = f"Make all objects {scale_factor}x larger"

        # Create edit operation
        operation = EditOperation(
            operation_type='compositional_edit',
            parameters={
                'composition_type': composition_type,
                'steps': steps,
            },
            description=description,
        )

        # Generate USD
        initial_usd = self._scene_to_usd(initial_objects)
        target_usd = self._scene_to_usd(target_objects)

        # Expected metrics
        expected_metrics = {
            'object_count': len(target_objects),
            'composition_type': composition_type,
            'num_steps': len(steps),
        }

        return USDScenePair(
            test_case_id=f"complex_compositional_{composition_type}_{self.object_counter}",
            complexity='complex',
            initial_scene=initial_objects,
            target_scene=target_objects,
            edit_operation=operation,
            initial_usd=initial_usd,
            target_usd=target_usd,
            expected_metrics=expected_metrics,
        )

    def generate_complex_edit(self) -> USDScenePair:
        """
        Generate a random complex edit operation.

        Returns:
            USDScenePair
        """
        operation_type = random.choice([
            'create_pattern',
            'compositional_edit',
        ])

        if operation_type == 'create_pattern':
            return self.generate_create_pattern_edit()
        elif operation_type == 'compositional_edit':
            return self.generate_compositional_edit()

        return self.generate_create_pattern_edit()  # Fallback

    def generate_dataset(self, num_cases: int, complexity: str = 'simple') -> List[Dict[str, Any]]:
        """
        Generate a dataset of test cases.

        Args:
            num_cases: Number of test cases to generate
            complexity: 'simple', 'medium', or 'complex'

        Returns:
            List of test case dictionaries
        """
        dataset = []

        for i in range(num_cases):
            if complexity == 'simple':
                scene_pair = self.generate_simple_edit()
            elif complexity == 'medium':
                scene_pair = self.generate_medium_edit()
            elif complexity == 'complex':
                scene_pair = self.generate_complex_edit()
            else:
                scene_pair = self.generate_simple_edit()

            # Convert to dict for JSON serialization
            test_case = {
                'id': scene_pair.test_case_id,
                'complexity': scene_pair.complexity,
                'initial_usd': scene_pair.initial_usd,
                'target_usd': scene_pair.target_usd,
                'edit_operation': {
                    'type': scene_pair.edit_operation.operation_type,
                    'parameters': scene_pair.edit_operation.parameters,
                    'description': scene_pair.edit_operation.description,
                },
                'expected_metrics': scene_pair.expected_metrics,
            }

            dataset.append(test_case)

        return dataset


# For testing
if __name__ == "__main__":
    print("Testing USD Generator...")
    generator = USDGenerator(seed=42)

    # Test add primitive
    print("\n=== Test: Add Primitive ===")
    pair = generator.generate_add_primitive_edit()
    print(f"Test Case ID: {pair.test_case_id}")
    print(f"Operation: {pair.edit_operation.description}")
    print(f"Initial Scene ({len(pair.initial_scene)} objects):")
    print(pair.initial_usd[:200], "...")
    print(f"\nTarget Scene ({len(pair.target_scene)} objects):")
    print(pair.target_usd[:200], "...")

    # Test change color
    print("\n=== Test: Change Color ===")
    pair = generator.generate_change_color_edit()
    print(f"Test Case ID: {pair.test_case_id}")
    print(f"Operation: {pair.edit_operation.description}")

    # Test dataset generation
    print("\n=== Test: Dataset Generation ===")
    dataset = generator.generate_dataset(num_cases=5, complexity='simple')
    print(f"Generated {len(dataset)} test cases")
    for tc in dataset:
        print(f"  - {tc['id']}: {tc['edit_operation']['description']}")
