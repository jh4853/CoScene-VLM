import torch
from transformers import CLIPModel, CLIPProcessor

class CLIPVerifier:
    def __init__(self):
        self.device = "cpu"
        self.model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32"
        ).to(self.device)
        self.proc = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32"
        )

    @torch.no_grad()
    def score(self, image, text):
        inputs = self.proc(
            text=[text], images=[image], return_tensors="pt"
        ).to(self.device)
        return float(self.model(**inputs).logits_per_image.item())
