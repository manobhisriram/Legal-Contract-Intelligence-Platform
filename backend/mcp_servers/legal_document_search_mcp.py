"""
Legal Document Search MCP Server
Exposes contract library search as MCP tools.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

server = Server("legal-document-search")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_contract_library",
            description="Semantic search across all indexed contracts. Supports natural language queries and returns the most relevant clause excerpts with contract references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "top_k": {"type": "integer", "description": "Number of results to return", "default": 5},
                    "contract_id": {"type": "string", "description": "Optional: restrict search to a specific contract", "default": ""},
                    "risk_filter": {"type": "string", "enum": ["all", "critical", "high", "medium", "low"], "default": "all"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="find_similar_clauses",
            description="Given a clause text, find semantically similar clauses across all contracts in the library. Useful for precedent analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clause_text": {"type": "string", "description": "Clause text to find similar matches for"},
                    "clause_type": {"type": "string", "description": "Optional clause type filter", "default": ""},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["clause_text"],
            },
        ),
        types.Tool(
            name="get_clause_history",
            description="Show how a specific clause type has appeared across all contracts — useful for pattern analysis and risk trending.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clause_type": {"type": "string", "description": "Type of clause to analyze (e.g., 'liability_cap', 'data_rights', 'auto_renewal')"},
                },
                "required": ["clause_type"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "search_contract_library":
            return await _handle_search(arguments)
        elif name == "find_similar_clauses":
            return await _handle_find_similar(arguments)
        elif name == "get_clause_history":
            return await _handle_clause_history(arguments)
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_search(arguments: dict) -> list[types.TextContent]:
    from backend.services.embedding_service import get_single_embedding, rewrite_query_for_search, rerank_chunks
    from backend.db.milvus_client import search_contracts, contract_filter

    query = arguments["query"]
    top_k = arguments.get("top_k", 5)
    contract_id = arguments.get("contract_id", "")

    rewritten = await rewrite_query_for_search(query)
    embedding = await get_single_embedding(rewritten)

    filter_expr = contract_filter(contract_id) if contract_id else None
    hits = search_contracts(embedding, top_k=top_k * 2, filter_expr=filter_expr)
    reranked = rerank_chunks(rewritten, hits, top_k=top_k)

    output = f"# Search Results for: {query}\n*Rewritten query: {rewritten}*\n\n"
    for i, hit in enumerate(reranked, 1):
        entity = hit.get("entity", hit)
        output += f"**Result {i}** (Relevance: {hit.get('rerank_score', hit.get('distance', 0)):.2f})\n"
        output += f"Contract ID: `{entity.get('contract_id', 'unknown')[:8]}...` | Page: {entity.get('page_number', '?')}\n"
        if entity.get("has_vision_enrichment"):
            output += "👁️ *Vision-enriched chunk*\n"
        output += f"{entity.get('text', '')[:400]}...\n\n"

    return [types.TextContent(type="text", text=output)]


async def _handle_find_similar(arguments: dict) -> list[types.TextContent]:
    from backend.services.embedding_service import get_single_embedding, rerank_chunks
    from backend.db.milvus_client import search_contracts

    clause_text = arguments["clause_text"]
    top_k = arguments.get("top_k", 5)

    embedding = await get_single_embedding(clause_text)
    hits = search_contracts(embedding, top_k=top_k * 2)
    reranked = rerank_chunks(clause_text, hits, top_k=top_k)

    output = f"# Similar Clauses Found ({len(reranked)} results)\n\n"
    for i, hit in enumerate(reranked, 1):
        entity = hit.get("entity", hit)
        output += f"**Match {i}** — Contract `{entity.get('contract_id', 'unknown')[:8]}...` Page {entity.get('page_number', '?')}\n"
        output += f"Similarity: {hit.get('rerank_score', 0):.2f}\n"
        output += f"{entity.get('text', '')[:300]}...\n\n"

    return [types.TextContent(type="text", text=output)]


async def _handle_clause_history(arguments: dict) -> list[types.TextContent]:
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import ExtractedClause
    from sqlalchemy import select, func

    clause_type = arguments["clause_type"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                ExtractedClause.risk_level,
                func.count(ExtractedClause.id)
            )
            .where(ExtractedClause.clause_type.ilike(f"%{clause_type}%"))
            .group_by(ExtractedClause.risk_level)
        )
        risk_distribution = dict(result.all())

        result2 = await db.execute(
            select(func.count(ExtractedClause.id))
            .where(ExtractedClause.clause_type.ilike(f"%{clause_type}%"))
        )
        total = result2.scalar()

    output = f"# Clause History: {clause_type}\n\n"
    output += f"**Total occurrences across all contracts:** {total}\n\n"
    output += "**Risk Distribution:**\n"
    for level, count in risk_distribution.items():
        level_str = level.value if hasattr(level, 'value') else str(level)
        output += f"- {level_str.upper()}: {count} contracts\n"

    return [types.TextContent(type="text", text=output)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="legal-document-search",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
