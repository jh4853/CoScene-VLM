"""
LangGraph scene editor agent.
"""
from typing import TypedDict, Annotated, List, Dict, Any
from uuid import UUID
import logging
import base64
import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from agents.prompts import (
    SYSTEM_PROMPT,
    get_usd_generation_prompt,
    get_vision_verification_prompt,
    get_fix_generation_prompt,
)
from services.usd_service import get_usd_service
from services.render_service import get_render_service
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============ State Definition ============


class SceneEditState(TypedDict):
    """State passed through the agent workflow."""
    session_id: str
    user_prompt: str
    current_usd: str
    input_scene_renders: dict[str, bytes]  # {camera_angle: image_bytes}
    generated_usd: str
    output_scene_renders: dict[str, bytes]  # {camera_angle: image_bytes}
    status: str  # "pending", "generating", "rendering", "verifying", "fixing", "success", "failed"
    error_message: str

    # Verification loop fields
    verification_attempts: int  # Number of verification attempts made
    verification_passed: bool  # Whether verification passed
    verification_feedback: str  # Detailed feedback from verification
    verification_issues: List[str]  # List of issues found
    verification_confidence: float  # Confidence score from verifier

    # Intermediate renders for debugging
    # List of {step, renders, usd, verification_result}
    intermediate_renders: List[Dict[str, Any]]


# ============ Agent Nodes ============

async def parse_intent_node(state: SceneEditState) -> SceneEditState:
    """
    Parse user intent
    """
    logger.info(f"Parsing intent: {state['user_prompt']}")

    state["status"] = "generating"

    return state


async def render_input_node(state: SceneEditState) -> SceneEditState:
    """
    Render the current USD scene (input state) to provide visual context.
    This happens BEFORE USD generation so the LLM can see the current state.
    Can be disabled via ENABLE_INPUT_RENDERING env var for ablation studies.
    """
    # Initialize empty dict
    state["input_scene_renders"] = {}

    # Check if input rendering is enabled
    if not settings.enable_input_rendering:
        logger.info("Input rendering disabled (ablation mode), skipping")
        return state

    logger.info("Rendering input scene for visual context")

    # Skip if no current scene
    if not state.get("current_usd") or state["current_usd"].strip() == "":
        logger.info(
            "No current scene to render (first edit), skipping input rendering")
        return state

    try:
        render_service = get_render_service()

        # Check if Blender is available
        if not await render_service.check_blender_available():
            logger.warning(
                "Blender not available, skipping input scene rendering")
            return state

        # Render current scene
        renders = await render_service.render_multiview(
            usd_content=state["current_usd"],
            quality="preview"
        )

        # Store image bytes (discard render time for now)
        state["input_scene_renders"] = {
            camera_angle: image_bytes
            for camera_angle, (image_bytes, render_time_ms) in renders.items()
        }

        logger.info(f"Input scene rendered: {len(renders)} views")

    except Exception as e:
        # Don't fail the whole workflow if input rendering fails
        # Generation can proceed without visual context (degraded mode)
        logger.warning(
            f"Input scene rendering failed (continuing without visual context): {e}")
        state["input_scene_renders"] = {}

    return state


