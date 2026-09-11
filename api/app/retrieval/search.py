import math
import re
from collections import Counter

from openai import APIError
from sqlalchemy import select, text

from app.core.settings import get_settings
from app.db.store import ChunkRow, store
from app.llm.gemini import GeminiError
from app.llm.provider import embed, is_rate_limit

STOP = {
    "the",
    "is",
    "are",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "this",
    "it",
    "how",
    "what",
    "where",
    "do",
    "does",
    "can",
    "i",
    "me",
    "you",
    "my",
    "for",
    "with",
    "from",
    "repository",
    "repo",
    "project",
    "should",
    "be",
    "understand",
    "implemented",
}
ALIASES = {
    "authentication": {"auth", "session", "login", "oauth"},
    "auth": {"authentication", "session", "login"},
    "testing": {"test", "pytest", "vitest", "playwright"},
    "tests": {"test", "pytest", "vitest", "playwright"},
    "deploy": {"deployment", "docker", "build", "uvicorn"},
    "deployed": {"deployment", "docker", "build"},
    "structure": {"architecture", "layout", "components"},
    "structured": {"architecture", "structure", "layout"},
    "contributing": {"contributing", "getting", "started", "test"},
    "contribute": {"contributing", "test"},
    "run": {"getting", "started", "dev", "install"},
    "database": {"postgresql", "sqlalchemy", "models", "prisma"},
    "risk": {"security", "ownership", "token", "authentication"},
    "learn": {"getting", "started", "structure", "architecture"},
}


def terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z][a-z0-9_]+", value.lower()) if term not in STOP}


def lexical_rank(question: str, sources: list[dict]) -> list[tuple[float, dict]]:
    query = terms(question)
    if not query:
        return []
    expanded = set(query)
    for term in query:
        expanded.update(ALIASES.get(term, set()))
    document_counts: Counter = Counter()
    docs = []
    for source in sources:
        tokens = terms(source["excerpt"])
        docs.append(tokens)
        document_counts.update(tokens)
    ranked = []
    for source, tokens in zip(sources, docs, strict=True):
        overlap = expanded & tokens
        path_overlap = expanded & terms(source["path"] + " " + source["heading"])
        if not overlap and not path_overlap:
            continue
        score = sum(
            math.log(1 + (len(sources) + 1) / (document_counts[token] + 1)) for token in overlap
        )
        score += 2.2 * len(path_overlap)
        # Weak matches such as "add" should not answer an unanswerable query.
        meaningful = overlap - {
            "add",
            "new",
            "feature",
            "change",
            "use",
            "using",
            "first",
            "handled",
        }
        if not meaningful and not path_overlap:
            continue
        ranked.append((score, source))
    return sorted(ranked, key=lambda pair: pair[0], reverse=True)


async def retrieve(repository_id: str, question: str, limit: int = 5) -> list[dict]:
    sources = store.list("sources", repository_id=repository_id)
    lookup = {source["id"]: source for source in sources}
    lexical = lexical_rank(question, sources)
    vector: list[tuple[float, str]] = []
    compatible = None
    if get_settings().embeddings_enabled:
        with store.session() as session:
            compatible = session.scalar(
                select(ChunkRow.id)
                .where(
                    ChunkRow.repository_id == repository_id,
                    ChunkRow.embedding_model == get_settings().embedding_identity,
                    ChunkRow.embedding.is_not(None),
                )
                .limit(1)
            )
    if get_settings().embeddings_enabled and compatible:
        try:
            query_vectors = await embed([question], task="query")
        except (APIError, GeminiError) as exc:
            if not is_rate_limit(exc):
                raise
            # Keyword evidence remains usable when embedding quota is exhausted.
            query_vectors = []
        if query_vectors:
            query = query_vectors[0]
            with store.session() as session:
                if store.engine.dialect.name == "postgresql":
                    rows = session.execute(
                        text(
                            "SELECT source_id, 1 - (embedding <=> CAST(:query AS vector)) AS score FROM chunks WHERE repository_id = :rid AND embedding IS NOT NULL AND embedding_model = :model ORDER BY embedding <=> CAST(:query AS vector) LIMIT 15"
                        ),
                        {
                            "query": str(query),
                            "rid": repository_id,
                            "model": get_settings().embedding_identity,
                        },
                    )
                    vector = [
                        (float(row.score), row.source_id) for row in rows if row.score >= 0.30
                    ]
                else:
                    for chunk in session.scalars(
                        select(ChunkRow).where(
                            ChunkRow.repository_id == repository_id,
                            ChunkRow.embedding_model == get_settings().embedding_identity,
                        )
                    ):
                        if chunk.embedding:
                            denominator = math.sqrt(
                                sum(x * x for x in query) * sum(x * x for x in chunk.embedding)
                            )
                            score = sum(
                                a * b for a, b in zip(query, chunk.embedding, strict=True)
                            ) / (denominator or 1)
                            if score >= 0.30:
                                vector.append((score, str(chunk.source_id)))
                    vector.sort(reverse=True)
    # Reciprocal-rank fusion balances lexical specificity and semantic matches.
    scores: dict[str, float] = {}
    for rank, (_, source) in enumerate(lexical[:20]):
        scores[source["id"]] = 1 / (40 + rank)
    for rank, (_, identifier) in enumerate(vector[:15]):
        scores[identifier] = scores.get(identifier, 0) + 1 / (40 + rank)
    result: list[dict] = []
    for identifier in sorted(scores, key=lambda identifier: scores[identifier], reverse=True):
        matched_source = lookup.get(identifier)
        if not matched_source:
            continue
        if any(
            old["path"] == matched_source["path"]
            and abs(old["start_line"] - matched_source["start_line"]) < 70
            for old in result
        ):
            continue
        result.append(matched_source)
        if len(result) >= limit:
            break
    return result
