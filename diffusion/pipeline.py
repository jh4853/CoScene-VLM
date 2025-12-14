import os, json
from planner import plan
from refine import spec_to_prompt, mutate
from diffusion_gen import DiffusionGenerator
from clip_verifier import CLIPVerifier

class Pipeline:
    def __init__(self):
        self.gen = DiffusionGenerator()
        self.verifier = CLIPVerifier()

    def run(self, prompt, iters=3, out_dir="outputs"):
        os.makedirs(out_dir, exist_ok=True)

        spec = plan(prompt)
        best_spec = spec
        best_score = -1e9
        best_img = None
        history = []

        for i in range(iters):
            candidates = [best_spec, mutate(best_spec)]
            for c in candidates:
                dprompt = spec_to_prompt(prompt, c)
                img = self.gen.generate(dprompt, seed=i)
                score = self.verifier.score(img, prompt)
                if score > best_score:
                    best_score = score
                    best_spec = c
                    best_img = img
            history.append(best_score)

        best_img.save(f"{out_dir}/best.png")
        json.dump(best_spec, open(f"{out_dir}/best_spec.json","w"), indent=2)
        json.dump(history, open(f"{out_dir}/score_history.json","w"), indent=2)

        return best_score, history
