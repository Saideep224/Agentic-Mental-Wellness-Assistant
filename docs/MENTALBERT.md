# MentalBERT Emotion Classification

Esona leverages specialized sentiment classification to analyze user text and measure mental wellness metrics (stress, anxiety, happiness, sadness, motivation, confidence).

## Core Classification Pipeline

The classification runs within [mentalbert_service.py](file:///e:/2026%20research%20intern/esona/backend/app/services/mentalbert_service.py):

```
User Input
↓
Try Hugging Face Transformers (MentalBERT model)
├── Success: Compute token logits, run Softmax, return probabilities.
└── Failure (No GPU/torch): Fallback to lightweight Rule-Based Classifier.
```

- **Primary Model**: `praveen2021/MentalBERT-base-uncased` (or similar fine-tuned BERT checkpoints for mental health classification).
- **Inference Mode**: Measures probabilities across typical emotion groups (anxiety, depression, stress, neutral, positive).

---

## Fallback Rule-Based Classifier

Because ML model initialization is resource-heavy, the service automatically falls back to an optimized lexical classifier if `torch` or `transformers` is missing (as is the case on Render standard environments due to container RAM/disk constraints).

### Lexical Pattern Groups
The fallback matches user text against curated emotional keyword vocabularies:
- **Anxiety**: `'worry'`, `'anxious'`, `'panic'`, `'fear'`, `'spiral'`, `'scared'`, `'dread'`.
- **Stress / Exhaustion**: `'stress'`, `'exhausted'`, `'tired'`, `'pressure'`, `'burnout'`, `'overwhelm'`, `'busy'`.
- **Depressive / Sad**: `'sad'`, `'melancholy'`, `'lonely'`, `'empty'`, `'cry'`, `'hurt'`, `'numb'`, `'hopeless'`.
- **Joy / Positive**: `'happy'`, `'excited'`, `'calm'`, `'peace'`, `'glad'`, `'good'`, `'proud'`, `'better'`.

### Probability Calculation
1. Parses word counts and matches keyword patterns.
2. Combines match counts with base scores using sigmoid normalization to generate mock logits.
3. Applies a standard Softmax layer to produce a normalized probability distribution (summing to 1.0).
4. Selects the highest scoring category as the `detected_emotion` and derives a corresponding `mood_score` (0.0 to 1.0).
