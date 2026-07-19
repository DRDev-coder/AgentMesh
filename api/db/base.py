from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from api.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, settings: Settings | None = None, url: str | None = None):
        self.settings = settings or get_settings()
        self.url = url or self.settings.database_url
        if self.url.startswith("sqlite") and "///" in self.url:
            relative = self.url.split("///", 1)[1]
            if relative and relative != ":memory:":
                Path(relative).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if self.url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            self.url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        if self.url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._sqlite_foreign_keys)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )

    @staticmethod
    def _sqlite_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def initialize(self) -> None:
        from api.db import models  # noqa: F401

        if self.settings.environment in {"development", "test"}:
            if self.url.startswith("postgresql"):
                with self.engine.begin() as connection:
                    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            Base.metadata.create_all(self.engine)
        else:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

    @contextmanager
    def session(self) -> Iterator[Session]:
        value = self.session_factory()
        try:
            yield value
            value.commit()
        except Exception:
            value.rollback()
            raise
        finally:
            value.close()

    def health(self) -> bool:
        try:
            with self.engine.connect() as connection:
                return connection.execute(text("SELECT 1")).scalar_one() == 1
        except Exception:
            return False

    def dispose(self) -> None:
        self.engine.dispose()
