"""Transactional SQLAlchemy storage; PostgreSQL gets native pgvector columns.

SQLite is an explicit development fallback. JSON payloads retain versioned API
objects while ownership and snapshot identities are relational and indexed.
"""

from __future__ import annotations

import builtins
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    String,
    create_engine,
    delete,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.settings import get_settings


def now() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class RecordMixin:
    id = Column(String, primary_key=True)
    owner_id = Column(String, nullable=False, index=True)
    repository_id = Column(String, nullable=True, index=True)
    payload = Column(JSON, nullable=False)


class RepositoryRow(RecordMixin, Base):
    __tablename__ = "repositories"


class SnapshotRow(RecordMixin, Base):
    __tablename__ = "repository_snapshots"


class SourceRow(RecordMixin, Base):
    __tablename__ = "sources"


class SkillRow(RecordMixin, Base):
    __tablename__ = "skills"


class JobRow(RecordMixin, Base):
    __tablename__ = "index_jobs"


class ConversationRow(RecordMixin, Base):
    __tablename__ = "conversations"


class MessageRow(RecordMixin, Base):
    __tablename__ = "messages"


class CitationRow(RecordMixin, Base):
    __tablename__ = "citations"


class UserRow(RecordMixin, Base):
    __tablename__ = "users"


class AccountRow(RecordMixin, Base):
    __tablename__ = "github_accounts"


class UsageRow(RecordMixin, Base):
    __tablename__ = "usage_events"


class ChunkRow(Base):
    __tablename__ = "chunks"
    id = Column(String, primary_key=True)
    repository_id = Column(String, index=True, nullable=False)
    source_id = Column(String, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(JSON().with_variant(Vector(1536), "postgresql"), nullable=True)
    embedding_model = Column(String, nullable=True)
    ordinal = Column(Integer, default=0)


TABLES: dict[str, Any] = {
    "repositories": RepositoryRow,
    "snapshots": SnapshotRow,
    "sources": SourceRow,
    "skills": SkillRow,
    "jobs": JobRow,
    "conversations": ConversationRow,
    "messages": MessageRow,
    "citations": CitationRow,
    "users": UserRow,
    "accounts": AccountRow,
    "usage": UsageRow,
}


class Store:
    def __init__(self, url: str | None = None):
        self.url = url or get_settings().database_url
        self.engine = create_engine(
            self.url,
            connect_args={"check_same_thread": False} if self.url.startswith("sqlite") else {},
            pool_pre_ping=True,
        )

    def initialize(self):
        if self.engine.dialect.name == "postgresql":
            with self.engine.begin() as connection:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(self.engine)
        if self.engine.dialect.name == "postgresql":
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS chunks_lexical_gin ON chunks USING gin (to_tsvector('english', content))"
                    )
                )

    @contextmanager
    def session(self):
        with Session(self.engine) as session, session.begin():
            yield session

    def get(self, table: str, identifier: str) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.get(TABLES[table], identifier)
            if row is None:
                return None
            return {**row.payload, "_owner_id": row.owner_id, "_repository_id": row.repository_id}

    def put(self, table: str, payload: dict, owner: str, repository_id: str | None = None):
        payload = {key: value for key, value in payload.items() if not key.startswith("_")}
        with self.session() as session:
            row = session.get(TABLES[table], payload["id"])
            if row:
                row.payload = payload
                row.owner_id = owner
            else:
                session.add(
                    TABLES[table](
                        id=payload["id"],
                        owner_id=owner,
                        repository_id=repository_id,
                        payload=payload,
                    )
                )

    def list(
        self, table: str, owner: str | None = None, repository_id: str | None = None
    ) -> list[dict]:
        model = TABLES[table]
        query = select(model)
        if owner is not None:
            query = query.where(model.owner_id == owner)
        if repository_id is not None:
            query = query.where(model.repository_id == repository_id)
        with self.session() as session:
            return [dict(row.payload) for row in session.scalars(query).all()]

    def delete(self, table: str, identifier: str):
        with self.session() as session:
            session.execute(delete(TABLES[table]).where(TABLES[table].id == identifier))

    def replace_index(
        self,
        repo: dict,
        sources: builtins.list[dict],
        embeddings: builtins.list,
        skills: builtins.list[dict],
        files: dict,
    ):
        """All-or-nothing snapshot replacement: a failed index leaves the old one usable."""
        rid, owner = repo["id"], repo["_owner_id"]
        with self.session() as session:
            session.execute(delete(ChunkRow).where(ChunkRow.repository_id == rid))
            for model in (SourceRow, SkillRow):
                session.execute(delete(model).where(model.repository_id == rid))
            for index, source in enumerate(sources):
                session.add(
                    SourceRow(id=source["id"], owner_id=owner, repository_id=rid, payload=source)
                )
                session.flush()
                session.add(
                    ChunkRow(
                        id=source["id"],
                        repository_id=rid,
                        source_id=source["id"],
                        content=source["excerpt"],
                        embedding=embeddings[index] if embeddings else None,
                        embedding_model=get_settings().embedding_identity if embeddings else None,
                        ordinal=index,
                    )
                )
            for skill in skills:
                session.add(
                    SkillRow(
                        id=rid + ":" + skill["id"], owner_id=owner, repository_id=rid, payload=skill
                    )
                )
            snapshot_id = rid + ":" + repo["commit_sha"]
            session.merge(
                SnapshotRow(
                    id=snapshot_id,
                    owner_id=owner,
                    repository_id=rid,
                    payload={
                        "id": snapshot_id,
                        "commit_sha": repo["commit_sha"],
                        "created_at": now(),
                        "files": files,
                    },
                )
            )
            row = session.get(RepositoryRow, rid)
            if row:
                row.payload = {key: value for key, value in repo.items() if not key.startswith("_")}

    def delete_repository(self, rid: str):
        with self.session() as session:
            session.execute(delete(ChunkRow).where(ChunkRow.repository_id == rid))
            for model in TABLES.values():
                session.execute(delete(model).where(model.repository_id == rid))
            session.execute(delete(RepositoryRow).where(RepositoryRow.id == rid))

    def ready(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True


store = Store()
