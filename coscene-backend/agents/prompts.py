"""
Prompt templates for VLM agents.
"""

SYSTEM_PROMPT = """You are an expert USD (Universal Scene Descriptor) engineer and 3D scene designer.
Your role is to generate valid USD code that modifies 3D scenes based on natural language instructions.

Guidelines:
1. Always output ONLY valid USD ASCII format code
2. Start with #usda 1.0 version declaration
3. Use proper USD syntax with correct indentation
4. Include proper transforms (translation, rotation, scale)
5. Set up materials using UsdPreviewSurface
6. Maintain scene hierarchy under /World root
7. Use descriptive names for objects
8. Add comments to explain complex modifications

Remember: Users may not know USD syntax, but they know what they want to see. Translate their intent into proper USD code.
"""

USD_GENERATION_PROMPT_TEMPLATE = """Generate USD code to modify the following 3D scene.

Current Scene:
```usd
{current_usd}
```

User Request: "{user_prompt}"

Visual Context:
You are provided with rendered view(s) of the current scene state showing how it currently looks. Use these images as visual context to better understand the scene's current appearance, object positions, colors, and spatial relationships when making modifications.

Instructions:
1. Analyze the user's request carefully
2. Review the provided render(s) to understand the current visual state
3. Determine what needs to be added, modified, or removed
4. IMPORTANT: Preserve ALL existing objects in the scene UNLESS the user explicitly requests their removal
5. Generate complete, valid USD code for the entire scene including:
   - Objects mentioned in the user's request (with modifications applied)
   - ALL other existing objects (unchanged)
6. Ensure all USD syntax is correct
7. Use appropriate default values for unspecified properties

Output Format:
Generate ONLY the USD code, no explanations. Start with #usda 1.0

USD Code:
"""

SIMPLE_USD_GENERATION_PROMPT = """You are a USD code generator. Given a natural language description, generate valid USD scene code.

User wants: "{user_prompt}"

Generate complete USD code for this scene. Include:
- Version declaration (#usda 1.0)
- defaultPrim = "World"
- upAxis = "Z"
- Proper scene hierarchy
- Materials for all objects
- Appropriate transforms

Output ONLY the USD code, starting with #usda 1.0:
"""

PARSE_INTENT_PROMPT = """Analyze the following user request for 3D scene editing and extract the intent.

User Request: "{user_prompt}"

Current Scene Objects: {scene_objects}

Determine:
1. Action type: add, remove, modify, or change_lighting
2. Target object(s): What objects are being affected
3. Properties: What properties need to change (position, color, size, material, etc.)
4. New objects: Any new objects to create

Respond in JSON format:
{{
    "action": "add|remove|modify|change_lighting",
    "target": "object name or null",
    "properties": {{}},
    "new_objects": [
        {{
            "type": "Sphere|Cube|Cylinder|etc",
            "name": "descriptive name",
            "parameters": {{}}
        }}
    ]
}}
"""

# Verification prompts
VERIFICATION_PROMPT_TEMPLATE = """Compare the before and after states of a 3D scene modification.

User requested: "{user_prompt}"

Before Scene:
{before_objects}

After Scene:
{after_objects}

Verification Checklist:
1. Was the requested action performed correctly?
2. Are any objects missing or incorrectly placed?
3. Are materials/colors correct?
4. Are there any unintended side effects?

Respond in JSON:
{{
    "verification_passed": true/false,
    "issues_found": ["list of problems"],
    "suggested_fix": "description of how to fix, or null"
}}
"""

# Vision-based verification prompt with multi-view renders
VISION_VERIFICATION_PROMPT = """You are verifying whether a 3D scene modification correctly fulfills a user's request.

User Request: "{user_prompt}"

You are provided with rendered images of the scene from multiple camera angles (perspective, front, top, side).

Your task:
1. Examine the rendered images carefully
2. Determine if the modification matches the user's intent
3. Identify any issues or discrepancies
4. If issues exist, provide specific, actionable feedback for correction

Visual Verification Checklist:
- Does the scene contain all objects requested by the user?
- Are the REQUESTED objects positioned correctly relative to each other?
- Are colors, materials, and textures correct for REQUESTED modifications?
- Are object sizes/scales appropriate for REQUESTED objects?
- IMPORTANT: Are pre-existing objects that were NOT mentioned in the request still present and unchanged?
- Are there any unwanted NEW objects that were not requested?
- Does the overall composition match the user's intent?

Critical Rule: Only flag objects as "unwanted" if they appear to be NEW additions not present in the original scene. Pre-existing objects should be preserved unless the user explicitly requested their removal.

Respond in the following JSON format (ONLY output valid JSON, no markdown):
{{
    "verification_passed": true,
    "confidence": 0.95,
    "issues_found": [],
    "detailed_feedback": "The scene correctly shows...",
    "suggested_fixes": null
}}

OR if issues are found:
{{
    "verification_passed": false,
    "confidence": 0.85,
    "issues_found": [
        "The red sphere is positioned too far left",
        "The cube should be blue, not green"
    ],
    "detailed_feedback": "While the scene includes the requested objects, there are positioning and color issues...",
    "suggested_fixes": "Move the sphere to coordinate (0, 0, 0) and change the cube's diffuseColor to (0, 0, 1)"
}}
"""

