"""Validate and summarize the versioned policy knowledge base.

The consolidated runtime reads the approved JSON file directly, so no external
vector database seeding step is required.
"""

from agents.sage.rag_engine import RAGEngine


def seed() -> None:
    engine = RAGEngine()
    if not engine.ready:
        raise RuntimeError(engine.error)
    print(f"Knowledge base ready: {len(engine.documents)} approved documents from {engine.path}")


if __name__ == "__main__":
    seed()
