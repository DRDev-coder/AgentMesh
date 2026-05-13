from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np


class VoteTally:
    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def calculate_agreement(self, answers: List[str], threshold=0.75) -> List[str]:
        if len(answers) < 2:
            return ["AGREE"] * len(answers)

        embeddings = self.embedder.encode(answers)
        votes = []

        for i in range(len(answers)):
            similarities = []
            for j in range(len(answers)):
                if i != j:
                    sim = np.dot(embeddings[i], embeddings[j]) / (
                        np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                    )
                    similarities.append(sim)

            avg_sim = np.mean(similarities)
            if avg_sim >= threshold:
                votes.append("AGREE")
            elif avg_sim >= 0.5:
                votes.append("ABSTAIN")
            else:
                votes.append("DISAGREE")

        return votes
