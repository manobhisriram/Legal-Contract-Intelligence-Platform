from typing import List
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core import metrics
import time

logger = get_logger(__name__)


async def get_embeddings(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """Generate embeddings using OpenAI text-embedding-3-small with batching."""
    if not texts:
        return []

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # Clean texts
        batch = [t[:8000] if t else " " for t in batch]
        batch_start_ms = time.time() * 1000
        try:
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            metrics.embedding_batch_executed(len(batch), time.time()*1000 - batch_start_ms, success=True)
        except Exception as e:
            logger.error("Embedding failed for batch", error=str(e), batch_start=i)
            all_embeddings.extend([[0.0] * 1536] * len(batch))
            metrics.embedding_batch_executed(len(batch), time.time()*1000 - batch_start_ms, success=False)

    return all_embeddings


async def get_single_embedding(text: str) -> List[float]:
    """Get embedding for a single text string."""
    results = await get_embeddings([text])
    return results[0] if results else [0.0] * 1536


def rerank_chunks(query: str, chunks: List[dict], top_k: int = 5) -> List[dict]:
    """Rerank retrieved chunks using Cohere reranking API."""
    if not chunks:
        return chunks
    try:
        import cohere
        co = cohere.Client(api_key=settings.cohere_api_key)
        documents = [c.get("text", c.get("entity", {}).get("text", "")) for c in chunks]
        documents = [d[:2000] for d in documents if d]

        if not documents:
            return chunks[:top_k]

        response = co.rerank(
            query=query,
            documents=documents,
            top_n=top_k,
            model="rerank-english-v3.0",
        )
        reranked = []
        for result in response.results:
            original_chunk = chunks[result.index]
            reranked.append({**original_chunk, "rerank_score": result.relevance_score})
        return reranked
    except Exception as e:
        logger.error("Reranking failed, returning original order", error=str(e))
        return chunks[:top_k]


async def rewrite_query_for_search(query: str) -> str:
    """Use Groq to rewrite conversational query into optimized search query."""
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            max_tokens=100,
            messages=[
                {
                    "role": "system",
                    "content": "You are a search query optimizer for legal document retrieval. Convert conversational questions into precise 5-10 word search queries that will retrieve the most relevant legal clauses. Return ONLY the optimized query, nothing else.",
                },
                {"role": "user", "content": f"Optimize this query for legal document search: {query}"},
            ],
        )
        rewritten = response.choices[0].message.content.strip()
        logger.info("Query rewritten", original=query[:50], rewritten=rewritten)
        return rewritten
    except Exception as e:
        logger.error("Query rewriting failed", error=str(e))
        return query
