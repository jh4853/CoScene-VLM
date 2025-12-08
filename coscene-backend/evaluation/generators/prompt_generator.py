"""
Prompt Generator for creating natural language prompts from edit operations.
Generates multiple variations of prompts for the same edit operation.
"""
import random
from typing import List, Dict, Any, Tuple

from evaluation.generators.template_library import (
    get_position_descriptors,
    POSITION_DESCRIPTORS,
)


class PromptGenerator:
    """Generate natural language prompts for USD edit operations."""

    def __init__(self, seed: int = None):
        """
        Initialize prompt generator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)

        # Define prompt templates for each operation type
        self.templates = {
            'add_primitive': [
                "Add a {color} {primitive} at {position_desc}",
                "Create a {color} {primitive} {position_desc}",
                "Put a {color} {primitive} {position_desc}",
                "I want a {color} {primitive} {position_desc}",
                "Place a {color} {primitive} {position_desc}",
                "Make a {color} {primitive} {position_desc}",
            ],
            'change_color': [
                "Make the {object_desc} {new_color}",
                "Change the {object_desc}'s color to {new_color}",
                "Turn the {object_desc} {new_color}",
                "Set the {object_desc} color to {new_color}",
                "Color the {object_desc} {new_color}",
                "Change the color of the {object_desc} to {new_color}",
            ],
            'move_object': [
                "Move the {object_desc} to {position_desc}",
                "Shift the {object_desc} {position_desc}",
                "Relocate the {object_desc} {position_desc}",
                "Put the {object_desc} at {position_desc}",
                "Change the position of the {object_desc} to {position_desc}",
            ],
            'scale_object': [
                "Make the {object_desc} {scale_desc}",
                "Scale the {object_desc} to {scale_factor}x",
                "Change the {object_desc} size to {scale_desc}",
                "Resize the {object_desc} to {scale_desc}",
            ],
            'delete_object': [
                "Remove the {object_desc}",
                "Delete the {object_desc}",
                "Get rid of the {object_desc}",
                "Take away the {object_desc}",
            ],
        }

        # Primitive name variations
        self.primitive_variations = {
            'sphere': ['sphere', 'ball', 'spherical object'],
            'cube': ['cube', 'box', 'cubic object'],
            'cylinder': ['cylinder', 'cylindrical object', 'tube'],
            'cone': ['cone', 'conical object', 'pyramid'],
        }

        # Scale descriptors
        self.scale_descriptors = {
            0.5: ['smaller', 'half the size', 'half size'],
            1.0: ['normal size', 'regular size', 'original size'],
            1.5: ['larger', '1.5 times the size', '50% larger'],
            2.0: ['twice as large', 'double the size', 'much larger'],
        }

    def _get_position_description(self, position: Tuple[float, float, float]) -> str:
        """Get a natural language description of a position."""
        descriptors = get_position_descriptors(position)
        return random.choice(descriptors)

    def _get_primitive_variation(self, primitive_type: str) -> str:
        """Get a variation of primitive name."""
        variations = self.primitive_variations.get(primitive_type, [primitive_type])
        return random.choice(variations)

    def _get_scale_description(self, scale: float) -> str:
        """Get a natural language description of a scale."""
        descriptors = self.scale_descriptors.get(scale, [f'{scale}x size'])
        return random.choice(descriptors)

    def generate_add_primitive_prompt(self, parameters: Dict[str, Any]) -> str:
        """
        Generate prompt for add_primitive operation.

        Args:
            parameters: Dict with 'primitive_type', 'color_name', 'position'

        Returns:
            Natural language prompt string
        """
        primitive_type = parameters['primitive_type']
        color_name = parameters['color_name']
        position = parameters['position']

        # Choose random template
        template = random.choice(self.templates['add_primitive'])

        # Get variations
        primitive_var = self._get_primitive_variation(primitive_type)
        position_desc = self._get_position_description(position)

        # Fill template
        prompt = template.format(
            color=color_name,
            primitive=primitive_var,
            position_desc=position_desc,
        )

        return prompt

    def generate_change_color_prompt(self, parameters: Dict[str, Any]) -> str:
        """
        Generate prompt for change_color operation.

        Args:
            parameters: Dict with 'object_name', 'old_color_name', 'new_color_name'

        Returns:
            Natural language prompt string
        """
        old_color = parameters['old_color_name']
        new_color = parameters['new_color_name']

        # Extract primitive type from object name (e.g., "RedSphere_1" -> "sphere")
        object_name = parameters['object_name']
        for prim_type in self.primitive_variations.keys():
            if prim_type.lower() in object_name.lower():
                primitive_type = prim_type
                break
        else:
            primitive_type = 'object'

        # Choose random template
        template = random.choice(self.templates['change_color'])

        # Get variations
        primitive_var = self._get_primitive_variation(primitive_type)
        object_desc = f"{old_color} {primitive_var}"

        # Fill template
        prompt = template.format(
            object_desc=object_desc,
            new_color=new_color,
        )

        return prompt

    def generate_move_object_prompt(self, parameters: Dict[str, Any]) -> str:
        """Generate prompt for move_object operation."""
        object_color = parameters.get('object_color', '')
        object_type = parameters.get('object_type', 'object')
        new_position = parameters['new_position']

        # Build object description
        primitive_var = self._get_primitive_variation(object_type)
        if object_color:
            object_desc = f"{object_color} {primitive_var}"
        else:
            object_desc = primitive_var

        template = random.choice(self.templates['move_object'])
        position_desc = self._get_position_description(new_position)

        prompt = template.format(
            object_desc=object_desc,
            position_desc=position_desc,
        )

        return prompt

    def generate_scale_object_prompt(self, parameters: Dict[str, Any]) -> str:
        """Generate prompt for scale_object operation."""
        object_color = parameters.get('object_color', '')
        object_type = parameters.get('object_type', 'object')
        new_scale = parameters['new_scale']

        # Build object description
        primitive_var = self._get_primitive_variation(object_type)
        if object_color:
            object_desc = f"{object_color} {primitive_var}"
        else:
            object_desc = primitive_var

        template = random.choice(self.templates['scale_object'])
        scale_desc = self._get_scale_description(new_scale)

        prompt = template.format(
            object_desc=object_desc,
            scale_desc=scale_desc,
            scale_factor=new_scale,
        )

        return prompt

    def generate_delete_object_prompt(self, parameters: Dict[str, Any]) -> str:
        """Generate prompt for delete_object operation."""
        object_color = parameters.get('object_color', '')
        object_type = parameters.get('object_type', 'object')

        # Build object description
        primitive_var = self._get_primitive_variation(object_type)
        if object_color:
            object_desc = f"{object_color} {primitive_var}"
        else:
            object_desc = primitive_var

        template = random.choice(self.templates['delete_object'])

        prompt = template.format(
            object_desc=object_desc,
        )

        return prompt

    def generate_add_multiple_objects_prompt(self, parameters: Dict[str, Any]) -> str:
        """Generate prompt for add_multiple_objects operation."""
        num_objects = parameters['num_objects']
        objects = parameters['objects']

        # Build description of objects to add
        object_descriptions = []
        for obj in objects:
            color = obj['color']
            obj_type = obj['type']
            primitive_var = self._get_primitive_variation(obj_type)
            object_descriptions.append(f"{color} {primitive_var}")

        # Choose template style
        if num_objects == 2:
            template = f"Add a {{obj1}} and a {{obj2}}"
            prompt = template.format(obj1=object_descriptions[0], obj2=object_descriptions[1])
        elif num_objects == 3:
            template = f"Add a {{obj1}}, a {{obj2}}, and a {{obj3}}"
            prompt = template.format(
                obj1=object_descriptions[0],
                obj2=object_descriptions[1],
                obj3=object_descriptions[2]
            )
        else:
            prompt = f"Add {num_objects} objects to the scene"

        return prompt

    def generate_create_pattern_prompt(self, parameters: Dict[str, Any]) -> str:
        """Generate prompt for create_pattern operation."""
        pattern_type = parameters['pattern_type']
        primitive_type = parameters['primitive_type']
        num_objects = parameters.get('num_objects', 6)

        primitive_var = self._get_primitive_variation(primitive_type)

        # Pattern-specific templates
        if pattern_type == 'grid':
            templates = [
                f"Create a grid of {primitive_var}s",
                f"Make a grid pattern with {primitive_var}s",
                f"Arrange {primitive_var}s in a grid",
                f"Put {primitive_var}s in a grid formation",
            ]
        elif pattern_type == 'circle':
            templates = [
                f"Create a circle of {primitive_var}s",
                f"Arrange {num_objects} {primitive_var}s in a circle",
                f"Make a circular pattern with {primitive_var}s",
                f"Put {primitive_var}s in a circle",
            ]
        elif pattern_type == 'line':
            templates = [
                f"Create a line of {primitive_var}s",
                f"Arrange {primitive_var}s in a line",
                f"Make a row of {primitive_var}s",
                f"Put {num_objects} {primitive_var}s in a line",
            ]
        else:
            templates = [f"Create a {pattern_type} pattern of {primitive_var}s"]

        return random.choice(templates)

    def generate_compositional_edit_prompt(self, parameters: Dict[str, Any]) -> str:
        """Generate prompt for compositional_edit operation."""
        composition_type = parameters['composition_type']
        steps = parameters.get('steps', [])

        if composition_type == 'arrangement':
            templates = [
                "Arrange the objects in a line",
                "Put all the objects in a row",
                "Line up the objects horizontally",
                "Organize the objects in a horizontal line",
            ]
        elif composition_type == 'creation':
            templates = [
                "Create a colorful scene with multiple objects",
                "Add several objects to make an interesting scene",
                "Make a diverse scene with different shapes and colors",
                "Fill the scene with colorful objects",
            ]
        elif composition_type == 'transformation':
            templates = [
                "Make all the objects larger",
                "Scale up everything in the scene",
                "Increase the size of all objects",
                "Make everything bigger",
            ]
        else:
            templates = ["Modify the scene"]

        return random.choice(templates)

    def generate_prompt(self, operation_type: str, parameters: Dict[str, Any]) -> str:
        """
        Generate a prompt for any operation type.

        Args:
            operation_type: Type of operation
            parameters: Operation parameters

        Returns:
            Natural language prompt
        """
        if operation_type == 'add_primitive':
            return self.generate_add_primitive_prompt(parameters)
        elif operation_type == 'change_color':
            return self.generate_change_color_prompt(parameters)
        elif operation_type == 'move_object':
            return self.generate_move_object_prompt(parameters)
        elif operation_type == 'scale_object':
            return self.generate_scale_object_prompt(parameters)
        elif operation_type == 'delete_object':
            return self.generate_delete_object_prompt(parameters)
        elif operation_type == 'add_multiple_objects':
            return self.generate_add_multiple_objects_prompt(parameters)
        elif operation_type == 'create_pattern':
            return self.generate_create_pattern_prompt(parameters)
        elif operation_type == 'compositional_edit':
            return self.generate_compositional_edit_prompt(parameters)
        else:
            # Fallback
            return f"Perform {operation_type} operation"

    def generate_prompt_variations(
        self,
        operation_type: str,
        parameters: Dict[str, Any],
        num_variations: int = 3
    ) -> List[str]:
        """
        Generate multiple prompt variations for the same operation.

        Args:
            operation_type: Type of operation
            parameters: Operation parameters
            num_variations: Number of variations to generate

        Returns:
            List of prompt strings
        """
        variations = []
        for _ in range(num_variations):
            prompt = self.generate_prompt(operation_type, parameters)
            if prompt not in variations:  # Avoid duplicates
                variations.append(prompt)

        # Ensure we have enough variations
        while len(variations) < num_variations:
            prompt = self.generate_prompt(operation_type, parameters)
            if prompt not in variations:
                variations.append(prompt)

        return variations[:num_variations]


# For testing
if __name__ == "__main__":
    print("Testing Prompt Generator...")
    generator = PromptGenerator(seed=42)

    # Test add_primitive prompts
    print("\n=== Add Primitive Prompts ===")
    params = {
        'primitive_type': 'sphere',
        'color_name': 'red',
        'position': (0, 0, 0),
        'scale': 1.0,
    }
    variations = generator.generate_prompt_variations('add_primitive', params, num_variations=5)
    for i, prompt in enumerate(variations, 1):
        print(f"{i}. {prompt}")

    # Test change_color prompts
    print("\n=== Change Color Prompts ===")
    params = {
        'object_name': 'RedSphere_1',
        'old_color_name': 'red',
        'new_color_name': 'blue',
    }
    variations = generator.generate_prompt_variations('change_color', params, num_variations=5)
    for i, prompt in enumerate(variations, 1):
        print(f"{i}. {prompt}")

    # Test move_object prompts
    print("\n=== Move Object Prompts ===")
    params = {
        'object_name': 'RedSphere_1',
        'new_position': (2, 0, 0),
    }
    variations = generator.generate_prompt_variations('move_object', params, num_variations=5)
    for i, prompt in enumerate(variations, 1):
        print(f"{i}. {prompt}")
