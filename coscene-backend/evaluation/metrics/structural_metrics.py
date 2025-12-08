"""
Structural metrics for comparing USD scenes.
Compares object counts, types, positions, colors, and other properties.
"""
import re
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


class USDObject:
    """Parsed USD object with properties."""
    def __init__(self, name: str, prim_type: str):
        self.name = name
        self.prim_type = prim_type
        self.position: Optional[Tuple[float, float, float]] = None
        self.scale: Optional[Tuple[float, float, float]] = None
        self.color: Optional[Tuple[float, float, float]] = None
        self.metallic: Optional[float] = None
        self.roughness: Optional[float] = None
        self.radius: Optional[float] = None
        self.size: Optional[float] = None
        self.height: Optional[float] = None

    def __repr__(self):
        return f"USDObject(name='{self.name}', type='{self.prim_type}', position={self.position}, color={self.color})"


class USDParser:
    """Simple USD parser for extracting object information."""

    @staticmethod
    def parse_usd(usd_content: str) -> List[USDObject]:
        """
        Parse USD content and extract objects.

        Args:
            usd_content: USD file content as string

        Returns:
            List of USDObject instances
        """
        objects = []
        lines = usd_content.split('\n')

        current_object = None
        indent_stack = []

        for line in lines:
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # Detect object definitions (def Sphere "Name")
            obj_match = re.match(r'\s*def\s+(Sphere|Cube|Cylinder|Cone|Mesh)\s+"([^"]+)"', line)
            if obj_match:
                prim_type = obj_match.group(1)
                name = obj_match.group(2)

                # Save previous object if exists
                if current_object is not None:
                    objects.append(current_object)

                current_object = USDObject(name=name, prim_type=prim_type)
                continue

            # Parse properties if we're inside an object
            if current_object is not None:
                # Parse translate (position)
                pos_match = re.search(r'xformOp:translate\s*=\s*\(([^)]+)\)', line)
                if pos_match:
                    coords = pos_match.group(1).split(',')
                    current_object.position = tuple(float(c.strip()) for c in coords)

                # Parse scale
                scale_match = re.search(r'xformOp:scale\s*=\s*\(([^)]+)\)', line)
                if scale_match:
                    scales = scale_match.group(1).split(',')
                    current_object.scale = tuple(float(s.strip()) for s in scales)

                # Parse color
                color_match = re.search(r'diffuseColor\s*=\s*\(([^)]+)\)', line)
                if color_match:
                    colors = color_match.group(1).split(',')
                    current_object.color = tuple(float(c.strip()) for c in colors)

                # Parse metallic
                metal_match = re.search(r'metallic\s*=\s*([\d.]+)', line)
                if metal_match:
                    current_object.metallic = float(metal_match.group(1))

                # Parse roughness
                rough_match = re.search(r'roughness\s*=\s*([\d.]+)', line)
                if rough_match:
                    current_object.roughness = float(rough_match.group(1))

                # Parse radius
                radius_match = re.search(r'radius\s*=\s*([\d.]+)', line)
                if radius_match:
                    current_object.radius = float(radius_match.group(1))

                # Parse size (for Cube)
                size_match = re.search(r'size\s*=\s*([\d.]+)', line)
                if size_match:
                    current_object.size = float(size_match.group(1))

                # Parse height
                height_match = re.search(r'height\s*=\s*([\d.]+)', line)
                if height_match:
                    current_object.height = float(height_match.group(1))

        # Don't forget the last object
        if current_object is not None:
            objects.append(current_object)

        return objects


