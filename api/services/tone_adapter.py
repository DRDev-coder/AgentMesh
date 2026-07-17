from shared.schemas import EmpathOutput


class ToneAdapter:
    """Adds a non-factual presentation prefix while preserving the verified body."""

    _PREFIXES = {
        "EMPATHETIC_URGENT": "I understand this is urgent and stressful. Let's focus on the safest next step.",
        "APOLOGETIC": "I'm sorry this situation has been frustrating.",
        "PATIENT": "I can help make the policy clearer.",
        "FRIENDLY": "I'm glad you reached out.",
        "EMPATHETIC": "I understand this situation may be difficult.",
    }

    def adapt(self, factual_answer: str, empath: EmpathOutput | None) -> str:
        if not empath:
            return factual_answer
        prefix = self._PREFIXES.get(empath.recommended_tone)
        if not prefix:
            return factual_answer
        return f"{prefix}\n\n{factual_answer}"

    @staticmethod
    def preserves_facts(factual_answer: str, adapted_answer: str) -> bool:
        return factual_answer in adapted_answer
