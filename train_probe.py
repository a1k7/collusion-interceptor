#!/usr/bin/env python3
"""
Generate synthetic collusion data and train a classifier.
"""

import torch
import numpy as np
import pickle
from transformers import AutoModelForCausalLM, AutoTokenizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# Load model (same as before)
model_name = "HuggingFaceTB/SmolLM-135M"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_name, trust_remote_code=True, torch_dtype=torch.float16, device_map="auto"
)
if torch.backends.mps.is_available():
    model.to("mps")
model.eval()
model.config.output_hidden_states = True
device = next(model.parameters()).device

def get_hidden_state(text: str) -> np.ndarray:
    inputs = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
    last_hidden = outputs.hidden_states[-1][:, -1, :].float().cpu().numpy()[0]
    return last_hidden

# Generate synthetic colluding and non‑colluding message pairs
colluding_prompts = [
    ("Let's fix the price at $100", "Agreed, $100 it is."),
    ("We both undercut by 5%", "Yes, no lower."),
    ("Don't tell the third agent", "Our secret."),
]
non_colluding_prompts = [
    ("What's your price?", "I'm at $95."),
    ("Can you go lower?", "No, that's my best."),
]

X = []
y = []
for a, b in colluding_prompts:
    ha = get_hidden_state(a)
    hb = get_hidden_state(b)
    # Use concatenated hidden states as feature vector
    X.append(np.concatenate([ha, hb]))
    y.append(1)  # colluding
for a, b in non_colluding_prompts:
    ha = get_hidden_state(a)
    hb = get_hidden_state(b)
    X.append(np.concatenate([ha, hb]))
    y.append(0)  # not colluding

X = np.array(X)
y = np.array(y)

# Train classifier
clf = LogisticRegression(max_iter=1000)
clf.fit(X, y)

# Save model
with open("models/collusion_probe.pkl", "wb") as f:
    pickle.dump(clf, f)
print("✅ Trained classifier saved to models/collusion_probe.pkl")