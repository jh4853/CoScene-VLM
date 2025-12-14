# Diffusion Baseline

This folder contains a diffusion-based agentic baseline used to compare against the main VLM-driven CoScene pipeline.  
Unlike the VLM system, which operates on an explicit symbolic scene graph, this diffusion baseline explores how far a generative diffusion model can be pushed using an agentic refinement loop.

---

## Overview

**Goal:** Evaluate whether a diffusion model, guided by CLIP feedback and an agent loop, can construct images that satisfy structured spatial prompts such as:

> “Add a red cube next to a blue sphere.”

This baseline is fully image-based and does **not** manipulate a 3D scene graph.  
It instead refines a *hypothesized scene specification* and samples images until the best one is selected.

This allows us to directly compare:
- **Symbolic, tool-driven reasoning** (VLM pipeline)  
- **Purely generative, reward-guided refinement** (Diffusion baseline)

---

## Pipeline

                         ┌───────────────────────────┐
                         │        User Prompt         │
                         │  "Add a red cube next to  │
                         │      a blue sphere."       │
                         └──────────────┬────────────┘
                                        │
                                        ▼
                         ┌───────────────────────────┐
                         │   1. Planner (planner.py)  │
                         │ Parses prompt → structured │
                         │ scene hypothesis (JSON).  │
                         └──────────────┬────────────┘
                                        │
                                        ▼
                     ┌───────────────────────────────────┐
                     │ 2. Diffusion Generator            │
                     │ (diffusion_gen.py)                │
                     │                                   │
                     │ Converts scene hypothesis →       │
                     │ SD prompt and generates images.   │
                     │                                   │
                     └──────────────┬────────────────────┘
                                    │
                                    ▼
                         ┌───────────────────────────┐
                         │   3. CLIP Verifier         │
                         │    (clip_verifier.py)      │
                         │ Scores each image based on │
                         │ prompt alignment.          │
                         └──────────────┬────────────┘
                                        │
                                        ▼
                      ┌───────────────────────────────────────┐
                      │      4. Agent Loop (pipeline.py)       │
                      │────────────────────────────────────────│
                      │ • Generate N image candidates          │
                      │ • Score with CLIP                      │
                      │ • Keep highest-scoring sample          │
                      │ • Refine scene hypothesis              │
                      │ • Repeat for K iterations              │
                      └──────────────┬─────────────────────────┘
                                     │
                                     ▼
                         ┌───────────────────────────┐
                         │       Final Output         │
                         │  Best image + score curve  │
                         │  + intermediate samples    │
                         └────────────────────────────┘
## 📊 Results & Analysis

### Final Image (Diffusion Baseline Output)

The agentic diffusion pipeline produced the following best image after refinement:

Although visually coherent, the model fails to express the structured spatial relationships and object-level constraints specified in the scene.

---

### Extracted Best Scene Specification
The highest-scoring scene hypothesis selected by the agent was:

```json
{
  "style": "cartoon 3D render, bright colors",
  "layout": "behind",
  "objects": [
    {"shape": "cube", "color": "red", "count": 1},
    {"shape": "sphere", "color": "red", "count": 1},
    {"shape": "cylinder", "color": "red", "count": 1}
  ]
}

