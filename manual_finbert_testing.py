from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load FinBERT sentiment model (ProsusAI/finbert is common)
model_name = "ProsusAI/finbert"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# manually check the sentiment of the headline
headline = 'Rupee strengthens on sustained foreign inflows'

inputs = tokenizer(headline, return_tensors="pt", truncation=True, max_length=512)
with torch.no_grad():
    logits = model(**inputs).logits
# ProsusAI/finbert has 3 labels: positive, negative, neutral (index 0, 1, 2)
probs = torch.softmax(logits, dim=1)[0]
labels = ["positive", "negative", "neutral"]
pred_idx = logits.argmax().item()
conf = probs[pred_idx].item()

# Same scoring as news_sentiment.py: ±confidence of winning label, neutral → 0
if pred_idx == 0:   # positive
    score = conf
elif pred_idx == 1:  # negative
    score = -conf
else:                # neutral
    score = 0.0

print("Headline:", headline)
print("Prediction:", labels[pred_idx])
print("Scores:", {l: f"{p:.4f}" for l, p in zip(labels, probs.tolist())})
print("Sentiment score (news_sentiment.py style):", f"{score:.4f}")