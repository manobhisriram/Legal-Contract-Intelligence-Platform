"""
Contract Intelligence MCP Server
Exposes contract review, clause extraction, and risk analysis as MCP tools.
Any developer connects this server to Claude Desktop and gets contract intelligence as native capabilities.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

from backend.core.config import settings

server = Server("legal-contract-intelligence")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="review_contract",
            description="Perform a complete AI-powered review of a legal contract. Uses 4 specialized agents (Extractor, Risk Analyst, Comparator, Synthesis) across Claude, GPT-4o, and Gemini to identify risky clauses, compare against standard templates, and produce a structured risk report with severity classifications.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_text": {
                        "type": "string",
                        "description": "Full text of the contract to review",
                    },
                    "contract_type": {
                        "type": "string",
                        "enum": ["saas", "nda", "vendor", "employment", "general"],
                        "description": "Type of contract for template comparison",
                        "default": "general",
                    },
                    "contract_filename": {
                        "type": "string",
                        "description": "Original filename for reference",
                        "default": "contract.pdf",
                    },
                },
                "required": ["contract_text"],
            },
        ),
        types.Tool(
            name="extract_clauses",
            description="Extract and categorize all clauses from a contract document without full risk analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_text": {
                        "type": "string",
                        "description": "Contract text to extract clauses from",
                    },
                },
                "required": ["contract_text"],
            },
        ),
        types.Tool(
            name="flag_risky_clauses",
            description="Return only HIGH and CRITICAL risk clauses from a contract, ideal for quick risk screening.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_text": {"type": "string", "description": "Contract text to analyze"},
                    "contract_type": {
                        "type": "string",
                        "enum": ["saas", "nda", "vendor", "general"],
                        "default": "general",
                    },
                },
                "required": ["contract_text"],
            },
        ),
        types.Tool(
            name="compare_to_template",
            description="Compare a contract against your standard template for the given contract type and identify all deviations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_text": {"type": "string", "description": "Contract text to compare"},
                    "contract_type": {
                        "type": "string",
                        "enum": ["saas", "nda", "vendor"],
                        "description": "Contract type for template selection",
                    },
                },
                "required": ["contract_text", "contract_type"],
            },
        ),
        types.Tool(
            name="generate_redline_suggestions",
            description="For a specific risky clause, generate professionally worded alternative language that protects your interests.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clause_text": {"type": "string", "description": "The risky clause text"},
                    "clause_type": {"type": "string", "description": "Type of clause (e.g., 'liability_cap', 'data_rights')"},
                    "risk_description": {"type": "string", "description": "Why this clause is risky"},
                },
                "required": ["clause_text", "clause_type"],
            },
        ),
        types.Tool(
            name="get_negotiation_priorities",
            description="Given a list of contract issues, return them ranked by negotiation priority with recommended strategies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_text": {"type": "string", "description": "Contract text to analyze"},
                    "company_context": {
                        "type": "string",
                        "description": "Brief context about your company (size, industry, risk tolerance)",
                        "default": "",
                    },
                },
                "required": ["contract_text"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "review_contract":
            return await _handle_review_contract(arguments)
        elif name == "extract_clauses":
            return await _handle_extract_clauses(arguments)
        elif name == "flag_risky_clauses":
            return await _handle_flag_risky_clauses(arguments)
        elif name == "compare_to_template":
            return await _handle_compare_to_template(arguments)
        elif name == "generate_redline_suggestions":
            return await _handle_generate_redlines(arguments)
        elif name == "get_negotiation_priorities":
            return await _handle_negotiation_priorities(arguments)
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing {name}: {str(e)}")]


async def _handle_review_contract(arguments: dict) -> list[types.TextContent]:
    from backend.agents.contract_review_agent import run_full_contract_review
    import uuid

    contract_id = str(uuid.uuid4())
    result = await run_full_contract_review(
        contract_text=arguments["contract_text"],
        contract_id=contract_id,
        contract_filename=arguments.get("contract_filename", "mcp_contract.pdf"),
        contract_type=arguments.get("contract_type", "general"),
    )

    summary = f"""# Contract Review Report

**Overall Risk Level:** {result.get('overall_risk_level', 'unknown').upper()}
**Risk Score:** {result.get('overall_risk_score', 0)}/100
**Confidence:** {result.get('confidence_score', 0)}%

## Executive Summary
{result.get('executive_summary', 'No summary available')}

## Risk Breakdown
- Critical issues: {result.get('risk_counts', {}).get('critical', 0)}
- High risk: {result.get('risk_counts', {}).get('high', 0)}
- Medium risk: {result.get('risk_counts', {}).get('medium', 0)}
- Low risk: {result.get('risk_counts', {}).get('low', 0)}

