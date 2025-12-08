"""
Visual metrics for comparing rendered images.
Uses SSIM, MSE, and PSNR to measure visual similarity.
"""
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import image processing libraries
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - visual metrics will be limited")

try:
    from skimage import metrics as skmetrics
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False
    logger.warning("scikit-image not available - using basic metrics only")


class VisualMetrics:
    """Compute visual similarity metrics between rendered images."""

    def __init__(self):
        """Initialize visual metrics calculator."""
        if not PIL_AVAILABLE:
            logger.warning("PIL not installed. Install with: pip install Pillow")
        if not SKIMAGE_AVAILABLE:
            logger.warning("scikit-image not installed. Install with: pip install scikit-image")

    def load_image_from_bytes(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Load image from bytes and convert to numpy array.

        Args:
            image_bytes: Image data as bytes

        Returns:
            Numpy array (H, W, C) or None if failed
        """
        if not PIL_AVAILABLE:
            logger.error("PIL not available - cannot load images")
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return np.array(image)
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None

    def load_image_from_path(self, image_path: str) -> Optional[np.ndarray]:
        """
        Load image from file path.

        Args:
            image_path: Path to image file

        Returns:
            Numpy array (H, W, C) or None if failed
        """
        if not PIL_AVAILABLE:
            logger.error("PIL not available - cannot load images")
            return None

        try:
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return np.array(image)
        except Exception as e:
            logger.error(f"Failed to load image from {image_path}: {e}")
            return None

    def compute_mse(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute Mean Squared Error between two images.

        Args:
            img1: First image as numpy array
            img2: Second image as numpy array

        Returns:
            MSE value (lower is better)
        """
        if img1.shape != img2.shape:
            logger.error(f"Image shape mismatch: {img1.shape} vs {img2.shape}")
            return float('inf')

        # Normalize to [0, 1] if needed
        if img1.dtype == np.uint8:
            img1 = img1.astype(np.float32) / 255.0
        if img2.dtype == np.uint8:
            img2 = img2.astype(np.float32) / 255.0

        mse = np.mean((img1 - img2) ** 2)
        return float(mse)

    def compute_psnr(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute Peak Signal-to-Noise Ratio.

        Args:
            img1: First image as numpy array
            img2: Second image as numpy array

        Returns:
            PSNR value in dB (higher is better)
        """
        mse = self.compute_mse(img1, img2)

        if mse == 0:
            return float('inf')  # Perfect match

        # PSNR = 20 * log10(MAX_I / sqrt(MSE))
        # For normalized images, MAX_I = 1.0
        psnr = 20 * np.log10(1.0 / np.sqrt(mse))
        return float(psnr)

    def compute_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """
        Compute Structural Similarity Index (SSIM).

        Args:
            img1: First image as numpy array
            img2: Second image as numpy array

        Returns:
            SSIM value in [0, 1] (higher is better)
        """
        if not SKIMAGE_AVAILABLE:
            logger.warning("scikit-image not available - cannot compute SSIM")
            return 0.0

        if img1.shape != img2.shape:
            logger.error(f"Image shape mismatch: {img1.shape} vs {img2.shape}")
            return 0.0

        # Normalize to [0, 1] if needed
        if img1.dtype == np.uint8:
            img1 = img1.astype(np.float32) / 255.0
        if img2.dtype == np.uint8:
            img2 = img2.astype(np.float32) / 255.0

        try:
            # SSIM for multichannel (RGB) images
            ssim = skmetrics.structural_similarity(
                img1, img2,
                win_size=7,
                channel_axis=2,  # RGB channels
                data_range=1.0
            )
            return float(ssim)
        except Exception as e:
            logger.error(f"Failed to compute SSIM: {e}")
            return 0.0

    def compute_all_metrics(
        self,
        ground_truth_image: np.ndarray,
        generated_image: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compute all visual metrics.

        Args:
            ground_truth_image: Ground truth image as numpy array
            generated_image: Generated image as numpy array

        Returns:
            Dict with all visual metrics
        """
        if ground_truth_image is None or generated_image is None:
            return {
                'error': 'One or both images are None',
                'mse': None,
                'psnr': None,
                'ssim': None,
            }

        # Check shapes
        if ground_truth_image.shape != generated_image.shape:
            logger.error(f"Image shape mismatch: {ground_truth_image.shape} vs {generated_image.shape}")
            return {
                'error': 'Image shape mismatch',
                'ground_truth_shape': ground_truth_image.shape,
                'generated_shape': generated_image.shape,
                'mse': None,
                'psnr': None,
                'ssim': None,
            }

        # Compute metrics
        mse = self.compute_mse(ground_truth_image, generated_image)
        psnr = self.compute_psnr(ground_truth_image, generated_image)
        ssim = self.compute_ssim(ground_truth_image, generated_image)

        return {
            'mse': mse,
            'psnr': psnr,
            'ssim': ssim,
            'image_shape': ground_truth_image.shape,
            'summary': {
                'high_quality': ssim > 0.8 and psnr > 20,
                'acceptable_quality': ssim > 0.6 and psnr > 15,
                'visual_similarity_score': ssim,  # Use SSIM as main score
            }
        }

    def compute_metrics_from_bytes(
        self,
        ground_truth_bytes: bytes,
        generated_bytes: bytes
    ) -> Dict[str, Any]:
        """
        Compute visual metrics from image bytes.

        Args:
            ground_truth_bytes: Ground truth image as bytes
            generated_bytes: Generated image as bytes

        Returns:
            Dict with all visual metrics
        """
        gt_image = self.load_image_from_bytes(ground_truth_bytes)
        gen_image = self.load_image_from_bytes(generated_bytes)

        return self.compute_all_metrics(gt_image, gen_image)

    def compute_metrics_from_paths(
        self,
        ground_truth_path: str,
        generated_path: str
    ) -> Dict[str, Any]:
        """
        Compute visual metrics from image file paths.

        Args:
            ground_truth_path: Path to ground truth image
            generated_path: Path to generated image

        Returns:
            Dict with all visual metrics
        """
        gt_image = self.load_image_from_path(ground_truth_path)
        gen_image = self.load_image_from_path(generated_path)

        return self.compute_all_metrics(gt_image, gen_image)


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Testing Visual Metrics...")
    print(f"PIL available: {PIL_AVAILABLE}")
    print(f"scikit-image available: {SKIMAGE_AVAILABLE}")

    if PIL_AVAILABLE and SKIMAGE_AVAILABLE:
        # Create test images
        print("\nCreating test images...")

        # Image 1: Red square
        img1 = np.zeros((100, 100, 3), dtype=np.uint8)
        img1[:, :, 0] = 255  # Red channel

        # Image 2: Identical
        img2 = img1.copy()

        # Image 3: Slightly different
        img3 = img1.copy()
        img3[40:60, 40:60, 0] = 200  # Darker red in center

        # Image 4: Very different
        img4 = np.zeros((100, 100, 3), dtype=np.uint8)
        img4[:, :, 2] = 255  # Blue channel

        metrics_calc = VisualMetrics()

        # Test identical images
        print("\n=== Identical Images ===")
        result = metrics_calc.compute_all_metrics(img1, img2)
        print(f"MSE: {result['mse']:.6f}")
        print(f"PSNR: {result['psnr']:.2f} dB")
        print(f"SSIM: {result['ssim']:.4f}")

        # Test similar images
        print("\n=== Similar Images ===")
        result = metrics_calc.compute_all_metrics(img1, img3)
        print(f"MSE: {result['mse']:.6f}")
        print(f"PSNR: {result['psnr']:.2f} dB")
        print(f"SSIM: {result['ssim']:.4f}")

        # Test different images
        print("\n=== Different Images ===")
        result = metrics_calc.compute_all_metrics(img1, img4)
        print(f"MSE: {result['mse']:.6f}")
        print(f"PSNR: {result['psnr']:.2f} dB")
        print(f"SSIM: {result['ssim']:.4f}")
    else:
        print("\nSkipping tests - required libraries not available")
        print("Install with: pip install Pillow scikit-image")
