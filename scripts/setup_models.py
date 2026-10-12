"""Downloads the small pretrained models the AI Engineering track uses, once.
Exercises run with HF_HUB_OFFLINE=1, so they only ever read this cache.

    npm run setup:models
"""
from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer

MODELS = {
    "distilbert/distilbert-base-uncased-finetuned-sst-2-english": AutoModelForSequenceClassification,  # sentiment
    "distilbert/distilgpt2": AutoModelForCausalLM,  # small text generator
}

for name, cls in MODELS.items():
    AutoTokenizer.from_pretrained(name)
    cls.from_pretrained(name)
    print("cached", name)