## Top 5 Issues
"""
    for i, issue in enumerate(result.get("top_5_issues", [])[:5], 1):
        summary += f"\n{i}. **{issue.get('issue_title', 'Issue')}** [{issue.get('severity', 'medium').upper()}]\n"
        summary += f"   {issue.get('description', '')}\n"
        if issue.get("suggested_redline"):
            summary += f"   *Suggested redline:* {issue['suggested_redline'][:200]}\n"

    if result.get("deal_breakers"):
        summary += "\n## ⚠️ Deal Breakers\n"
        for db in result.get("deal_breakers", []):
            summary += f"- {db}\n"

    summary += "\n## Negotiation Priorities\n"
    for priority in result.get("negotiation_priorities", [])[:5]:
        summary += f"- {priority}\n"

    summary += f"\n---\n*Review took {result.get('review_duration_seconds', 0):.1f}s | {result.get('total_tokens_used', 0):,} tokens | Models: {', '.join(result.get('models_used', []))}*"

    return [types.TextContent(type="text", text=summary)]


async def _handle_extract_clauses(arguments: dict) -> list[types.TextContent]:
    from backend.agents.contract_review_agent import run_extractor_agent
    result = run_extractor_agent(arguments["contract_text"])
    clauses = result.get("clauses", [])
    output = f"# Extracted Clauses ({len(clauses)} found)\n\n"
    for clause in clauses:
        output += f"**{clause.get('clause_type', 'Unknown')}**\n"
        output += f"{clause.get('clause_text', '')[:300]}...\n\n"
    return [types.TextContent(type="text", text=output)]


async def _handle_flag_risky_clauses(arguments: dict) -> list[types.TextContent]:
    from backend.agents.contract_review_agent import run_extractor_agent, run_risk_analyst_agent
    extractor = run_extractor_agent(arguments["contract_text"])
    clauses = extractor.get("clauses", [])
    risk_result = run_risk_analyst_agent(clauses)
    assessments = risk_result.get("risk_assessments", [])

    risky = [a for a in assessments if a.get("risk_level", "low") in ["high", "critical"]]
    output = f"# High & Critical Risk Clauses ({len(risky)} found)\n\n"
    for clause in risky:
        output += f"**[{clause.get('risk_level', '').upper()}] {clause.get('clause_type', 'Unknown')}**\n"
        output += f"{clause.get('risk_reasoning', '')}\n\n"
    return [types.TextContent(type="text", text=output)]


async def _handle_compare_to_template(arguments: dict) -> list[types.TextContent]:
    from backend.agents.contract_review_agent import run_extractor_agent, run_comparator_agent
    extractor = run_extractor_agent(arguments["contract_text"])
    clauses = extractor.get("clauses", [])
    result = run_comparator_agent(clauses, arguments["contract_type"])
    deviations = result.get("deviations", [])
    output = f"# Template Comparison ({len(deviations)} deviations)\n\n"
    for dev in deviations:
        output += f"**{dev.get('clause_type', 'Unknown')}** [{dev.get('severity', 'moderate').upper()}]\n"
        output += f"Standard: {dev.get('standard_says', '')}\n"
        output += f"Contract: {dev.get('contract_says', '')}\n"
        output += f"Action: {dev.get('recommended_action', 'review')}\n\n"
    return [types.TextContent(type="text", text=output)]


async def _handle_generate_redlines(arguments: dict) -> list[types.TextContent]:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""As a senior legal counsel, provide professionally worded alternative language for this risky contract clause.

Clause Type: {arguments.get('clause_type', 'general')}
Risk Description: {arguments.get('risk_description', 'Unfavorable terms')}

Original Clause:
{arguments['clause_text']}

Provide:
1. Why this is risky (1-2 sentences)
2. Suggested replacement language that protects both parties
3. What this change achieves""",
        }],
    )
    return [types.TextContent(type="text", text=response.content[0].text)]


async def _handle_negotiation_priorities(arguments: dict) -> list[types.TextContent]:
    from backend.agents.contract_review_agent import run_full_contract_review
    import uuid
    result = await run_full_contract_review(
        contract_text=arguments["contract_text"],
        contract_id=str(uuid.uuid4()),
        contract_filename="negotiation_analysis.pdf",
        contract_type="general",
    )
    priorities = result.get("negotiation_priorities", [])
    context = arguments.get("company_context", "")
    output = "# Negotiation Priorities\n\n"
    if context:
        output += f"*Context: {context}*\n\n"
    for i, priority in enumerate(priorities, 1):
        output += f"{i}. {priority}\n"
    if result.get("deal_breakers"):
        output += "\n## Must-Fix Before Signing\n"
        for db in result.get("deal_breakers", []):
            output += f"- {db}\n"
    return [types.TextContent(type="text", text=output)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="legal-contract-intelligence",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