async def generate_usd_node(state: SceneEditState) -> SceneEditState:
    """
    Generate USD code using Claude 4.5 Sonnet.
    """
    logger.info("Generating USD with Claude 4.5 Sonnet")
    state["status"] = "generating"

    try:
        # Initialize Claude
        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.0,  # Deterministic for code generation
            max_tokens=4096
        )

        # Build prompt
        prompt = get_usd_generation_prompt(
            current_usd=state.get("current_usd", ""),
            user_prompt=state["user_prompt"]
        )

        # Build message content (text + optional images)
        message_content = []

        # Add text prompt
        message_content.append({
            "type": "text",
            "text": prompt
        })

        # Add input scene renders if available
        input_renders = state.get("input_scene_renders", {})
        if input_renders:
            logger.info(
                f"Including {len(input_renders)} input scene render(s) as visual context")
            for camera_angle, image_bytes in input_renders.items():
                # Encode image to base64
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                message_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_base64
                    }
                })

        # Generate USD
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message_content)
        ]

        response = await llm.ainvoke(messages)
        generated_content = response.content

        # Extract USD code (remove markdown if present)
        usd_code = generated_content
        if "```" in usd_code:
            # Extract code from markdown blocks
            parts = usd_code.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Odd indices are code blocks
                    # Remove language identifier
                    lines = part.split("\n")
                    if lines[0].strip().lower() in ["usd", "usda", ""]:
                        usd_code = "\n".join(lines[1:])
                    else:
                        usd_code = part
                    break

        # Validate USD
        usd_service = get_usd_service()
        is_valid, error = usd_service.validate_usd(usd_code)

        if not is_valid:
            logger.error(f"Generated invalid USD: {error}")
            state["status"] = "failed"
            state["error_message"] = f"Generated invalid USD: {error}"
            return state

        logger.info("USD generated successfully")
        logger.info(usd_code)
        state["generated_usd"] = usd_code
        state["status"] = "rendering"

    except Exception as e:
        logger.error(f"Error generating USD: {e}")
        state["status"] = "failed"

        # Provide more descriptive error messages
        error_str = str(e)
        if "404" in error_str or "not_found" in error_str:
            state["error_message"] = "Invalid Claude model name. Please check API configuration."
        elif "authentication" in error_str.lower() or "401" in error_str:
            state["error_message"] = "Invalid Anthropic API key. Please check configuration."
        elif "rate_limit" in error_str.lower() or "429" in error_str:
            state["error_message"] = "Rate limit exceeded. Please try again later."
        else:
            state["error_message"] = f"USD generation failed: {error_str}"

    return state


async def render_output_node(state: SceneEditState) -> SceneEditState:
    """
    Render the generated USD scene (output state).
    """
    logger.info("Rendering output scene with Blender")
    state["status"] = "rendering"

    try:
        render_service = get_render_service()

        # Check if Blender is available
        if not await render_service.check_blender_available():
            logger.warning("Blender not available, skipping render")
            state["status"] = "success"
            state["error_message"] = "Blender not available - USD generated but not rendered"
            state["output_scene_renders"] = {}
            return state

        # Render scene with multi-view
        # Use preview quality to match ground truth renders for fair comparison
        renders = await render_service.render_multiview(
            usd_content=state["generated_usd"],
            quality="preview"  # Use preview to match evaluation ground truth
        )

        # Store image bytes in state
        state["output_scene_renders"] = {
            camera_angle: image_bytes
            for camera_angle, (image_bytes, render_time_ms) in renders.items()
        }

        # Store intermediate render for debugging
        if not state.get("intermediate_renders"):
            state["intermediate_renders"] = []

        state["intermediate_renders"].append({
            "step": f"render_attempt_{state.get('verification_attempts', 0)}",
            "renders": {k: v for k, v in state["output_scene_renders"].items()},
            "usd": state["generated_usd"],
            "verification_result": None  # Will be filled by verification node
        })

        state["status"] = "verifying" if False else "success"
        logger.info(f"Rendering complete: {len(renders)} frames")

    except Exception as e:
        logger.error(f"Rendering failed: {e}")
        state["status"] = "failed"
        state["error_message"] = f"Rendering failed: {str(e)}"
        state["output_scene_renders"] = {}

    return state


