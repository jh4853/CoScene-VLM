"""
Main evaluation runner for CoScene agent pipeline.

Usage:
    python -m evaluation.run_evaluation --dataset evaluation/datasets/simple/test_dataset.json
    python -m evaluation.run_evaluation --dataset evaluation/datasets/simple/test_dataset.json --limit 10
"""
import argparse
import json
import yaml
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import time

# Import metrics
from evaluation.metrics import StructuralMetrics, VisualMetrics, SemanticMetrics

# Import agent
from agents.scene_editor import process_scene_edit

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Main evaluation coordinator."""

    def __init__(self, config: Dict[str, Any], renders_dir: Path = None):
        """
        Initialize evaluation runner.

        Args:
            config: Configuration dictionary
            renders_dir: Directory to save rendered frames (optional)
        """
        self.config = config
        self.structural_metrics = StructuralMetrics()
        self.visual_metrics = VisualMetrics()
        self.semantic_metrics = SemanticMetrics()
        self.renders_dir = renders_dir
        if self.renders_dir:
            self.renders_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Saving renders to: {self.renders_dir}")

    async def evaluate_test_case(self, test_case: Dict[str, Any], case_num: int, total: int) -> Dict[str, Any]:
        """
        Evaluate a single test case.

        Args:
            test_case: Test case dictionary
            case_num: Current case number
            total: Total number of cases

        Returns:
            Evaluation result dictionary
        """
        test_id = test_case['id']
        logger.info(f"[{case_num}/{total}] Evaluating {test_id}...")

        result = {
            'test_case_id': test_id,
            'prompt': test_case['prompt'],
            'complexity': test_case['complexity'],
            'timestamp': datetime.now().isoformat(),
        }

        start_time = time.time()

        try:
            # Run agent on test case
            logger.debug(f"  Running agent with prompt: {test_case['prompt']}")
            agent_result = await process_scene_edit(
                session_id=f"eval_{test_id}",
                user_prompt=test_case['prompt'],
                current_usd=test_case['initial_usd']
            )

            elapsed_time = time.time() - start_time

            # Check if agent succeeded
            if agent_result['status'] != 'success':
                result['success'] = False
                # Get error message and handle empty strings
                error_msg = agent_result.get('error_message', '')
                # If error message is empty or None, provide a descriptive default
                if not error_msg or error_msg.strip() == '':
                    error_msg = f"Agent completed with status '{agent_result['status']}' but no error message provided"
                result['error'] = error_msg
                result['latency'] = elapsed_time
                logger.warning(f"  Agent failed: {result['error']}")
                return result

            result['success'] = True
            result['generated_usd'] = agent_result['generated_usd']
            result['latency'] = elapsed_time

            # Compute structural metrics
            logger.debug("  Computing structural metrics...")
            structural_result = self.structural_metrics.compute_all_metrics(
                ground_truth_usd=test_case['target_usd'],
                generated_usd=agent_result['generated_usd']
            )
            result['structural_metrics'] = structural_result

            # Compute semantic metrics
            logger.debug("  Computing semantic metrics...")
            semantic_result = self.semantic_metrics.compute_all_metrics(
                operation_type=test_case['edit_operation']['type'],
                operation_params=test_case['edit_operation']['parameters'],
                ground_truth_usd=test_case['target_usd'],
                generated_usd=agent_result['generated_usd']
            )
            result['semantic_metrics'] = semantic_result

            # Save rendered frames (if available)
            saved_render_paths = {}
            if agent_result.get('output_scene_renders') and self.renders_dir:
                logger.debug("  Saving rendered frames...")
                for camera_angle, image_bytes in agent_result['output_scene_renders'].items():
                    filename = f"{test_id}_{camera_angle}_generated.png"
                    render_path = self.renders_dir / filename
                    with open(render_path, 'wb') as f:
                        f.write(image_bytes)
                    saved_render_paths[f"{camera_angle}_generated"] = str(
                        render_path)
                    logger.debug(
                        f"    Saved {camera_angle} render to {filename}")

                result['render_paths'] = saved_render_paths

            # Save intermediate renders from verification loop
            intermediate_render_paths = []
            if agent_result.get('intermediate_renders') and self.renders_dir:
                logger.debug(
                    "  Saving intermediate renders from verification loop...")
                for idx, intermediate in enumerate(agent_result['intermediate_renders']):
                    step_name = intermediate.get('step', f'step_{idx}')
                    step_paths = {}

                    for camera_angle, image_bytes in intermediate.get('renders', {}).items():
                        filename = f"{test_id}_{step_name}_{camera_angle}.png"
                        render_path = self.renders_dir / filename
                        with open(render_path, 'wb') as f:
                            f.write(image_bytes)
                        step_paths[camera_angle] = str(render_path)
                        logger.debug(
                            f"    Saved intermediate {step_name}/{camera_angle} to {filename}")

                    intermediate_render_paths.append({
                        'step': step_name,
                        'paths': step_paths,
                        'verification_result': intermediate.get('verification_result')
                    })

                result['intermediate_render_paths'] = intermediate_render_paths

            # Store verification metadata
            if agent_result.get('verification_attempts') is not None:
                result['verification_metadata'] = {
                    'attempts': agent_result.get('verification_attempts', 0),
                    'passed': agent_result.get('verification_passed', False),
                    'feedback': agent_result.get('verification_feedback', ''),
                    'issues': agent_result.get('verification_issues', []),
                    'confidence': agent_result.get('verification_confidence', 0.0)
                }

            # Optionally render input and ground truth for visual comparison
            input_render_paths = {}
            ground_truth_render_paths = {}
            if self.renders_dir:
                logger.debug(
                    "  Rendering input and ground truth for comparison...")
                try:
                    from services.render_service import get_render_service
                    render_service = get_render_service()

                    # Check if Blender is available
                    if await render_service.check_blender_available():
                        # Render input USD
                        if test_case.get('initial_usd'):
                            logger.debug("    Rendering input scene...")
                            input_renders = await render_service.render_multiview(
                                usd_content=test_case['initial_usd'],
                                quality="preview"
                            )

                            for camera_angle, (image_bytes, render_time_ms) in input_renders.items():
                                filename = f"{test_id}_{camera_angle}_input.png"
                                render_path = self.renders_dir / filename
                                with open(render_path, 'wb') as f:
                                    f.write(image_bytes)
                                input_render_paths[f"{camera_angle}_input"] = str(
                                    render_path)
                                logger.debug(
                                    f"    Saved input {camera_angle} to {filename}")

                            result['input_render_paths'] = input_render_paths

                        # Render ground truth USD
                        if test_case.get('target_usd'):
                            logger.debug("    Rendering ground truth scene...")
                            gt_renders = await render_service.render_multiview(
                                usd_content=test_case['target_usd'],
                                quality="preview"
                            )

                            for camera_angle, (image_bytes, render_time_ms) in gt_renders.items():
                                filename = f"{test_id}_{camera_angle}_ground_truth.png"
                                render_path = self.renders_dir / filename
                                with open(render_path, 'wb') as f:
                                    f.write(image_bytes)
                                ground_truth_render_paths[f"{camera_angle}_ground_truth"] = str(
                                    render_path)
                                logger.debug(
                                    f"    Saved ground truth {camera_angle} to {filename}")

                            result['ground_truth_render_paths'] = ground_truth_render_paths
                except Exception as e:
                    logger.warning(
                        f"  Could not render input/ground truth: {e}")

            # Compute visual metrics (if renders available)
            visual_result = None
            if agent_result.get('output_scene_renders') and ground_truth_render_paths:
                logger.debug("  Computing visual metrics...")
                try:
                    # Compare perspective view
                    if 'perspective' in agent_result['output_scene_renders']:
                        gt_bytes = None
                        for camera_angle, (image_bytes, _) in gt_renders.items():
                            if camera_angle == 'perspective':
                                gt_bytes = image_bytes
                                break

                        if gt_bytes:
                            gen_bytes = agent_result['output_scene_renders']['perspective']
                            visual_result = self.visual_metrics.compute_metrics_from_bytes(
                                ground_truth_bytes=gt_bytes,
                                generated_bytes=gen_bytes
                            )
                            result['visual_metrics'] = visual_result
                except Exception as e:
                    logger.warning(f"  Visual metrics computation failed: {e}")
                    result['visual_metrics'] = {
                        'note': 'Visual metrics computation failed', 'error': str(e)}
            elif agent_result.get('output_scene_renders'):
                result['visual_metrics'] = {
                    'note': 'Ground truth rendering not available'}
            else:
                result['visual_metrics'] = {'note': 'No renders available'}

            # Log summary
            log_msg = (f"  ✓ Success | Structural: {structural_result['summary']['structural_similarity_score']:.2f} | "
                       f"Semantic: {semantic_result['summary']['semantically_correct']}")

            # Add visual metrics to log if available
            if visual_result and 'ssim' in visual_result:
                log_msg += f" | SSIM: {visual_result['ssim']:.3f}"

            log_msg += f" | Latency: {elapsed_time:.2f}s"
            logger.info(log_msg)

        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            result['latency'] = time.time() - start_time
            logger.error(f"  ✗ Exception: {e}")

        return result

    async def evaluate_dataset(
        self,
        dataset_path: str,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        Evaluate entire dataset.

        Args:
            dataset_path: Path to dataset JSON file
            limit: Maximum number of test cases to evaluate (None for all)

        Returns:
            Evaluation results dictionary
        """
        # Load dataset
        logger.info(f"Loading dataset from {dataset_path}...")
        with open(dataset_path, 'r') as f:
            dataset = json.load(f)

        test_cases = dataset['test_cases']
        if limit:
            test_cases = test_cases[:limit]
            logger.info(f"Limiting evaluation to {limit} test cases")

        logger.info(f"Loaded {len(test_cases)} test cases")

        # Evaluate each test case
        results = []
        for i, test_case in enumerate(test_cases, 1):
            result = await self.evaluate_test_case(test_case, i, len(test_cases))
            results.append(result)

        # Compute aggregate metrics
        aggregate_metrics = self.compute_aggregate_metrics(results)

        return {
            'metadata': {
                'dataset_path': dataset_path,
                'dataset_metadata': dataset.get('metadata', {}),
                'num_test_cases': len(test_cases),
                'evaluation_date': datetime.now().isoformat(),
                'config': self.config,
            },
            'test_case_results': results,
            'aggregate_metrics': aggregate_metrics,
        }

    def compute_aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute aggregate metrics across all test cases.

        Args:
            results: List of test case results

        Returns:
            Aggregate metrics dictionary
        """
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        failed = total - successful

        # Collect metrics from successful cases
        structural_scores = []
        semantic_correct = []
        latencies = []
        ssim_scores = []
        psnr_scores = []
        mse_scores = []

        for r in results:
            if r.get('success'):
                if 'structural_metrics' in r:
                    structural_scores.append(
                        r['structural_metrics']['summary']['structural_similarity_score']
                    )
                if 'semantic_metrics' in r:
                    semantic_correct.append(
                        r['semantic_metrics']['summary']['semantically_correct']
                    )
                if 'latency' in r:
                    latencies.append(r['latency'])

                # Visual metrics
                if 'visual_metrics' in r and 'ssim' in r['visual_metrics']:
                    ssim_scores.append(r['visual_metrics']['ssim'])
                    psnr_scores.append(r['visual_metrics']['psnr'])
                    mse_scores.append(r['visual_metrics']['mse'])

        aggregate = {
            'total_cases': total,
            'successful_cases': successful,
            'failed_cases': failed,
            'success_rate': successful / total if total > 0 else 0.0,
            'structural_similarity': {
                'mean': sum(structural_scores) / len(structural_scores) if structural_scores else 0.0,
                'min': min(structural_scores) if structural_scores else 0.0,
                'max': max(structural_scores) if structural_scores else 0.0,
            },
            'semantic_correctness': {
                'correct_count': sum(semantic_correct),
                'total_count': len(semantic_correct),
                'accuracy': sum(semantic_correct) / len(semantic_correct) if semantic_correct else 0.0,
            },
            'latency': {
                'mean': sum(latencies) / len(latencies) if latencies else 0.0,
                'min': min(latencies) if latencies else 0.0,
                'max': max(latencies) if latencies else 0.0,
                'total': sum(latencies),
            },
        }

        # Add visual metrics if available
        if ssim_scores:
            aggregate['visual_similarity'] = {
                'ssim_mean': sum(ssim_scores) / len(ssim_scores),
                'ssim_min': min(ssim_scores),
                'ssim_max': max(ssim_scores),
                'psnr_mean': sum(psnr_scores) / len(psnr_scores),
                'psnr_min': min(psnr_scores),
                'psnr_max': max(psnr_scores),
                'mse_mean': sum(mse_scores) / len(mse_scores),
                'cases_with_visual_metrics': len(ssim_scores),
            }

        return aggregate

    def generate_report(self, evaluation_results: Dict[str, Any], output_path: Path):
        """
        Generate evaluation report.

        Args:
            evaluation_results: Evaluation results dictionary
            output_path: Path to save report
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save JSON report
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(evaluation_results, f, indent=2)
        logger.info(f"✓ Saved JSON report to {json_path}")

        # Generate markdown report
        md_path = output_path.with_suffix('.md')
        # Pass renders directory name for correct relative paths
        renders_dir_name = self.renders_dir.name if self.renders_dir else None
        markdown = self._generate_markdown_report(
            evaluation_results, renders_dir_name)
        with open(md_path, 'w') as f:
            f.write(markdown)
        logger.info(f"✓ Saved Markdown report to {md_path}")

    def _generate_markdown_report(self, results: Dict[str, Any], renders_dir_name: str = None) -> str:
        """
        Generate markdown report.

        Args:
            results: Evaluation results dictionary
            renders_dir_name: Name of renders directory (for relative paths)
        """
        metadata = results['metadata']
        aggregate = results['aggregate_metrics']

        md = f"""# CoScene Evaluation Report

**Date**: {metadata['evaluation_date']}
**Dataset**: {metadata['dataset_path']}
**Test Cases**: {metadata['num_test_cases']}

## Summary

- **Success Rate**: {aggregate['success_rate']:.1%} ({aggregate['successful_cases']}/{aggregate['total_cases']})
- **Failed Cases**: {aggregate['failed_cases']}

## Aggregate Metrics

### Structural Similarity
- **Mean**: {aggregate['structural_similarity']['mean']:.3f}
- **Min**: {aggregate['structural_similarity']['min']:.3f}
- **Max**: {aggregate['structural_similarity']['max']:.3f}

### Semantic Correctness
- **Accuracy**: {aggregate['semantic_correctness']['accuracy']:.1%}
- **Correct**: {aggregate['semantic_correctness']['correct_count']}/{aggregate['semantic_correctness']['total_count']}
"""

        # Add visual similarity section if available
        if 'visual_similarity' in aggregate:
            vs = aggregate['visual_similarity']
            md += f"""
### Visual Similarity (Ground Truth vs Generated)
- **SSIM Mean**: {vs['ssim_mean']:.3f} (range: {vs['ssim_min']:.3f} - {vs['ssim_max']:.3f})
- **PSNR Mean**: {vs['psnr_mean']:.1f}dB (range: {vs['psnr_min']:.1f} - {vs['psnr_max']:.1f}dB)
- **MSE Mean**: {vs['mse_mean']:.6f}
- **Cases with Visual Metrics**: {vs['cases_with_visual_metrics']}/{aggregate['total_cases']}
"""

        md += f"""
### Performance
- **Mean Latency**: {aggregate['latency']['mean']:.2f}s
- **Min Latency**: {aggregate['latency']['min']:.2f}s
- **Max Latency**: {aggregate['latency']['max']:.2f}s
- **Total Time**: {aggregate['latency']['total']:.2f}s

## Test Case Results

| ID | Prompt | Success | Structural | Semantic | SSIM | PSNR | Latency | Retries |
|----|--------|---------|------------|----------|------|------|---------|---------|
"""

        for r in results['test_case_results']:
            test_id = r['test_case_id']
            prompt = r['prompt'][:40] + \
                '...' if len(r['prompt']) > 40 else r['prompt']
            success = '✓' if r.get('success') else '✗'

            if r.get('success'):
                # Structural metrics
                structural = f"{r['structural_metrics']['summary']['structural_similarity_score']:.2f}"

                # Semantic metrics
                semantic = '✓' if r['semantic_metrics']['summary']['semantically_correct'] else '✗'

                # Visual metrics
                vm = r.get('visual_metrics', {})
                if 'ssim' in vm:
                    ssim = f"{vm['ssim']:.3f}"
                    psnr = f"{vm['psnr']:.1f}dB"
                else:
                    ssim = '-'
                    psnr = '-'

                # Performance
                latency = f"{r['latency']:.2f}s"

                # Verification retries
                retries = r.get('verification_metadata', {}).get('attempts', 0)
            else:
                structural = '-'
                semantic = '-'
                ssim = '-'
                psnr = '-'
                latency = f"{r.get('latency', 0):.2f}s"
                retries = '-'

            md += f"| {test_id} | {prompt} | {success} | {structural} | {semantic} | {ssim} | {psnr} | {latency} | {retries} |\n"

        # Add visual comparison section if renders are available
        renders_available = any(r.get('render_paths')
                                for r in results['test_case_results'])
        if renders_available:
            md += """
## Visual Comparison

Below are side-by-side comparisons showing the input scene, ground truth (expected), and generated renders for each test case.

"""
            for r in results['test_case_results']:
                if not r.get('render_paths'):
                    continue

                test_id = r['test_case_id']
                prompt = r['prompt']

                md += f"### {test_id}\n\n"
                md += f"**Prompt**: {prompt}\n\n"

                # Add verification metadata if available
                if r.get('verification_metadata'):
                    vm = r['verification_metadata']
                    md += f"**Verification**: "
                    confidence = vm.get('confidence', 0.0)
                    confidence_str = f"{confidence:.2f}" if confidence is not None else "N/A"
                    attempts = vm.get('attempts', 0)

                    if vm.get('passed', False):
                        md += f"✓ PASSED (confidence: {confidence_str}, attempts: {attempts})\n\n"
                    else:
                        md += f"✗ FAILED after {attempts} attempts (confidence: {confidence_str})\n"
                        if vm.get('issues'):
                            md += f"  - Issues: {', '.join(vm['issues'])}\n"
                        md += "\n"

                # Get paths (convert to relative paths for markdown)
                input_paths = r.get('input_render_paths', {})
                gt_paths = r.get('ground_truth_render_paths', {})
                gen_paths = r.get('render_paths', {})

                # Use actual renders directory name for correct relative paths
                renders_path_prefix = renders_dir_name if renders_dir_name else 'renders'

                # Define camera angles to display
                camera_angles = ['perspective', 'front', 'top', 'side']

                # Helper function to extract path for a specific camera angle
                def get_render_path(paths_dict, angle):
                    for key, path in paths_dict.items():
                        if angle in key:
                            return Path(path).name
                    return None

                # Create multiview comparison table
                md += "#### Multiview Comparison\n\n"
                md += "| View | Input | Ground Truth | Generated |\n"
                md += "|------|-------|--------------|----------|\n"

                for angle in camera_angles:
                    # Get paths for each angle
                    input_path = get_render_path(input_paths, angle)
                    gt_path = get_render_path(gt_paths, angle)
                    gen_path = get_render_path(gen_paths, angle)

                    # Build cells
                    input_col = f"![Input {angle}]({renders_path_prefix}/{input_path})" if input_path else "*(not rendered)*"
                    gt_col = f"![GT {angle}]({renders_path_prefix}/{gt_path})" if gt_path else "*(not rendered)*"
                    gen_col = f"![Gen {angle}]({renders_path_prefix}/{gen_path})" if gen_path else "*(not rendered)*"

                    # Add row
                    md += f"| **{angle.capitalize()}** | {input_col} | {gt_col} | {gen_col} |\n"

                md += "\n"

                # Add metrics if available
                if r.get('visual_metrics') and 'ssim' in r.get('visual_metrics', {}):
                    vm = r['visual_metrics']
                    # Check that values are not None
                    if vm['ssim'] is not None and vm['psnr'] is not None:
                        md += f"**Visual Metrics**: SSIM={vm['ssim']:.3f}, PSNR={vm['psnr']:.2f}dB, MSE={vm['mse']:.6f}\n\n"

                # Add intermediate renders section if available and there were retries
                # Only show if there were multiple attempts (i.e., actual retries happened)
                intermediate_paths = r.get('intermediate_render_paths', [])
                verification_meta = r.get('verification_metadata', {})
                num_attempts = verification_meta.get('attempts', 0)

                # Show intermediate steps only if there were retries (attempts > 1)
                if intermediate_paths and num_attempts > 0:
                    md += f"#### Intermediate Steps (Verification Loop)\n\n"
                    md += "This section shows the progression through verification and fix iterations:\n\n"

                    for step_data in r['intermediate_render_paths']:
                        step_name = step_data['step']
                        step_paths = step_data['paths']
                        verification = step_data.get('verification_result')

                        md += f"**{step_name}**:\n\n"

                        # Show all camera angles in a table
                        md += "| View | Render |\n"
                        md += "|------|--------|\n"

                        for angle in camera_angles:
                            angle_key = f"{angle}"
                            if angle_key in step_paths:
                                angle_path = Path(step_paths[angle_key]).name
                                md += f"| **{angle.capitalize()}** | ![{step_name} {angle}]({renders_path_prefix}/{angle_path}) |\n"

                        md += "\n"

                        # Show verification result if available
                        if verification:
                            conf = verification.get('confidence', 0.0)
                            conf_str = f"{conf:.2f}" if conf is not None else "N/A"

                            if verification.get('verification_passed'):
                                md += f"✓ Verification passed (confidence: {conf_str})\n\n"
                            else:
                                md += f"✗ Verification failed (confidence: {conf_str})\n"
                                issues = verification.get('issues_found', [])
                                if issues:
                                    md += "Issues:\n"
                                    for issue in issues:
                                        md += f"  - {issue}\n"
                                md += "\n"

                md += "---\n\n"

        md += f"""
## Failed Cases

"""
        failed_cases = [r for r in results['test_case_results']
                        if not r.get('success')]
        if failed_cases:
            for r in failed_cases:
                md += f"- **{r['test_case_id']}**: {r.get('error', 'Unknown error')}\n"
        else:
            md += "No failed cases! 🎉\n"

        md += """
---
*Generated by CoScene Evaluation Framework*
"""

        return md


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


