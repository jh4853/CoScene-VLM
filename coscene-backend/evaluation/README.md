# CoScene Evaluation Framework

This directory contains the evaluation framework for the CoScene agentic 3D scene editing pipeline.

## Overview

The evaluation framework generates synthetic test data (USD files + natural language prompts) and provides quantitative metrics to measure agent performance as complexity is added to the system.

## Structure

```
evaluation/
├── EVALUATION_PLAN.md          # Detailed implementation plan
├── README.md                   # This file
├── generators/                 # Data generation modules
│   ├── template_library.py     # USD operation templates
│   ├── usd_generator.py        # Procedural USD generation
│   └── prompt_generator.py     # NL prompt generation
├── metrics/                    # Evaluation metrics
│   ├── structural_metrics.py   # Object count, types, hierarchy
│   ├── visual_metrics.py       # Image similarity (SSIM, LPIPS)
│   └── semantic_metrics.py     # Intent matching
├── datasets/                   # Generated test datasets
│   ├── simple/                 # Level 1 test cases
│   ├── medium/                 # Level 2 test cases
│   └── complex/                # Level 3 test cases
├── generate_dataset.py         # Dataset generation script
├── run_evaluation.py           # Main evaluation runner
└── config.yaml                 # Evaluation configuration
```

## Quick Start

### 1. Generate Test Dataset

```bash
cd coscene-backend

# Generate 50 simple test cases
python3 -m evaluation.generate_dataset --complexity simple --num-cases 50

# Save individual USD files for inspection
python3 -m evaluation.generate_dataset --complexity simple --num-cases 20 --save-usd-files

# Use custom seed for reproducibility
python3 -m evaluation.generate_dataset --complexity simple --num-cases 50 --seed 123
```

### 2. Run Evaluation

```bash
# Evaluate agent on test dataset
python3 -m evaluation.run_evaluation --dataset evaluation/datasets/simple/test_dataset.json

# Specify Blender path (required if Blender is not in PATH)
python3 -m evaluation.run_evaluation \
  --dataset evaluation/datasets/simple/test_dataset.json \
  --blender-path /Applications/Blender.app/Contents/MacOS/Blender

# Limit to first 10 cases for quick testing
python3 -m evaluation.run_evaluation --dataset evaluation/datasets/simple/test_dataset.json --limit 10

# Specify output location
python3 -m evaluation.run_evaluation --dataset evaluation/datasets/simple/test_dataset.json --output results/my_eval

# Verbose mode for debugging
python3 -m evaluation.run_evaluation --dataset evaluation/datasets/simple/test_dataset.json --verbose

# Combine options
python3 -m evaluation.run_evaluation \
  --dataset evaluation/datasets/simple/test_dataset.json \
  --blender-path /path/to/blender \
  --limit 10 \
  --verbose
```

### 3. View Results

```bash
# View markdown report (with embedded images!)
cat evaluation/results/test_dataset_YYYYMMDD_HHMMSS.md

# Or open in a markdown viewer to see rendered images
open evaluation/results/test_dataset_YYYYMMDD_HHMMSS.md

# View JSON report
cat evaluation/results/test_dataset_YYYYMMDD_HHMMSS.json

# Browse rendered frames
ls evaluation/results/test_dataset_YYYYMMDD_HHMMSS_renders/
```

The markdown report includes:
- Summary statistics and aggregate metrics
- Table of all test cases with results
- **Visual Comparison section** with side-by-side images (Ground Truth vs Generated)
- Visual metrics (SSIM, PSNR, MSE) when available
- Failed cases details

## Test Case Complexity Levels

### Simple (Level 1)
- Empty scene or 1-2 existing objects
- Single atomic operation (add, color change)
- Absolute references only
- Clear, unambiguous prompts

**Example**: "Add a red sphere at the center"

### Medium (Level 2)
- 2-4 existing objects
- 1-2 operations
- Relative references ("next to the cube")
- Spatial reasoning required

**Example**: "Move the red sphere next to the blue cube"

### Complex (Level 3)
- 5+ objects
- 3+ operations or compositional tasks
- Complex spatial relationships
- Potentially ambiguous prompts

**Example**: "Make the scene look like a sunset with warm lighting"

## Evaluation Metrics

### Structural Metrics (USD-based)
- Object count accuracy
- Object type accuracy
- Position MAE (mean absolute error)
- Scale MAE
- Color accuracy
- Material property accuracy

### Visual Metrics (Render-based)
- SSIM (Structural Similarity Index)
- MSE (Mean Squared Error)
- PSNR (Peak Signal-to-Noise Ratio)

**NEW**: Visual comparison with ground truth renders embedded in markdown reports!
See [VISUAL_COMPARISON_FEATURE.md](VISUAL_COMPARISON_FEATURE.md) for details.

### Semantic Metrics
- Intent preservation
- Hallucination rate
- Reference resolution accuracy

### Agent Performance Metrics
- Success rate
- Token usage
- Latency
- Verification iterations

## Configuration

See `config.yaml` for configuration options including:
- Dataset generation parameters
- Evaluation settings
- Ablation study configurations
- Output formats

## Dependencies

```bash
# Install additional dependencies for evaluation
pip install scikit-image pillow matplotlib pandas jinja2
```

## References

- See `EVALUATION_PLAN.md` for detailed implementation plan
- See `coscene-backend/agents/` for agent pipeline implementation
- See `Project_Proposal.pdf` for project overview
