from agents.empath.emotion_model import EmotionAnalyzer


class EmpathService(EmotionAnalyzer):
    @property
    def ready(self) -> bool:
        return True