class StructuralMetrics:
    """Compute structural similarity metrics between USD scenes."""

    def __init__(self, position_threshold: float = 0.1, color_threshold: float = 0.05):
        """
        Initialize structural metrics calculator.

        Args:
            position_threshold: Maximum distance for positions to be considered equal
            color_threshold: Maximum color difference (per channel) for colors to be equal
        """
        self.position_threshold = position_threshold
        self.color_threshold = color_threshold
        self.parser = USDParser()

    def compute_object_count_accuracy(self, ground_truth: List[USDObject], generated: List[USDObject]) -> Dict[str, Any]:
        """
        Compare object counts.

        Returns:
            Dict with count metrics
        """
        gt_count = len(ground_truth)
        gen_count = len(generated)

        return {
            'ground_truth_count': gt_count,
            'generated_count': gen_count,
            'count_match': gt_count == gen_count,
            'count_difference': abs(gt_count - gen_count),
        }

    def compute_type_accuracy(self, ground_truth: List[USDObject], generated: List[USDObject]) -> Dict[str, Any]:
        """
        Compare object types.

        Returns:
            Dict with type accuracy metrics
        """
        if not ground_truth:
            return {'type_accuracy': 1.0 if not generated else 0.0, 'type_matches': 0}

        # Count types in each scene
        gt_types = {}
        for obj in ground_truth:
            gt_types[obj.prim_type] = gt_types.get(obj.prim_type, 0) + 1

        gen_types = {}
        for obj in generated:
            gen_types[obj.prim_type] = gen_types.get(obj.prim_type, 0) + 1

        # Count matches
        matches = 0
        for prim_type, count in gt_types.items():
            matches += min(count, gen_types.get(prim_type, 0))

        accuracy = matches / len(ground_truth) if ground_truth else 0.0

        return {
            'type_accuracy': accuracy,
            'type_matches': matches,
            'ground_truth_types': gt_types,
            'generated_types': gen_types,
        }

    def _find_best_match(self, target_obj: USDObject, candidate_objs: List[USDObject]) -> Optional[USDObject]:
        """
        Find the best matching object based on type and position.

        Args:
            target_obj: Object to match
            candidate_objs: List of candidate objects

        Returns:
            Best matching object or None
        """
        best_match = None
        best_distance = float('inf')

        for candidate in candidate_objs:
            # Must match type
            if candidate.prim_type != target_obj.prim_type:
                continue

            # Calculate position distance if both have positions
            if target_obj.position and candidate.position:
                distance = sum((a - b) ** 2 for a, b in zip(target_obj.position, candidate.position)) ** 0.5
                if distance < best_distance:
                    best_distance = distance
                    best_match = candidate
            elif not best_match:
                # If no position info, just match by type
                best_match = candidate

        return best_match

    def compute_position_mae(self, ground_truth: List[USDObject], generated: List[USDObject]) -> Dict[str, Any]:
        """
        Compute Mean Absolute Error for object positions.

        Returns:
            Dict with position error metrics
        """
        errors = []
        matched_pairs = []

        # Match each ground truth object with best generated object
        used_gen_objs = set()
        for gt_obj in ground_truth:
            if not gt_obj.position:
                continue

            # Find best match among unused generated objects
            available_gen = [obj for obj in generated if obj not in used_gen_objs]
            match = self._find_best_match(gt_obj, available_gen)

            if match and match.position:
                # Calculate error
                error = sum(abs(a - b) for a, b in zip(gt_obj.position, match.position)) / 3.0
                errors.append(error)
                matched_pairs.append((gt_obj, match))
                used_gen_objs.add(match)

        mae = sum(errors) / len(errors) if errors else 0.0

        return {
            'position_mae': mae,
            'num_matched_objects': len(matched_pairs),
            'position_errors': errors,
            'positions_within_threshold': sum(1 for e in errors if e <= self.position_threshold),
        }

    def compute_color_accuracy(self, ground_truth: List[USDObject], generated: List[USDObject]) -> Dict[str, Any]:
        """
        Compute color matching accuracy.

        Returns:
            Dict with color accuracy metrics
        """
        color_matches = 0
        total_with_color = 0
        color_errors = []

        # Match objects and compare colors
        used_gen_objs = set()
        for gt_obj in ground_truth:
            if not gt_obj.color:
                continue

            total_with_color += 1

            # Find best match
            available_gen = [obj for obj in generated if obj not in used_gen_objs]
            match = self._find_best_match(gt_obj, available_gen)

            if match and match.color:
                # Calculate color difference (RGB distance)
                color_diff = sum(abs(a - b) for a, b in zip(gt_obj.color, match.color)) / 3.0
                color_errors.append(color_diff)

                # Check if within threshold
                if color_diff <= self.color_threshold:
                    color_matches += 1

                used_gen_objs.add(match)

        accuracy = color_matches / total_with_color if total_with_color > 0 else 0.0

        return {
            'color_accuracy': accuracy,
            'color_matches': color_matches,
            'total_colored_objects': total_with_color,
            'avg_color_error': sum(color_errors) / len(color_errors) if color_errors else 0.0,
        }

    def compute_all_metrics(self, ground_truth_usd: str, generated_usd: str) -> Dict[str, Any]:
        """
        Compute all structural metrics.

        Args:
            ground_truth_usd: Ground truth USD content
            generated_usd: Generated USD content

        Returns:
            Dict with all structural metrics
        """
        # Parse USD files
        gt_objects = self.parser.parse_usd(ground_truth_usd)
        gen_objects = self.parser.parse_usd(generated_usd)

        logger.debug(f"Parsed {len(gt_objects)} ground truth objects")
        logger.debug(f"Parsed {len(gen_objects)} generated objects")

        # Compute metrics
        count_metrics = self.compute_object_count_accuracy(gt_objects, gen_objects)
        type_metrics = self.compute_type_accuracy(gt_objects, gen_objects)
        position_metrics = self.compute_position_mae(gt_objects, gen_objects)
        color_metrics = self.compute_color_accuracy(gt_objects, gen_objects)

        return {
            'count': count_metrics,
            'type': type_metrics,
            'position': position_metrics,
            'color': color_metrics,
            'summary': {
                'exact_match': (
                    count_metrics['count_match'] and
                    type_metrics['type_accuracy'] == 1.0 and
                    position_metrics['position_mae'] < self.position_threshold and
                    color_metrics['color_accuracy'] == 1.0
                ),
                'structural_similarity_score': (
                    (1.0 if count_metrics['count_match'] else 0.5) * 0.2 +
                    type_metrics['type_accuracy'] * 0.3 +
                    (1.0 - min(position_metrics['position_mae'], 1.0)) * 0.3 +
                    color_metrics['color_accuracy'] * 0.2
                ),
            }
        }


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Test USD parsing
    test_usd = """#usda 1.0
(
    defaultPrim = "World"
    upAxis = "Z"
)

def Xform "World"
{
    def Sphere "RedSphere_1"
    {
        double radius = 1.0
        double3 xformOp:translate = (0, 0, 0)
        double3 xformOp:scale = (1.0, 1.0, 1.0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]

        def Material "Material"
        {
            token outputs:surface.connect = </World/RedSphere_1/Material/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (1.0, 0.0, 0.0)
                float inputs:metallic = 0.0
                float inputs:roughness = 0.5
                token outputs:surface
            }
        }
    }
}
"""

    print("Testing USD Parser...")
    parser = USDParser()
    objects = parser.parse_usd(test_usd)
    print(f"Parsed {len(objects)} objects:")
    for obj in objects:
        print(f"  {obj}")

    print("\nTesting Structural Metrics...")
    metrics_calculator = StructuralMetrics()

    # Test with identical scenes
    result = metrics_calculator.compute_all_metrics(test_usd, test_usd)
    print(f"Identical scenes - Structural Similarity: {result['summary']['structural_similarity_score']:.2f}")
    print(f"Exact match: {result['summary']['exact_match']}")

    # Test with different scene
    test_usd_2 = test_usd.replace("(1.0, 0.0, 0.0)", "(0.0, 1.0, 0.0)")  # Different color
    result = metrics_calculator.compute_all_metrics(test_usd, test_usd_2)
    print(f"\nDifferent color - Structural Similarity: {result['summary']['structural_similarity_score']:.2f}")
    print(f"Color accuracy: {result['color']['color_accuracy']:.2f}")
