"""
Manual FinBERT check: score a single headline the way news_sentiment.py does.
Requires transformers + torch.

Run:
    python manual_finbert_testing.py
    python manual_finbert_testing.py "Rupee strengthens on sustained foreign inflows"
"""
import sys

DEFAULT_HEADLINE = "Rupee strengthens on sustained foreign inflows"


def score_headline(headline: str) -> tuple[str, float, dict]:
    """Return (label, score, per-label probabilities) for one headline."""
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch

    # Load FinBERT sentiment model (ProsusAI/finbert is common).
    # Revision pinned to the maintainer branch for the same reason as
    # news_sentiment._get_finbert(): unpinned loads can resolve weights from an
    # unmerged pull request on the Hub.
    model_name = "ProsusAI/finbert"
    revision = "main"
    tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, revision=revision)

    inputs = tokenizer(headline, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    # ProsusAI/finbert has 3 labels: positive, negative, neutral (index 0, 1, 2)
    probs = torch.softmax(logits, dim=1)[0]
    labels = ["positive", "negative", "neutral"]
    pred_idx = int(logits.argmax().item())
    conf = float(probs[pred_idx].item())

    # Same scoring as news_sentiment.py: ±confidence of winning label, neutral → 0
    if pred_idx == 0:    # positive
        score = conf
    elif pred_idx == 1:  # negative
        score = -conf
    else:                # neutral
        score = 0.0

    return labels[pred_idx], score, {l: float(p) for l, p in zip(labels, probs.tolist(), strict=True)}


def main() -> int:
    headline = " ".join(sys.argv[1:]).strip() or DEFAULT_HEADLINE
    label, score, probs = score_headline(headline)
    print("Headline:", headline)
    print("Prediction:", label)
    print("Scores:", {l: f"{p:.4f}" for l, p in probs.items()})
    print("Sentiment score (news_sentiment.py style):", f"{score:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
