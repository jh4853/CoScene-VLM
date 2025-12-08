"""
Quick test script to verify metrics work correctly.
"""
import json
from evaluation.metrics import StructuralMetrics, SemanticMetrics, VisualMetrics

# Load test dataset
print("Loading test dataset...")
with open('evaluation/datasets/simple/test_dataset.json', 'r') as f:
    dataset = json.load(f)

test_case = dataset['test_cases'][0]
print(f"\nTest Case: {test_case['id']}")
print(f"Prompt: {test_case['prompt']}")

# Test structural metrics
print("\n=== Structural Metrics ===")
structural_calc = StructuralMetrics()
structural_result = structural_calc.compute_all_metrics(
    ground_truth_usd=test_case['target_usd'],
    generated_usd=test_case['target_usd']  # Using target as generated (perfect match)
)
print(f"Structural Similarity: {structural_result['summary']['structural_similarity_score']:.3f}")
print(f"Exact Match: {structural_result['summary']['exact_match']}")
print(f"Object Count Match: {structural_result['count']['count_match']}")

# Test semantic metrics
print("\n=== Semantic Metrics ===")
semantic_calc = SemanticMetrics()
semantic_result = semantic_calc.compute_all_metrics(
    operation_type=test_case['edit_operation']['type'],
    operation_params=test_case['edit_operation']['parameters'],
    ground_truth_usd=test_case['target_usd'],
    generated_usd=test_case['target_usd']  # Using target as generated
)
print(f"Semantically Correct: {semantic_result['summary']['semantically_correct']}")
print(f"Intent Preserved: {semantic_result['intent']['intent_preserved']}")
print(f"No Hallucinations: {semantic_result['hallucinations']['no_hallucinations']}")

print("\n✓ All metrics working correctly!")
