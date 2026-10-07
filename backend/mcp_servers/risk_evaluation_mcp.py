"""
Risk Evaluation MCP Server
Exposes contract risk scoring and clause severity classification as MCP tools.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

server = Server("legal-risk-evaluation")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="score_contract_risk",
            description="Return a detailed risk score breakdown for an already-reviewed contract by contract ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_id": {"type": "string", "description": "Contract UUID from the library"},
                },
                "required": ["contract_id"],
            },
        ),
        types.Tool(
            name="classify_clause_severity",
            description="Classify the risk severity of a specific clause text and return detailed reasoning.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clause_text": {"type": "string", "description": "The clause text to classify"},
                    "clause_type": {"type": "string", "description": "Clause type for context", "default": "general"},
                    "contract_type": {"type": "string", "enum": ["saas", "nda", "vendor", "general"], "default": "general"},
                },
                "required": ["clause_text"],
            },
        ),
        types.Tool(
            name="get_negotiation_priorities",
            description="Return negotiation priorities ranked by business impact for a reviewed contract.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_id": {"type": "string", "description": "Contract UUID from the library"},
                },
                "required": ["contract_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "score_contract_risk":
            return await _handle_score_risk(arguments)
        elif name == "classify_clause_severity":
            return await _handle_classify_severity(arguments)
        elif name == "get_negotiation_priorities":
            return await _handle_negotiation_priorities(arguments)
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_score_risk(arguments: dict) -> list[types.TextContent]:
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import ContractReview, Contract, ReviewStatus
    from sqlalchemy import select, desc
    import uuid

    contract_id = arguments["contract_id"]

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
            contract = result.scalar_one_or_none()
        except Exception:
            return [types.TextContent(type="text", text=f"Invalid contract ID: {contract_id}")]

        if not contract:
            return [types.TextContent(type="text", text=f"Contract {contract_id} not found")]

        result = await db.execute(
            select(ContractReview)
            .where(ContractReview.contract_id == uuid.UUID(contract_id))
            .where(ContractReview.review_status == ReviewStatus.COMPLETED)
            .order_by(desc(ContractReview.created_at))
            .limit(1)
        )
        review = result.scalar_one_or_none()

    if not review:
        return [types.TextContent(type="text", text=f"No completed review found for contract {contract_id}. Run /api/contracts/review first.")]

    risk_level = review.overall_risk_level.value if review.overall_risk_level else "unknown"
    output = f"""# Risk Score: {contract.original_filename}

**Overall Risk Score:** {review.overall_risk_score or 'N/A'}/100
**Risk Level:** {risk_level.upper()}
**Total Clauses Found:** {review.total_clauses_found}
**High Risk Clauses:** {review.high_risk_clause_count}
**Critical Clauses:** {review.critical_clause_count}
**Review Confidence:** {review.synthesis_output.get('confidence_score', 'N/A') if review.synthesis_output else 'N/A'}%

## Synthesis Summary
{review.synthesis_output.get('executive_summary', 'No summary available') if review.synthesis_output else 'No review data'}

## Review Metadata
- Models used: {', '.join(review.models_used or [])}
- Review duration: {review.review_duration_seconds:.1f}s
- Total cost: ${review.total_cost_usd:.4f}
- Reviewed at: {review.created_at.isoformat()}
"""
    return [types.TextContent(type="text", text=output)]


async def _handle_classify_severity(arguments: dict) -> list[types.TextContent]:
    from backend.agents.contract_review_agent import RISK_PATTERNS
    from backend.core.config import settings
    import anthropic
    import json

    clause_text = arguments["clause_text"]
    clause_type = arguments.get("clause_type", "general")
    contract_type = arguments.get("contract_type", "general")

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        pattern_context = json.dumps({k: {"risk_level": v["risk_level"], "description": v["description"]} for k, v in RISK_PATTERNS.items()}, indent=2)

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": f"""Classify the risk severity of this contract clause.

Clause Type: {clause_type}
Contract Type: {contract_type}

Clause Text:
{clause_text}

Known Risk Patterns:
{pattern_context[:2000]}

Return:
1. Risk Level: low / medium / high / critical
2. Reasoning: Specific explanation
3. Matched Patterns: Which patterns from the library apply
4. Recommended Action: accept / negotiate / reject / seek_legal_review
5. Suggested Alternative: Better language if applicable""",
            }],
        )
        return [types.TextContent(type="text", text=response.content[0].text)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Classification error: {str(e)}")]


async def _handle_negotiation_priorities(arguments: dict) -> list[types.TextContent]:
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import ContractReview, Contract, ReviewStatus
    from sqlalchemy import select, desc
    import uuid

    contract_id = arguments["contract_id"]

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
            contract = result.scalar_one_or_none()
        except Exception:
            return [types.TextContent(type="text", text="Invalid contract ID")]

        result = await db.execute(
            select(ContractReview)
            .where(ContractReview.contract_id == uuid.UUID(contract_id))
            .where(ContractReview.review_status == ReviewStatus.COMPLETED)
            .order_by(desc(ContractReview.created_at))
            .limit(1)
        )
        review = result.scalar_one_or_none()

    if not review:
        return [types.TextContent(type="text", text="No completed review found for this contract.")]

    priorities = review.negotiation_priorities or []
    synthesis = review.synthesis_output or {}
    deal_breakers = synthesis.get("deal_breakers", [])
    top_issues = synthesis.get("top_5_issues", [])

    output = f"# Negotiation Priorities: {contract.original_filename if contract else contract_id}\n\n"

    if deal_breakers:
        output += "## ⛔ Non-Negotiable — Must Change Before Signing\n"
        for item in deal_breakers:
            output += f"- {item}\n"
        output += "\n"

    output += "## 📋 Negotiation Priority Order\n"
    for i, priority in enumerate(priorities, 1):
        output += f"{i}. {priority}\n"

    if top_issues:
        output += "\n## 🔍 Detailed Issue Breakdown\n"
        for issue in top_issues[:5]:
            output += f"\n**{issue.get('issue_title', 'Issue')}** [{issue.get('severity', 'medium').upper()}]\n"
            output += f"{issue.get('description', '')}\n"
            if issue.get("recommended_action"):
                output += f"*Action: {issue['recommended_action']}*\n"

    return [types.TextContent(type="text", text=output)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="legal-risk-evaluation",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
