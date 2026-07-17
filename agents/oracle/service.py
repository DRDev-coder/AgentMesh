from agents.oracle.fact_checker import FactChecker
from shared.schemas import OracleOutput, SourceRecord


class OracleService:
    def __init__(self, checker: FactChecker | None = None):
        self.checker = checker or FactChecker()

    @property
    def ready(self) -> bool:
        return True

    def analyze(self, draft_answer: str, sources: list[SourceRecord]) -> OracleOutput:
        return self.checker.verify(draft_answer, sources)