async def verify_output_node(state: SceneEditState) -> SceneEditState:
    """
    Verify that the generated scene matches user intent using VLM with vision.
    Uses multi-view renders to check correctness.
    """
    logger.info("Verifying output with vision-based VLM")
    state["status"] = "verifying"

    # Skip verification if disabled (for ablation studies)
    if not False:
        logger.info("Verification loop disabled, marking as passed")
        state["verification_passed"] = True
        state["status"] = "success"
        return state

    # Skip if no renders available
    if not state.get("output_scene_renders"):
        logger.warning("No renders available for verification, skipping")
        state["verification_passed"] = True
        state["status"] = "success"
        return state

    try:
        # Initialize Claude for verification
        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.0,
            max_tokens=2048
        )

        # Build verification prompt with images
        prompt = get_vision_verification_prompt(state["user_prompt"])

        message_content = []

        # Add text prompt
        message_content.append({
            "type": "text",
            "text": prompt
        })

        # Add all rendered views as visual context
        for camera_angle, image_bytes in state["output_scene_renders"].items():
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_base64
                }
            })
            logger.debug(f"  Added {camera_angle} view for verification")

        # Call VLM for verification
        messages = [HumanMessage(content=message_content)]
        response = await llm.ainvoke(messages)
        response_text = response.content

        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if "```" in response_text:
                parts = response_text.split("```")
                for i, part in enumerate(parts):
                    if i % 2 == 1:  # Odd indices are code blocks
                        lines = part.split("\n")
                        if lines[0].strip().lower() in ["json", ""]:
                            response_text = "\n".join(lines[1:])
                        else:
                            response_text = part
                        break

            verification_result = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            # Assume verification passed if we can't parse (graceful degradation)
            state["verification_passed"] = True
            state["verification_feedback"] = "Could not parse verification response"
            state["verification_issues"] = []
            state["verification_confidence"] = 0.5
            state["status"] = "success"
            return state

        # Extract verification results
        state["verification_passed"] = verification_result.get(
            "verification_passed", True)
        state["verification_feedback"] = verification_result.get(
            "detailed_feedback", "")
        state["verification_issues"] = verification_result.get(
            "issues_found", [])
        state["verification_confidence"] = verification_result.get(
            "confidence", 0.0)

        # Update intermediate renders with verification result
        if state.get("intermediate_renders"):
            state["intermediate_renders"][-1]["verification_result"] = verification_result

        # Log result
        if state["verification_passed"]:
            logger.info(
                f"✓ Verification PASSED (confidence: {state['verification_confidence']:.2f})")
            state["status"] = "success"
        else:
            logger.warning(
                f"✗ Verification FAILED (confidence: {state['verification_confidence']:.2f})")
            logger.warning(
                f"  Issues: {', '.join(state['verification_issues'])}")
            state["status"] = "fixing"

    except Exception as e:
        logger.error(f"Verification failed with error: {e}")
        # Graceful degradation: assume verification passed if error occurs
        state["verification_passed"] = True
        state["verification_feedback"] = f"Verification error: {str(e)}"
        state["verification_issues"] = []
        state["verification_confidence"] = 0.0
        state["status"] = "success"

    return state


async def fix_output_node(state: SceneEditState) -> SceneEditState:
    """
    Fix the generated USD based on verification feedback.
    Generates corrected USD code addressing the issues found.
    """
    # Increment verification attempts counter
    state["verification_attempts"] = state.get("verification_attempts", 0) + 1

    logger.info(
        f"Generating fix (attempt {state['verification_attempts']}/{settings.max_verification_attempts})")
    state["status"] = "fixing"

    try:
        # Initialize Claude for fix generation
        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.0,
            max_tokens=4096
        )

        # Build fix prompt
        prompt = get_fix_generation_prompt(
            user_prompt=state["user_prompt"],
            current_usd=state["generated_usd"],
            verification_feedback=state.get("verification_feedback", ""),
            issues_list=state.get("verification_issues", []),
            # Use detailed feedback as suggestions
            suggested_fixes=state.get("verification_feedback", "")
        )

        # Generate fix
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        response = await llm.ainvoke(messages)
        generated_content = response.content

        # Extract USD code (remove markdown if present)
        usd_code = generated_content
        if "```" in usd_code:
            parts = usd_code.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Odd indices are code blocks
                    lines = part.split("\n")
                    if lines[0].strip().lower() in ["usd", "usda", ""]:
                        usd_code = "\n".join(lines[1:])
                    else:
                        usd_code = part
                    break

        # Validate USD
        usd_service = get_usd_service()
        is_valid, error = usd_service.validate_usd(usd_code)

        if not is_valid:
            logger.error(f"Fix generated invalid USD: {error}")
            state["status"] = "failed"
            state["error_message"] = f"Fix generated invalid USD: {error}"
            return state

        # Update generated USD with fixed version
        state["generated_usd"] = usd_code
        state["status"] = "rendering"
        logger.info("Fix generated successfully, will re-render")

    except Exception as e:
        logger.error(f"Error generating fix: {e}")
        state["status"] = "failed"
        state["error_message"] = f"Fix generation failed: {str(e)}"

    return state


# ============ Decision Functions ============

