# Complex Test Cases (Level 3)

This directory contains complex test cases for evaluating the CoScene agent pipeline.

## Characteristics

- **Scene Complexity**: 5+ objects
- **Operations**: 3+ operations or compositional tasks
- **References**: Complex spatial relationships
- **Prompts**: May be ambiguous, require interpretation

## Operations Covered

1. **Scene Composition**: Create multi-object scenes from descriptions
2. **Style/Mood Changes**: "Make it look like sunset", "Create a cozy room"
3. **Complex Spatial Arrangements**: Grids, patterns, hierarchies
4. **Multi-Step Edits**: Chains of dependent operations

## Example Test Cases

### Test Case: `complex_composition_001`
```json
{
  "id": "complex_composition_001",
  "initial_usd": "(empty scene)",
  "target_usd": "(scene with 5 spheres in a circle)",
  "prompt": "Create a circle of 5 colored spheres",
  "operation": "scene_composition"
}
```

### Test Case: `complex_mood_001`
```json
{
  "id": "complex_mood_001",
  "initial_usd": "(basic scene with objects)",
  "target_usd": "(scene with warm lighting and colors)",
  "prompt": "Make the scene look like sunset",
  "operation": "style_change"
}
```

## Dataset Format

Same JSON structure as simple/medium test cases, with higher complexity.

## Usage

```bash
# Generate complex test cases
python -m evaluation.generate_dataset --complexity complex --num-cases 100

# Evaluate agent on complex cases
python -m evaluation.run_evaluation --dataset datasets/complex/test_dataset.json
```
