from __future__ import annotations

from api.services.knowledge import _embedding_values


class _PgVectorLike:
    def tolist(self) -> list[float]:
        return [0.25, 0.5, 0.75]


def test_embedding_values_accepts_pgvector_like_objects() -> None:
    assert _embedding_values(_PgVectorLike()) == [0.25, 0.5, 0.75]


def test_embedding_values_accepts_none() -> None:
    assert _embedding_values(None) == []
