from agents.empath.emotion_model import EmotionAnalyzer


class EmpathService(EmotionAnalyzer):
    def __init__(self, preferred_tone: str = "PROFESSIONAL"):
        self.preferred_tone = preferred_tone

    def analyze(self, text: str):
        output = super().analyze(text)
        if output.recommended_tone == "PROFESSIONAL" and self.preferred_tone in {
            "PROFESSIONAL",
            "FRIENDLY",
            "PATIENT",
            "EMPATHETIC",
        }:
            return output.model_copy(
                update={"recommended_tone": self.preferred_tone}
            )
        return output

    @property
    def ready(self) -> bool:
        return True
