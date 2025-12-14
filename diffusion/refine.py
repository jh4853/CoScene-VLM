import copy, random

STYLES = [
    "simple 3D render, plain background, clean lighting",
    "isometric 3D render, clean lighting",
    "cartoon 3D render, bright colors",
]

def spec_to_prompt(user_prompt, spec):
    objs = ", ".join([f"{o['color']} {o['shape']}" for o in spec["objects"]])
    return f"{spec['style']}. A scene with {objs}, arranged {spec['layout']}. {user_prompt}"

def mutate(spec):
    s = copy.deepcopy(spec)
    if random.random() < 0.5:
        s["style"] = random.choice(STYLES)
    return s
