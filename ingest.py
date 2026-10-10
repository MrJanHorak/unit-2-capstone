"""Embed overlapping UTF-8 text/Markdown chunks; safe to run repeatedly."""
import argparse
from pathlib import Path
from config import Settings
from retrieval import collection_for, embedding_model


def chunk_document(text, chunk_size=500, overlap=50):
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= overlap < chunk_size")
    words, chunks = text.split(), []
    for start in range(0, len(words), chunk_size - overlap):
        chunks.append(" ".join(words[start:start + chunk_size]))
        if start + chunk_size >= len(words):
            break  # Avoid an unnecessary final overlap-only chunk.
    return chunks


def ingest(docs_path=None, settings=None):
    settings = settings or Settings.from_environment()
    docs_path = Path(docs_path or settings.documents)
    if not docs_path.is_dir():
        raise FileNotFoundError(f"Document folder does not exist: {docs_path}")
    model = embedding_model(settings.embedding_model)
    with collection_for(settings, create=True) as collection:
        return _ingest_collection(docs_path, collection, model)


def _ingest_collection(docs_path, collection, model):
    """Synchronise this folder while the caller owns the open Chroma client."""
    sources, total = set(), 0
    for path in sorted(docs_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
            continue
        source = path.relative_to(docs_path).as_posix()
        sources.add(source)
        chunks = chunk_document(path.read_text(encoding="utf-8"))
        old_ids = set(collection.get(where={"source": source})["ids"])
        ids = [f"{source}:{i}" for i in range(len(chunks))]
        if chunks:
            collection.upsert(ids=ids, documents=chunks, embeddings=model.encode(chunks).tolist(),
                              metadatas=[{"source": source, "chunk": i} for i in range(len(chunks))])
        stale = old_ids - set(ids)
        if stale:
            collection.delete(ids=sorted(stale))  # Remove old trailing chunks when a file shrinks.
        total += len(chunks)
        print(f"Ingested {len(chunks)} chunks from {source}")
    existing = collection.get(include=["metadatas"])
    stale = [identifier for identifier, meta in zip(existing["ids"], existing["metadatas"])
             if meta["source"] not in sources]
    if stale:
        collection.delete(ids=stale)  # The selected folder is authoritative for this index.
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents", nargs="?")
    ingest(parser.parse_args().documents)
