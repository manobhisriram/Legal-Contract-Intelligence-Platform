"""Each MCP server must complete a real stdio handshake and advertise its tools."""
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_TOOLS = {
    "contract_intelligence_mcp": {
        "review_contract", "extract_clauses", "flag_risky_clauses",
        "compare_to_template", "generate_redline_suggestions", "get_negotiation_priorities",
    },
    "regulatory_intelligence_mcp": {
        "get_recent_regulatory_changes", "check_contract_compliance", "get_affected_contracts",
        "subscribe_to_regulatory_source", "get_compliance_report",
    },
    "legal_document_search_mcp": {"search_contract_library", "find_similar_clauses", "get_clause_history"},
    "risk_evaluation_mcp": {"score_contract_risk", "classify_clause_severity", "get_negotiation_priorities"},
}


@pytest.mark.parametrize("module", sorted(EXPECTED_TOOLS))
async def test_server_handshake_and_tool_listing(module):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", f"backend.mcp_servers.{module}"],
        cwd=str(ROOT),
        env={
            **os.environ,
            "PYTHONPATH": str(ROOT),
            "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
            "DD_TRACE_ENABLED": "false",
        },
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
    assert {t.name for t in tools.tools} == EXPECTED_TOOLS[module]
