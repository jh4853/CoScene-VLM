"""
Semantic metrics for checking intent preservation and quality.
Verifies that the agent did what was asked and didn't hallucinate.
"""
from typing import Dict, Any, List
import logging

from evaluation.metrics.structural_metrics import USDParser, USDObject

logger = logging.getLogger(__name__)


class SemanticMetrics:
    """Compute semantic correctness metrics."""

    def __init__(self):
        """Initialize semantic metrics calculator."""
        self.parser = USDParser()

    def check_intent_preservation(
        self,
        operation_type: str,
        operation_params: Dict[str, Any],
        ground_truth_usd: str,
        generated_usd: str
    ) -> Dict[str, Any]:
        """
        Check if the intended operation was performed correctly.

        Args:
            operation_type: Type of operation (add_primitive, change_color, etc.)
            operation_params: Operation parameters
            ground_truth_usd: Expected result
            generated_usd: Generated result

        Returns:
            Dict with intent preservation metrics
        """
        gt_objects = self.parser.parse_usd(ground_truth_usd)
        gen_objects = self.parser.parse_usd(generated_usd)

        if operation_type == 'add_primitive':
            return self._check_add_primitive_intent(operation_params, gt_objects, gen_objects)
        elif operation_type == 'change_color':
            return self._check_change_color_intent(operation_params, gt_objects, gen_objects)
        elif operation_type == 'move_object':
            return self._check_move_object_intent(operation_params, gt_objects, gen_objects)
        else:
            logger.warning(f"Unknown operation type: {operation_type}")
            return {
                'intent_preserved': False,
                'reason': f'Unknown operation type: {operation_type}'
            }

    def _check_add_primitive_intent(
        self,
        params: Dict[str, Any],
        gt_objects: List[USDObject],
        gen_objects: List[USDObject]
    ) -> Dict[str, Any]:
        """Check if add_primitive was done correctly."""
        expected_type = params.get('primitive_type')
        expected_color = tuple(params.get('color', []))

        # Check if a new object of the right type was added
        gen_types = [obj.prim_type.lower() for obj in gen_objects]
        gt_types = [obj.prim_type.lower() for obj in gt_objects]

        new_objects = [obj for obj in gen_objects if obj.prim_type.lower() == expected_type.lower()]

        if not new_objects:
            return {
                'intent_preserved': False,
                'reason': f'No {expected_type} object found in generated scene',
                'expected_type': expected_type,
                'found_types': gen_types,
            }

        # Check color of new object (if specified)
        if expected_color:
            color_match = any(
                obj.color and self._colors_match(obj.color, expected_color)
                for obj in new_objects
            )
            if not color_match:
                return {
                    'intent_preserved': False,
                    'reason': f'Object found but color mismatch',
                    'expected_color': expected_color,
                    'found_colors': [obj.color for obj in new_objects],
                }

        return {
            'intent_preserved': True,
            'reason': 'Object added with correct type and color',
            'matched_object': new_objects[0].name if new_objects else None,
        }

    def _check_change_color_intent(
        self,
        params: Dict[str, Any],
        gt_objects: List[USDObject],
        gen_objects: List[USDObject]
    ) -> Dict[str, Any]:
        """Check if change_color was done correctly."""
        new_color = tuple(params.get('new_color', []))
        object_name = params.get('object_name')

        # Find the object in generated scene
        target_obj = None
        for obj in gen_objects:
            if obj.name == object_name or object_name in obj.name:
                target_obj = obj
                break

        if not target_obj:
            return {
                'intent_preserved': False,
                'reason': f'Target object "{object_name}" not found in generated scene',
            }

        # Check color
        if target_obj.color and new_color:
            if self._colors_match(target_obj.color, new_color):
                return {
                    'intent_preserved': True,
                    'reason': 'Color changed correctly',
                    'matched_object': target_obj.name,
                }
            else:
                return {
                    'intent_preserved': False,
                    'reason': 'Color mismatch',
                    'expected_color': new_color,
                    'found_color': target_obj.color,
                }

        return {
            'intent_preserved': False,
            'reason': 'Could not verify color change',
        }

    def _check_move_object_intent(
        self,
        params: Dict[str, Any],
        gt_objects: List[USDObject],
        gen_objects: List[USDObject]
    ) -> Dict[str, Any]:
        """Check if move_object was done correctly."""
        new_position = tuple(params.get('new_position', []))
        object_name = params.get('object_name')

        # Find the object
        target_obj = None
        for obj in gen_objects:
            if obj.name == object_name or object_name in obj.name:
                target_obj = obj
                break

        if not target_obj:
            return {
                'intent_preserved': False,
                'reason': f'Target object "{object_name}" not found',
            }

        # Check position
        if target_obj.position and new_position:
            distance = sum((a - b) ** 2 for a, b in zip(target_obj.position, new_position)) ** 0.5
            if distance < 0.1:  # Within threshold
                return {
                    'intent_preserved': True,
                    'reason': 'Object moved to correct position',
                    'matched_object': target_obj.name,
                }
            else:
                return {
                    'intent_preserved': False,
                    'reason': 'Position mismatch',
                    'expected_position': new_position,
                    'found_position': target_obj.position,
                    'distance': distance,
                }

        return {
            'intent_preserved': False,
            'reason': 'Could not verify position',
        }

    def _colors_match(self, color1: tuple, color2: tuple, threshold: float = 0.05) -> bool:
        """Check if two colors match within threshold."""
        if len(color1) != len(color2):
            return False
        return all(abs(a - b) <= threshold for a, b in zip(color1, color2))

    def check_no_hallucinations(
        self,
        ground_truth_usd: str,
        generated_usd: str
    ) -> Dict[str, Any]:
        """
        Check if the agent added unwanted extra objects (hallucinations).

        Args:
            ground_truth_usd: Expected scene
            generated_usd: Generated scene

        Returns:
            Dict with hallucination metrics
        """
        gt_objects = self.parser.parse_usd(ground_truth_usd)
        gen_objects = self.parser.parse_usd(generated_usd)

        gt_count = len(gt_objects)
        gen_count = len(gen_objects)

        # Hallucination: generated more objects than expected
        extra_objects = gen_count - gt_count

        if extra_objects > 0:
            return {
                'no_hallucinations': False,
                'hallucination_count': extra_objects,
                'expected_count': gt_count,
                'generated_count': gen_count,
                'reason': f'Generated {extra_objects} extra object(s)',
            }
        elif extra_objects < 0:
            return {
                'no_hallucinations': False,
                'hallucination_count': 0,
                'missing_objects': abs(extra_objects),
                'expected_count': gt_count,
                'generated_count': gen_count,
                'reason': f'Missing {abs(extra_objects)} object(s)',
            }
        else:
            return {
                'no_hallucinations': True,
                'hallucination_count': 0,
                'expected_count': gt_count,
                'generated_count': gen_count,
                'reason': 'Correct number of objects',
            }

    def compute_all_metrics(
        self,
        operation_type: str,
        operation_params: Dict[str, Any],
        ground_truth_usd: str,
        generated_usd: str
    ) -> Dict[str, Any]:
        """
        Compute all semantic metrics.

        Args:
            operation_type: Type of operation
            operation_params: Operation parameters
            ground_truth_usd: Expected result
            generated_usd: Generated result

        Returns:
            Dict with all semantic metrics
        """
        intent_metrics = self.check_intent_preservation(
            operation_type, operation_params, ground_truth_usd, generated_usd
        )

        hallucination_metrics = self.check_no_hallucinations(
            ground_truth_usd, generated_usd
        )

        return {
            'intent': intent_metrics,
            'hallucinations': hallucination_metrics,
            'summary': {
                'semantically_correct': (
                    intent_metrics.get('intent_preserved', False) and
                    hallucination_metrics.get('no_hallucinations', False)
                ),
                'intent_preserved': intent_metrics.get('intent_preserved', False),
                'no_hallucinations': hallucination_metrics.get('no_hallucinations', False),
            }
        }


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Testing Semantic Metrics...")

    # Test USD
    test_usd_before = """#usda 1.0
def Xform "World"
{
}
"""

    test_usd_after = """#usda 1.0
def Xform "World"
{
    def Sphere "RedSphere_1"
    {
        double radius = 1.0
        double3 xformOp:translate = (0, 0, 0)
        color3f inputs:diffuseColor = (1.0, 0.0, 0.0)
    }
}
"""

    metrics_calc = SemanticMetrics()

    # Test add_primitive intent
    print("\n=== Test: Add Primitive Intent ===")
    params = {
        'primitive_type': 'sphere',
        'color': (1.0, 0.0, 0.0),
        'position': (0, 0, 0),
    }
    result = metrics_calc.check_intent_preservation(
        'add_primitive', params, test_usd_after, test_usd_after
    )
    print(f"Intent preserved: {result['intent_preserved']}")
    print(f"Reason: {result['reason']}")

    # Test hallucinations
    print("\n=== Test: No Hallucinations ===")
    result = metrics_calc.check_no_hallucinations(test_usd_after, test_usd_after)
    print(f"No hallucinations: {result['no_hallucinations']}")
    print(f"Reason: {result['reason']}")

    # Test with extra object
    test_usd_extra = test_usd_after + """
    def Cube "ExtraCube"
    {
        double size = 2.0
    }
"""
    print("\n=== Test: With Hallucination ===")
    result = metrics_calc.check_no_hallucinations(test_usd_after, test_usd_extra)
    print(f"No hallucinations: {result['no_hallucinations']}")
    print(f"Hallucination count: {result['hallucination_count']}")
    print(f"Reason: {result['reason']}")
