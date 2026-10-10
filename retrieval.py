"""Shared embedding settings, lazy model loading, and bounded retrieval context."""
from functools import lru_cache
from contextlib import contextmanager
import re

STOPWORDS = {"what", "is", "our", "company", "the", "explain", "how", "do", "we", "does",
             "and", "to", "of", "in", "a", "an", "about", "are", "can", "me", "show",
             "please", "for", "with", "it", "this", "that", "process"}


def keywords(text):
    words = set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS
    return {word[:-3] + "y" if word.endswith("ies") else word[:-1] if word.endswith("s") else word
            for word in words}


def rank_candidates(query, candidates):
    """Combine semantic similarity with term coverage to retain precise policy references."""
    terms = keywords(query)
    for candidate in candidates:
        overlap = len(terms & keywords(candidate["content"])) / max(1, len(terms))
        similarity = max(0, min(1, 1 - candidate["distance"]))
        candidate["hybrid_score"] = 0.65 * similarity + 0.35 * overlap
    return sorted(candidates, key=lambda candidate: candidate["hybrid_score"], reverse=True)


@lru_cache(maxsize=2)
def embedding_model(name):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name)


@contextmanager
def collection_for(settings, create=False):
    import chromadb
    client = chromadb.PersistentClient(path=str(settings.index))
    try:
        if create:
            collection = client.get_or_create_collection(settings.collection, metadata={"hnsw:space": "cosine"})
        else:
            try:
                collection = client.get_collection(settings.collection)
            except Exception as exc:
                raise RuntimeError("Document index missing. Run python ingest.py first.") from exc
        yield collection
    finally:
        client.close()  # Release SQLite and vector-file handles, including on Windows.


def retrieve(query, settings):
    with collection_for(settings) as collection:
        count = collection.count()
        if not count:
            return []
        embedding = embedding_model(settings.embedding_model).encode([query]).tolist()
        # Fetch a small candidate pool first; cutting to two purely semantic hits
        # excluded the short code-review section in a broad security document.
        results = collection.query(query_embeddings=embedding, n_results=min(max(5, settings.top_k), count))
    candidates = [{"content": doc, "source": meta["source"], "chunk": meta["chunk"], "distance": distance}
                  for doc, meta, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0])]
    chunks, remaining = [], settings.context_words
    for candidate in rank_candidates(query, candidates)[:settings.top_k]:
        words = candidate["content"].split()[:remaining]
        if not words:
            break
        chunks.append({**candidate, "content": " ".join(words)})
        remaining -= len(words)
    return chunks
