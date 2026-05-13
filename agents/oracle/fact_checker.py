from sentence_transformers import SentenceTransformer
import numpy as np


class FactChecker:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def compare_answers(self, answer1: str, answer2: str):
        embeddings = self.model.encode([answer1, answer2])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)

    def check_against_context(self, answer: str, context: str):
        if not context or not context.strip():
            return 0.0
        embeddings = self.model.encode([answer, context])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)
