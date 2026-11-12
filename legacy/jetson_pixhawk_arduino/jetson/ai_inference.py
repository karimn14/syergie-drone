# ai_inference.py – Real AI model loading/inference for vision_recheck
import cv2
import numpy as np
import torch
from torchvision import transforms

class BloomClassifier:
    def __init__(self, model_path="bloom_model.pt", device="cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = torch.load(model_path, map_location=self.device)
        self.model.eval()
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
    def infer(self, frame):
        tensor = self.transform(frame).unsqueeze(0).to(self.device)
        with torch.no_grad():
            out = self.model(tensor)
            prob = torch.softmax(out, dim=1)
            pred = prob.argmax(dim=1).item()
        # Assume 1 = 'female_bloom', 0 = 'other'
        return ['female_bloom'] if pred == 1 else []
