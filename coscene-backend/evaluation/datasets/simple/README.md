# Simple Test Cases (Level 1)

This directory contains simple test cases for evaluating the CoScene agent pipeline.

## Characteristics

- **Scene Complexity**: Empty or 1-2 objects
- **Operations**: Single atomic operation
- **References**: Absolute only (no "the red sphere")
- **Prompts**: Clear and unambiguous

## Operations Covered

1. **Add Primitive**: Add sphere, cube, cylinder
2. **Change Color**: Modify object material color
3. **Simple Transforms**: Basic positioning

## Example Test Cases

### Test Case: `simple_add_sphere_001`
```json
{
  "id": "simple_add_sphere_001",
  "initial_usd": "#usda 1.0\n(empty scene)",
  "target_usd": "#usda 1.0\n(scene with red sphere)",
  "prompt": "Add a red sphere at the center",
  "operation": "add_primitive"
}
```

### Test Case: `simple_change_color_001`
```json
{
  "id": "simple_change_color_001",
  "initial_usd": "#usda 1.0\n(scene with red sphere)",
  "target_usd": "#usda 1.0\n(scene with blue sphere)",
  "prompt": "Change the sphere's color to blue",
  "operation": "change_color"
}
```

## Dataset Format

Generated datasets are stored as JSON files with the following structure:

```json
{
  "metadata": {
    "version": "1.0",
    "complexity": "simple",
    "num_test_cases": 50,
    "generated_date": "2025-11-28"
  },
  "test_cases": [
    {
      "id": "simple_add_sphere_001",
      "complexity": "simple",
      "initial_usd": "...",
      "target_usd": "...",
      "edit_operation": {...},
      "prompt": "...",
      "prompt_variations": [...],
      "ground_truth_render_path": "...",
      "expected_metrics": {...}
    }
  ]
}
```

## Usage

```bash
# Generate simple test cases
python -m evaluation.generate_dataset --complexity simple --num-cases 50

# Evaluate agent on simple cases
python -m evaluation.run_evaluation --dataset datasets/simple/test_dataset.json
```
