from transformers import pipeline


class EmotionAnalyzer:
    def __init__(self):
        self.classifier = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )

    def analyze(self, text: str):
        result = self.classifier(text[:512])[0]
        label = result["label"]
        score = result["score"]

        text_lower = text.lower()

        if any(w in text_lower for w in ["angry", "furious", "terrible", "worst", "scam", "fraud", "cheat", "lawsuit"]):
            emotion = "ANGRY"
            urgency = 9
        elif any(w in text_lower for w in ["urgent", "immediately", "asap", "emergency", "lost", "stolen", "hacked"]):
            emotion = "URGENT"
            urgency = 10
        elif any(w in text_lower for w in ["confused", "don't understand", "help", "how do i", "what is"]):
            emotion = "CONFUSED"
            urgency = 5
        elif any(w in text_lower for w in ["happy", "thanks", "great", "excellent", "love"]):
            emotion = "SATISFIED"
            urgency = 2
        else:
            emotion = "NEUTRAL"
            urgency = 5

        tone_map = {
            "ANGRY": "APOLOGETIC",
            "URGENT": "REASSURING",
            "CONFUSED": "PATIENT",
            "SATISFIED": "FRIENDLY",
            "NEUTRAL": "PROFESSIONAL"
        }

        return {
            "emotion": emotion,
            "urgency": urgency,
            "sentiment_label": label,
            "sentiment_score": round(score, 3),
            "recommended_tone": tone_map.get(emotion, "PROFESSIONAL"),
            "churn_risk": urgency > 7
        }
