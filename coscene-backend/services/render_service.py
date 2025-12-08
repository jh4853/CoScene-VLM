"""
Render service for invoking Blender headless rendering.
Manages USD file I/O and async subprocess execution.
"""
import asyncio
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class RenderService:
    """Service for rendering USD scenes with Blender."""

    def __init__(
        self,
        blender_executable: str = "blender",
        script_path: Optional[str] = None,
        temp_dir: Optional[str] = None
    ):
        """
        Initialize render service.

        Args:
            blender_executable: Path to Blender executable
            script_path: Path to blender_render.py script
            temp_dir: Directory for temporary files
        """
        self.blender_executable = blender_executable

        # Default script path
        if script_path is None:
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "scripts",
                "blender_render.py"
            )
        self.script_path = script_path

        # Temp directory for USD files and renders
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        self.temp_dir = Path(temp_dir) / "coscene_renders"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"RenderService initialized with Blender: {self.blender_executable}")
        logger.info(f"Script path: {self.script_path}")
        logger.info(f"Temp directory: {self.temp_dir}")

    async def check_blender_available(self) -> bool:
        """
        Check if Blender is available and executable.
        Returns True if Blender can be executed.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                self.blender_executable,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                version_info = stdout.decode().split('\n')[0]
                logger.info(f"Blender available: {version_info}")
                return True
            else:
                logger.error(f"Blender check failed: {stderr.decode()}")
                return False

        except FileNotFoundError:
            logger.error(f"Blender not found at: {self.blender_executable}")
            return False
        except Exception as e:
            logger.error(f"Error checking Blender: {e}")
            return False

    async def render_usd(
        self,
        usd_content: str,
        quality: str = "preview",
        camera_angle: str = "perspective"
    ) -> Tuple[bytes, int]:
        """
        Render USD scene to PNG image.

        Args:
            usd_content: USD scene content as string
            quality: Render quality (preview, verification, final)
            camera_angle: Camera angle (perspective, front, top, side)

        Returns:
            Tuple of (image_bytes, render_time_ms)

        Raises:
            RuntimeError: If rendering fails
        """
        # Generate unique IDs for files
        file_id = uuid4().hex
        usd_file = self.temp_dir / f"scene_{file_id}.usda"
        output_file = self.temp_dir / f"render_{file_id}.png"

        try:
            # Write USD content to file
            logger.info(f"Writing USD to {usd_file}")
            with open(usd_file, 'w') as f:
                f.write(usd_content)

            # Build Blender command
            cmd = [
                self.blender_executable,
                "-b",  # Background mode (headless)
                "--python", self.script_path,
                "--",  # Separator for script arguments
                str(usd_file),
                str(output_file),
                quality,
                camera_angle
            ]

            logger.info(f"Executing Blender render: {' '.join(cmd)}")

            # Execute Blender
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120.0  # 2 minute timeout
            )

            # Decode output for logging
            output_text = stdout.decode() if stdout else ""
            error_text = stderr.decode() if stderr else ""

            # Always log Blender output for debugging
            if output_text:
                logger.info(f"Blender stdout:\n{output_text}")
            if error_text:
                logger.warning(f"Blender stderr:\n{error_text}")

            # Check if rendering succeeded
            if process.returncode != 0:
                error_msg = error_text if error_text else output_text
                logger.error(f"Blender render failed with code {process.returncode}: {error_msg}")
                raise RuntimeError(f"Blender rendering failed: {error_msg}")

            # Parse render time from stdout
            render_time_ms = -1
            for line in output_text.split('\n'):
                if "Render complete in" in line:
                    try:
                        # Extract "123ms" from "Render complete in 123ms"
                        render_time_ms = int(line.split("in ")[1].split("ms")[0])
                    except:
                        pass

            logger.info(f"Render completed in {render_time_ms}ms")

            # Read rendered image
            if not output_file.exists():
                error_details = f"Render output file was not created at: {output_file}"
                if "ERROR" in output_text or "Error" in output_text:
                    error_details += f"\n\nBlender errors found:\n{output_text}"
                raise RuntimeError(error_details)

            with open(output_file, 'rb') as f:
                image_bytes = f.read()

            logger.info(f"Read {len(image_bytes)} bytes from render output")

            return image_bytes, render_time_ms

        except asyncio.TimeoutError:
            logger.error("Blender render timed out")
            raise RuntimeError("Rendering timed out after 120 seconds")

        except Exception as e:
            logger.error(f"Rendering error: {e}")
            raise

        finally:
            # Cleanup temporary files
            try:
                if usd_file.exists():
                    usd_file.unlink()
                if output_file.exists():
                    output_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")

    async def render_multiview(
        self,
        usd_content: str,
        quality: str = "preview",
        angles: list[str] = None
    ) -> dict[str, Tuple[bytes, int]]:
        """
        Render scene from multiple camera angles.

        Args:
            usd_content: USD scene content
            quality: Render quality
            angles: List of camera angles to render. Defaults to all 4 views.

        Returns:
            Dict mapping camera_angle -> (image_bytes, render_time_ms)
        """
        if angles is None:
            angles = ["perspective", "front", "top", "side"]

        logger.info(f"Rendering {len(angles)} views: {', '.join(angles)}")

        # Render all views concurrently for better performance
        tasks = []
        for angle in angles:
            task = self.render_usd(
                usd_content,
                quality=quality,
                camera_angle=angle
            )
            tasks.append((angle, task))

        # Await all renders
        results = {}
        for angle, task in tasks:
            try:
                image_bytes, render_time = await task
                results[angle] = (image_bytes, render_time)
                logger.info(f"View '{angle}' rendered in {render_time}ms")
            except Exception as e:
                logger.error(f"Failed to render view '{angle}': {e}")
                # Continue with other views even if one fails

        return results


# Singleton instance
_render_service_instance = None


def get_render_service() -> RenderService:
    """Get singleton render service instance."""
    global _render_service_instance
    if _render_service_instance is None:
        _render_service_instance = RenderService()
    return _render_service_instance


# For testing
if __name__ == "__main__":
    import argparse
    import time

    logging.basicConfig(level=logging.INFO)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Test render service with custom Blender path")
    parser.add_argument("--input-usd", type=str, required=True,
                        help="Path to input USD file to render")
    parser.add_argument("--output-png", type=str, default=None,
                        help="Output path for rendered frame (default: output_<timestamp>.png)")
    parser.add_argument("--blender-path", type=str, default="blender",
                        help="Path to Blender executable (default: blender)")
    parser.add_argument("--quality", type=str, default="preview",
                        choices=["preview", "verification", "final"],
                        help="Render quality (default: preview)")
    parser.add_argument("--camera-angle", type=str, default="perspective",
                        help="Camera angle for rendering (default: perspective)")
    args = parser.parse_args()

    # Set default output path if not provided
    if args.output_png is None:
        timestamp = str(int(time.time()))
        args.output_png = f"output_{timestamp}.png"

    async def test():
        # Read input USD file
        try:
            with open(args.input_usd, 'r') as f:
                usd_content = f.read()
            print(f"Loaded USD from: {args.input_usd}")
        except FileNotFoundError:
            print(f"Error: Input USD file not found: {args.input_usd}")
            return
        except Exception as e:
            print(f"Error reading USD file: {e}")
            return

        # Initialize render service with custom Blender path
        render_service = RenderService(blender_executable=args.blender_path)

        # Check if Blender is available
        if not await render_service.check_blender_available():
            print("Error: Blender is not available. Please check the path.")
            return

        # Render the USD file
        print(f"Rendering with quality: {args.quality}, camera: {args.camera_angle}")
        try:
            image_bytes, render_time_ms = await render_service.render_usd(
                usd_content=usd_content,
                quality=args.quality,
                camera_angle=args.camera_angle
            )

            # Save rendered image
            with open(args.output_png, 'wb') as f:
                f.write(image_bytes)

            print(f"✓ Render complete in {render_time_ms}ms")
            print(f"✓ Output saved to: {args.output_png}")
            print(f"✓ Image size: {len(image_bytes)} bytes")

        except Exception as e:
            print(f"Error during rendering: {e}")
            return

    asyncio.run(test())
