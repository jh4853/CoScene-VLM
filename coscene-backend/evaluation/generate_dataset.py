"""
Dataset generation script for CoScene evaluation framework.

Usage:
    python -m evaluation.generate_dataset --complexity simple --num-cases 50
    python -m evaluation.generate_dataset --config evaluation/config.yaml
"""
import argparse
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from evaluation.generators.usd_generator import USDGenerator
from evaluation.generators.prompt_generator import PromptGenerator


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatasetGenerator:
    """Main dataset generation coordinator."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize dataset generator.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.seed = config.get('dataset', {}).get('seed', 42)
        self.usd_generator = USDGenerator(seed=self.seed)
        self.prompt_generator = PromptGenerator(seed=self.seed)

    def generate_test_case(self, complexity: str) -> Dict[str, Any]:
        """
        Generate a single test case.

        Args:
            complexity: 'simple', 'medium', or 'complex'

        Returns:
            Test case dictionary
        """
        # Generate USD scene pair
        if complexity == 'simple':
            scene_pair = self.usd_generator.generate_simple_edit()
        elif complexity == 'medium':
            scene_pair = self.usd_generator.generate_medium_edit()
        elif complexity == 'complex':
            scene_pair = self.usd_generator.generate_complex_edit()
        else:
            logger.warning(f"Unknown complexity '{complexity}', using 'simple'")
            scene_pair = self.usd_generator.generate_simple_edit()

        # Generate prompts
        num_variations = self.config.get('dataset', {}).get('prompt_variations', 3)
        prompt_variations = self.prompt_generator.generate_prompt_variations(
            operation_type=scene_pair.edit_operation.operation_type,
            parameters=scene_pair.edit_operation.parameters,
            num_variations=num_variations
        )

        # Main prompt is the first variation
        main_prompt = prompt_variations[0]

        # Build test case
        test_case = {
            'id': scene_pair.test_case_id,
            'complexity': scene_pair.complexity,
            'initial_usd': scene_pair.initial_usd,
            'target_usd': scene_pair.target_usd,
            'edit_operation': {
                'type': scene_pair.edit_operation.operation_type,
                'parameters': {
                    k: (list(v) if isinstance(v, tuple) else v)
                    for k, v in scene_pair.edit_operation.parameters.items()
                },
                'description': scene_pair.edit_operation.description,
            },
            'prompt': main_prompt,
            'prompt_variations': prompt_variations,
            'expected_metrics': scene_pair.expected_metrics,
            'ground_truth_render_path': None,  # To be filled after rendering
        }

        return test_case

    def generate_dataset(self, complexity: str, num_cases: int) -> Dict[str, Any]:
        """
        Generate a complete dataset.

        Args:
            complexity: 'simple', 'medium', or 'complex'
            num_cases: Number of test cases to generate

        Returns:
            Dataset dictionary with metadata and test cases
        """
        logger.info(f"Generating {num_cases} {complexity} test cases...")

        test_cases = []
        for i in range(num_cases):
            if (i + 1) % 10 == 0:
                logger.info(f"  Generated {i + 1}/{num_cases} test cases")

            test_case = self.generate_test_case(complexity)
            test_cases.append(test_case)

        dataset = {
            'metadata': {
                'version': '1.0',
                'complexity': complexity,
                'num_test_cases': len(test_cases),
                'generated_date': datetime.now().isoformat(),
                'seed': self.seed,
                'config': {
                    'prompt_variations': self.config.get('dataset', {}).get('prompt_variations', 3),
                }
            },
            'test_cases': test_cases
        }

        logger.info(f"✓ Generated {len(test_cases)} test cases")
        return dataset

    def save_dataset(self, dataset: Dict[str, Any], output_path: Path):
        """
        Save dataset to JSON file.

        Args:
            dataset: Dataset dictionary
            output_path: Path to save JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(dataset, f, indent=2)

        logger.info(f"✓ Saved dataset to {output_path}")

    def save_individual_usd_files(self, dataset: Dict[str, Any], output_dir: Path):
        """
        Save individual USD files for each test case.

        Args:
            dataset: Dataset dictionary
            output_dir: Directory to save USD files
        """
        usd_dir = output_dir / 'usd_files'
        usd_dir.mkdir(parents=True, exist_ok=True)

        for test_case in dataset['test_cases']:
            test_id = test_case['id']

            # Save initial USD
            initial_path = usd_dir / f"{test_id}_initial.usd"
            with open(initial_path, 'w') as f:
                f.write(test_case['initial_usd'])

            # Save target USD
            target_path = usd_dir / f"{test_id}_target.usd"
            with open(target_path, 'w') as f:
                f.write(test_case['target_usd'])

        logger.info(f"✓ Saved USD files to {usd_dir}")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point for dataset generation."""
    parser = argparse.ArgumentParser(
        description='Generate evaluation datasets for CoScene agent pipeline'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='evaluation/config.yaml',
        help='Path to configuration YAML file'
    )
    parser.add_argument(
        '--complexity',
        type=str,
        choices=['simple', 'medium', 'complex', 'all'],
        help='Complexity level to generate (overrides config)'
    )
    parser.add_argument(
        '--num-cases',
        type=int,
        help='Number of test cases to generate (overrides config)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory (overrides config)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility (overrides config)'
    )
    parser.add_argument(
        '--save-usd-files',
        action='store_true',
        help='Save individual USD files in addition to JSON dataset'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Override with command-line arguments
    if args.seed is not None:
        config.setdefault('dataset', {})['seed'] = args.seed

    if args.output_dir:
        config.setdefault('dataset', {})['output_dir'] = args.output_dir

    # Initialize generator
    generator = DatasetGenerator(config)

    # Determine complexities to generate
    if args.complexity == 'all':
        complexities = config.get('dataset', {}).get('complexities', ['simple'])
    elif args.complexity:
        complexities = [args.complexity]
    else:
        complexities = config.get('dataset', {}).get('complexities', ['simple'])

    # Output directory
    output_dir = Path(config.get('dataset', {}).get('output_dir', 'evaluation/datasets'))

    # Generate datasets
    for complexity in complexities:
        logger.info(f"\n{'='*60}")
        logger.info(f"Generating {complexity.upper()} dataset")
        logger.info(f"{'='*60}")

        # Determine number of cases
        if args.num_cases:
            num_cases = args.num_cases
        else:
            num_cases = config.get('dataset', {}).get('num_cases', {}).get(complexity, 50)

        # Generate dataset
        dataset = generator.generate_dataset(complexity, num_cases)

        # Save dataset
        dataset_output_dir = output_dir / complexity
        dataset_path = dataset_output_dir / f'test_dataset.json'
        generator.save_dataset(dataset, dataset_path)

        # Optionally save individual USD files
        if args.save_usd_files:
            generator.save_individual_usd_files(dataset, dataset_output_dir)

        # Print summary
        logger.info(f"\n✓ Dataset Summary:")
        logger.info(f"  Complexity: {complexity}")
        logger.info(f"  Test Cases: {dataset['metadata']['num_test_cases']}")
        logger.info(f"  Output: {dataset_path}")

        # Print example test cases
        logger.info(f"\n  Example Test Cases:")
        for i, tc in enumerate(dataset['test_cases'][:3], 1):
            logger.info(f"    {i}. {tc['id']}: {tc['prompt']}")

    logger.info(f"\n{'='*60}")
    logger.info("✓ Dataset generation complete!")
    logger.info(f"{'='*60}\n")


if __name__ == '__main__':
    main()
