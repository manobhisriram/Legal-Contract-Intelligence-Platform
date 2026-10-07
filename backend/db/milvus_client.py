from pymilvus import MilvusClient, DataType
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core import metrics
import time as _time
from typing import List, Dict, Any, Optional
import json
import uuid

logger = get_logger(__name__)

_client: Optional[MilvusClient] = None

EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small dimension


def contract_filter(contract_id: str) -> str:
    """Build a Milvus filter expression for one contract.

    The identifier is parsed as a UUID so untrusted input can never alter the expression.
    """
    return f'contract_id == "{uuid.UUID(str(contract_id))}"'


def get_milvus_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(
            uri=settings.zilliz_cloud_uri,
            token=settings.zilliz_cloud_api_key,
        )
        logger.info("Milvus client initialized", uri=settings.zilliz_cloud_uri)
    return _client


def ensure_contracts_collection():
    client = get_milvus_client()
    collection_name = settings.contracts_collection

    if client.has_collection(collection_name):
        logger.info("Contracts collection already exists", collection=collection_name)
        return

    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("id", DataType.VARCHAR, max_length=64, is_primary=True)
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
    schema.add_field("contract_id", DataType.VARCHAR, max_length=64)
    schema.add_field("chunk_index", DataType.INT64)
    schema.add_field("page_number", DataType.INT64)
    schema.add_field("text", DataType.VARCHAR, max_length=4096)
    schema.add_field("has_vision_enrichment", DataType.BOOL)
    schema.add_field("clause_type", DataType.VARCHAR, max_length=200)
    schema.add_field("document_type", DataType.VARCHAR, max_length=100)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )
    logger.info("Contracts collection created", collection=collection_name)


def ensure_regulatory_collection():
    client = get_milvus_client()
    collection_name = settings.regulatory_collection

    if client.has_collection(collection_name):
        return

    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("id", DataType.VARCHAR, max_length=64, is_primary=True)
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
    schema.add_field("regulatory_doc_id", DataType.VARCHAR, max_length=64)
    schema.add_field("source_name", DataType.VARCHAR, max_length=200)
    schema.add_field("chunk_index", DataType.INT64)
    schema.add_field("text", DataType.VARCHAR, max_length=4096)
    schema.add_field("document_date", DataType.VARCHAR, max_length=50)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )
    logger.info("Regulatory collection created", collection=collection_name)


def ensure_cache_collection():
    client = get_milvus_client()
    collection_name = settings.cache_collection

    if client.has_collection(collection_name):
        return

    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("id", DataType.VARCHAR, max_length=64, is_primary=True)
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
    schema.add_field("query_text", DataType.VARCHAR, max_length=2000)
    schema.add_field("response_json", DataType.VARCHAR, max_length=8192)
    schema.add_field("created_at", DataType.VARCHAR, max_length=50)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )
    logger.info("Cache collection created", collection=collection_name)


def upsert_contract_chunks(chunks: List[Dict[str, Any]]):
    client = get_milvus_client()
    ensure_contracts_collection()
    if chunks:
        client.upsert(collection_name=settings.contracts_collection, data=chunks)
        logger.info("Upserted contract chunks", count=len(chunks))


def upsert_regulatory_chunks(chunks: List[Dict[str, Any]]):
    client = get_milvus_client()
    ensure_regulatory_collection()
    if chunks:
        client.upsert(collection_name=settings.regulatory_collection, data=chunks)
        logger.info("Upserted regulatory chunks", count=len(chunks))


def search_contracts(
    query_embedding: List[float],
    top_k: int = 10,
    filter_expr: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = get_milvus_client()
    ensure_contracts_collection()
    _t0 = _time.time() * 1000
    results = client.search(
        collection_name=settings.contracts_collection,
        data=[query_embedding],
        limit=top_k,
        filter=filter_expr,
        output_fields=["contract_id", "chunk_index", "page_number", "text",
                       "has_vision_enrichment", "clause_type", "document_type"],
    )
    hits = results[0] if results else []
    metrics.milvus_search_executed(settings.contracts_collection, top_k, _time.time()*1000 - _t0, len(hits))
    return hits


def search_regulatory(
    query_embedding: List[float],
    top_k: int = 10,
    filter_expr: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = get_milvus_client()
    ensure_regulatory_collection()
    results = client.search(
        collection_name=settings.regulatory_collection,
        data=[query_embedding],
        limit=top_k,
        filter=filter_expr,
        output_fields=["regulatory_doc_id", "source_name", "chunk_index", "text", "document_date"],
    )
    return results[0] if results else []


def check_semantic_cache(
    query_embedding: List[float],
    threshold: float = None,
) -> Optional[Dict[str, Any]]:
    client = get_milvus_client()
    ensure_cache_collection()
    threshold = threshold or settings.cache_similarity_threshold
    results = client.search(
        collection_name=settings.cache_collection,
        data=[query_embedding],
        limit=1,
        output_fields=["query_text", "response_json", "created_at"],
    )
    if results and results[0]:
        hit = results[0][0]
        if hit.get("distance", 0) >= threshold:
            try:
                return json.loads(hit["entity"]["response_json"])
            except Exception:
                return None
    return None


def store_in_cache(
    cache_id: str,
    query_embedding: List[float],
    query_text: str,
    response: Dict[str, Any],
):
    client = get_milvus_client()
    ensure_cache_collection()
    from datetime import datetime
    client.upsert(
        collection_name=settings.cache_collection,
        data=[{
            "id": cache_id,
            "embedding": query_embedding,
            "query_text": query_text[:2000],
            "response_json": json.dumps(response)[:8192],
            "created_at": datetime.utcnow().isoformat(),
        }]
    )


def delete_contract_chunks(contract_id: str):
    client = get_milvus_client()
    ensure_contracts_collection()
    client.delete(
        collection_name=settings.contracts_collection,
        filter=contract_filter(contract_id),
    )
    logger.info("Deleted contract chunks from Milvus", contract_id=contract_id)


def initialize_all_collections():
    ensure_contracts_collection()
    ensure_regulatory_collection()
    ensure_cache_collection()
    logger.info("All Milvus collections initialized")