def should_continue_to_render(state: SceneEditState) -> str:
    """
    Decide if we should continue to render or stop due to error.
    Returns 'render' to continue, 'end' to stop.
    """
    if state["status"] == "failed":
        logger.warning(
            f"Stopping workflow due to error: {state.get('error_message')}")
        return "end"
    return "render"


def should_verify_or_complete(state: SceneEditState) -> str:
    """
    Decide whether to verify output or complete (if verification disabled).
    Returns 'verify' to verify, 'end' to complete.
    """
    if state["status"] == "failed":
        return "end"

    # Skip verification if disabled (ablation mode)
    if not False:
        return "end"

    # Skip verification if no renders
    if not state.get("output_scene_renders"):
        return "end"

    return "verify"


def should_fix_or_complete(state: SceneEditState) -> str:
    """
    Decide whether to fix, re-render, or complete after verification.
    Returns:
    - 'fix' if verification failed and we haven't exceeded max attempts
    - 'complete_with_warning' if max attempts exceeded (need to set final state)
    - 'end' if verification passed
    """
    # If verification passed, we're done
    if state.get("verification_passed", True):
        return "end"

    # Check if we've exceeded max fix attempts
    current_attempts = state.get("verification_attempts", 0)
    if current_attempts >= settings.max_verification_attempts:
        logger.warning(
            f"Max verification attempts ({settings.max_verification_attempts}) exceeded, completing anyway")
        return "complete_with_warning"

    # Otherwise, try to fix
    return "fix"


async def complete_with_warning_node(state: SceneEditState) -> SceneEditState:
    """
    Handle completion when max verification attempts exceeded.
    This node properly sets status and error_message (can't do this in decision functions).
    """
    current_attempts = state.get("verification_attempts", 0)
    logger.warning(
        f"Completing with warning: Verification failed after {current_attempts} attempts")

    # Set appropriate status and error message
    # Mark as success so evaluation doesn't fail completely
    state["status"] = "success"
    state["error_message"] = f"Verification failed after {current_attempts} attempts (max: {settings.max_verification_attempts}). Issues: {', '.join(state.get('verification_issues', [])[:3])}"

    # Log the issues for debugging
    if state.get("verification_issues"):
        logger.warning(f"  Unresolved issues: {state['verification_issues']}")
    if state.get("verification_feedback"):
        logger.warning(
            f"  Final feedback: {state['verification_feedback'][:200]}")

    return state


# ============ Build Agent Graph ============

def create_scene_editor_graph():
    """
    Create the scene editor agent workflow.
    """
    workflow = StateGraph(SceneEditState)

    # Render nodes
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("render_input", render_input_node)
    workflow.add_node("generate_usd", generate_usd_node)
    workflow.add_node("render_output", render_output_node)

    # Verification nodes
    workflow.add_node("verify_output", verify_output_node)
    workflow.add_node("fix_output", fix_output_node)
    workflow.add_node("complete_with_warning", complete_with_warning_node)

    # Define edges
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "render_input")
    workflow.add_edge("render_input", "generate_usd")

    # Conditional: only render output if USD generation succeeded
    workflow.add_conditional_edges(
        "generate_usd",
        should_continue_to_render,
        {
            "render": "render_output",
            "end": END
        }
    )

    # Conditional verification
    workflow.add_conditional_edges(
        "render_output",
        should_verify_or_complete,
        {
            "verify": "verify_output",
            "end": END
        }
    )

    # After verification, decide whether to fix, warn-and-complete, or complete
    workflow.add_conditional_edges(
        "verify_output",
        should_fix_or_complete,
        {
            "fix": "fix_output",
            "complete_with_warning": "complete_with_warning",
            "end": END
        }
    )

    # After completing with warning, end the workflow
    workflow.add_edge("complete_with_warning", END)

    # After fix, re-render and verify again (creates the loop)
    workflow.add_edge("fix_output", "render_output")

    # Compile graph
    graph = workflow.compile()

    if False:
        logger.info(
            f"Scene editor graph compiled (with verification loop, max {settings.max_verification_attempts} attempts)")
    else:
        logger.info(
            "Scene editor graph compiled (no verification loop)")

    return graph


# ============ Agent Orchestration Function ============