async def main():
    """Main entry point for evaluation."""
    parser = argparse.ArgumentParser(
        description='Run evaluation on CoScene agent pipeline'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        required=True,
        help='Path to test dataset JSON file'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='evaluation/config.yaml',
        help='Path to configuration YAML file'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output path for results (default: auto-generated)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of test cases to evaluate'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--blender-path',
        type=str,
        help='Path to Blender executable (e.g., /Applications/Blender.app/Contents/MacOS/Blender)'
    )

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize render service with custom Blender path if provided
    if args.blender_path:
        from services.render_service import RenderService
        import services.render_service as render_service_module
        render_service_module._render_service_instance = RenderService(
            blender_executable=args.blender_path
        )
        logger.info(f"Using custom Blender path: {args.blender_path}")

    # Load configuration
    config = load_config(args.config)

    # Generate output path first
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = Path(args.dataset).stem
        output_dir = Path(config.get('evaluation', {}).get(
            'output_dir', 'evaluation/results'))
        output_path = output_dir / f"{dataset_name}_{timestamp}"

    # Create renders directory
    renders_dir = output_path.parent / (output_path.stem + "_renders")

    # Initialize runner with renders directory
    runner = EvaluationRunner(config, renders_dir=renders_dir)

    # Run evaluation
    logger.info("="*60)
    logger.info("Starting CoScene Agent Evaluation")
    logger.info("="*60)

    results = await runner.evaluate_dataset(
        dataset_path=args.dataset,
        limit=args.limit
    )

    # Generate report
    logger.info("="*60)
    logger.info("Generating Report")
    logger.info("="*60)
    runner.generate_report(results, output_path)

    # Print summary
    aggregate = results['aggregate_metrics']
    logger.info("")
    logger.info("="*60)
    logger.info("EVALUATION COMPLETE")
    logger.info("="*60)
    logger.info(
        f"Success Rate: {aggregate['success_rate']:.1%} ({aggregate['successful_cases']}/{aggregate['total_cases']})")
    logger.info(
        f"Structural Similarity: {aggregate['structural_similarity']['mean']:.3f}")
    logger.info(
        f"Semantic Correctness: {aggregate['semantic_correctness']['accuracy']:.1%}")

    # Show visual metrics if available
    if 'visual_similarity' in aggregate:
        vs = aggregate['visual_similarity']
        logger.info(
            f"Visual Similarity (SSIM): {vs['ssim_mean']:.3f} | PSNR: {vs['psnr_mean']:.1f}dB")

    logger.info(f"Mean Latency: {aggregate['latency']['mean']:.2f}s")
    logger.info(f"Report saved to: {output_path}")
    if renders_dir.exists() and any(renders_dir.iterdir()):
        logger.info(f"Rendered frames saved to: {renders_dir}")
    logger.info("="*60)


if __name__ == '__main__':
    asyncio.run(main())
