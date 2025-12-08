# Medium Test Cases (Level 2)

This directory contains medium-complexity test cases for evaluating the CoScene agent pipeline.

## Characteristics

- **Scene Complexity**: 2-4 existing objects
- **Operations**: 1-2 operations, multi-object addition
- **References**: Relative references ("next to the cube")
- **Prompts**: Require spatial reasoning

## Operations Covered

1. **Multi-Object Addition**: Add 2-3 objects at once
2. **Relative Positioning**: "next to", "above", "to the left of"
3. **Object Manipulation**: Move, scale, rotate existing objects
4. **Material Changes**: Modify multiple properties

## Example Test Cases

### Test Case: `medium_relative_position_001`
```json
{
  "id": "medium_relative_position_001",
  "initial_usd": "(scene with blue cube at origin)",
  "target_usd": "(scene with blue cube and red sphere next to it)",
  "prompt": "Add a red sphere next to the blue cube",
  "operation": "add_primitive_relative"
}
```

### Test Case: `medium_move_object_001`
```json
{
  "id": "medium_move_object_001",
  "initial_usd": "(scene with red sphere at origin)",
  "target_usd": "(scene with red sphere at (2,0,0))",
  "prompt": "Move the red sphere 2 units to the right",
  "operation": "move_object"
}
```

## Dataset Format

Same JSON structure as simple test cases, with additional complexity in operations.

## Usage

```bash
# Generate medium test cases
python -m evaluation.generate_dataset --complexity medium --num-cases 100

# Evaluate agent on medium cases
python -m evaluation.run_evaluation --dataset datasets/medium/test_dataset.json
```
