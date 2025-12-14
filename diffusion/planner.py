import re

_COLORS = ["red","blue","green","yellow","black","white","gray","orange","purple","pink","brown"]
_SHAPES  = ["cube","sphere","cylinder"]

def plan(prompt: str) -> dict:
    p = prompt.lower()
    objects = []

    for s in _SHAPES:
        if s in p:
            color = next((c for c in _COLORS if c in p), "red")
            objects.append({"shape": s, "color": color, "count": 1})

    if not objects:
        objects = [
            {"shape": "cube", "color": "red", "count": 1},
            {"shape": "sphere", "color": "blue", "count": 1},
        ]

    layout = "next to"
    if "left" in p: layout = "left of"
    if "right" in p: layout = "right of"
    if "behind" in p: layout = "behind"

    return {
        "style": "simple 3D render, plain background, clean lighting",
        "layout": layout,
        "objects": objects,
    }