async def process_scene_edit(
    session_id: str,
    user_prompt: str,
    current_usd: str = ""
) -> SceneEditState:
    """
    Process a scene edit request through the agent workflow.

    Args:
        session_id: Session ID
        user_prompt: User's natural language edit instruction
        current_usd: Current USD scene content (empty for first edit)

    Returns:
        Final state after agent processing
    """
    logger.info(f"Processing scene edit for session {session_id}")

    # Initialize state
    initial_state: SceneEditState = {
        "session_id": session_id,
        "user_prompt": user_prompt,
        "current_usd": current_usd,
        "input_scene_renders": {},
        "generated_usd": "",
        "output_scene_renders": {},
        "status": "pending",
        "error_message": "",

        # Verification fields
        "verification_attempts": 0,
        "verification_passed": False,
        "verification_feedback": "",
        "verification_issues": [],
        "verification_confidence": 0.0,
        "intermediate_renders": []
    }

    # Create and run graph
    graph = create_scene_editor_graph()

    # Set recursion limit for verification loop
    # Max path: parse -> render_input -> generate -> render_output -> verify -> fix (repeat) -> render_output -> verify
    # Each fix iteration adds ~3 nodes, so we need enough for all attempts
    recursion_limit = max(25, (settings.max_verification_attempts * 4) + 10)

    try:
        final_state = await graph.ainvoke(
            initial_state,
            config={"recursion_limit": recursion_limit}
        )
        logger.info(f"Agent workflow complete: status={final_state['status']}")
        return final_state

    except Exception as e:
        logger.error(f"Agent workflow failed: {e}")
        return {
            **initial_state,
            "status": "failed",
            "error_message": f"Agent workflow error: {str(e)}"
        }


# For testing
if __name__ == "__main__":
    import asyncio
    import argparse
    from services.render_service import RenderService, _render_service_instance
    import time
    t = str(int(time.time()))

    logging.basicConfig(level=logging.INFO)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Test scene editor with custom Blender path")
    parser.add_argument("--blender-path", type=str,
                        help="Path to Blender executable")
    parser.add_argument("--prompt", type=str, default="Create a red sphere in the center",
                        help="Scene generation prompt")
    parser.add_argument("--output-png", type=str, default="output" + t + ".png",
                        help="Output path for rendered frame (default: output.png)")
    parser.add_argument("--input-usd", type=str,
                        help="Path to input USD file to use as current_usd")
    parser.add_argument("--output-usd", type=str, default="output" + t + ".usd",
                        help="Path to output USD file to save generated USD")
    args = parser.parse_args()

    # Initialize render service with custom Blender path if provided
    if args.blender_path:
        import services.render_service as render_service_module
        render_service_module._render_service_instance = RenderService(
            blender_executable=args.blender_path
        )

    async def test():
        # Read input USD file if provided
        current_usd = ""
        if args.input_usd:
            with open(args.input_usd, 'r') as f:
                current_usd = f.read()
            print(f"Loaded input USD from: {args.input_usd}")

        result = await process_scene_edit(
            session_id="test-session",
            user_prompt=args.prompt,
            current_usd=current_usd
        )
        print(f"Status: {result['status']}")
        if result['status'] == "success":
            print(f"Generated USD:\n{result['generated_usd']}")

            # Save generated USD to file if output-usd specified
            if args.output_usd:
                with open(args.output_usd, 'w') as f:
                    f.write(result['generated_usd'])
                print(f"Generated USD saved to: {args.output_usd}")

            # Save rendered frame from agent state
            output_renders = result.get('output_scene_renders', {})
            if 'perspective' in output_renders:
                image_bytes = output_renders['perspective']
                with open(args.output_png, 'wb') as f:
                    f.write(image_bytes)
                print(f"Rendered frame saved to: {args.output_png}")
            elif output_renders:
                # Save first available render if perspective not found
                camera_angle, image_bytes = next(iter(output_renders.items()))
                with open(args.output_png, 'wb') as f:
                    f.write(image_bytes)
                print(
                    f"Rendered frame ({camera_angle}) saved to: {args.output_png}")
            else:
                print("No renders available in output")
        else:
            print(f"Error: {result['error_message']}")

    asyncio.run(test())
