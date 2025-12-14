import torch
from diffusers import StableDiffusionPipeline

class DiffusionGenerator:
    def __init__(self, size=384):
        self.device = "cpu"
        self.size = size
        self.pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
        ).to(self.device)
        self.pipe.enable_attention_slicing()

    @torch.no_grad()
    def generate(self, prompt, seed):
        g = torch.Generator(device=self.device).manual_seed(seed)
        out = self.pipe(
            prompt,
            generator=g,
            num_inference_steps=12,
            guidance_scale=7.5,
            height=self.size,
            width=self.size,
        )
        return out.images[0]