# Fix generation prompt
FIX_GENERATION_PROMPT = """You previously generated USD code for a 3D scene, but verification found issues.

Original User Request: "{user_prompt}"

Current USD Code:
```usd
{current_usd}
```

Verification Feedback:
{verification_feedback}

Issues Found:
{issues_list}

Suggested Fixes:
{suggested_fixes}

Generate corrected USD code that addresses ALL the issues while maintaining the correct parts of the scene.

CRITICAL: When fixing issues, preserve ALL objects from the current scene UNLESS:
1. The user explicitly requested their removal
2. The verification feedback specifically identifies them as newly added errors

Do not remove pre-existing objects just because they weren't mentioned in the user's request.

Output Format:
Generate ONLY the complete corrected USD code, no explanations. Start with #usda 1.0

USD Code:
"""

# Error recovery prompt
ERROR_RECOVERY_PROMPT = """The previous USD generation failed with an error.

Original Request: "{user_prompt}"

Error: {error_message}

Previous USD Output:
```
{failed_usd}
```

Generate corrected USD code that addresses the error while still fulfilling the user's request.
Output ONLY valid USD code starting with #usda 1.0:
"""


def get_usd_generation_prompt(current_usd: str, user_prompt: str) -> str:
    """Get prompt for USD generation."""
    if not current_usd or current_usd.strip() == "":
        # First generation - no existing scene
        return SIMPLE_USD_GENERATION_PROMPT.format(user_prompt=user_prompt)
    else:
        # Modification of existing scene
        return USD_GENERATION_PROMPT_TEMPLATE.format(
            current_usd=current_usd,
            user_prompt=user_prompt
        )


def get_parse_intent_prompt(user_prompt: str, scene_objects: list) -> str:
    """Get prompt for parsing user intent."""
    objects_str = ", ".join(
        [f"{obj.get('name')} ({obj.get('type')})" for obj in scene_objects])
    if not objects_str:
        objects_str = "Empty scene"

    return PARSE_INTENT_PROMPT.format(
        user_prompt=user_prompt,
        scene_objects=objects_str
    )


def get_verification_prompt(
    user_prompt: str,
    before_objects: list,
    after_objects: list
) -> str:
    """Get prompt for verification (Phase 2)."""
    before_str = "\n".join(
        [f"- {obj['name']} ({obj['type']})" for obj in before_objects])
    after_str = "\n".join(
        [f"- {obj['name']} ({obj['type']})" for obj in after_objects])

    return VERIFICATION_PROMPT_TEMPLATE.format(
        user_prompt=user_prompt,
        before_objects=before_str or "Empty",
        after_objects=after_str or "Empty"
    )


def get_error_recovery_prompt(
    user_prompt: str,
    error_message: str,
    failed_usd: str
) -> str:
    """Get prompt for error recovery."""
    return ERROR_RECOVERY_PROMPT.format(
        user_prompt=user_prompt,
        error_message=error_message,
        failed_usd=failed_usd
    )


def get_vision_verification_prompt(user_prompt: str) -> str:
    """Get prompt for vision-based verification (Phase 2)."""
    return VISION_VERIFICATION_PROMPT.format(user_prompt=user_prompt)


def get_fix_generation_prompt(
    user_prompt: str,
    current_usd: str,
    verification_feedback: str,
    issues_list: list,
    suggested_fixes: str
) -> str:
    """Get prompt for generating fixes based on verification feedback."""
    issues_str = "\n".join([f"- {issue}" for issue in issues_list])
    return FIX_GENERATION_PROMPT.format(
        user_prompt=user_prompt,
        current_usd=current_usd,
        verification_feedback=verification_feedback,
        issues_list=issues_str,
        suggested_fixes=suggested_fixes or "No specific fixes suggested"
    )
