"""Initial schema — all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-06-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enums ---
    risklevel_enum = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="risklevel", create_type=False
    )
    risklevel_enum.create(op.get_bind(), checkfirst=True)

    reviewstatus_enum = postgresql.ENUM(
        "pending", "in_progress", "completed", "failed",
        name="reviewstatus", create_type=False
    )
    reviewstatus_enum.create(op.get_bind(), checkfirst=True)

    governanceaction_enum = postgresql.ENUM(
        "approved", "rejected", "escalated",
        name="governanceaction", create_type=False
    )
    governanceaction_enum.create(op.get_bind(), checkfirst=True)

    # --- contracts ---
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("contract_type", sa.String(100), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("has_vision_processing", sa.Boolean(), nullable=True, default=False),
        sa.Column("upload_status", sa.String(50), nullable=True, default="processing"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contracts_created_at", "contracts", ["created_at"])
    op.create_index("ix_contracts_contract_type", "contracts", ["contract_type"])

    # --- extracted_clauses ---
    op.create_table(
        "extracted_clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clause_type", sa.String(200), nullable=False),
        sa.Column("clause_text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.Enum("low", "medium", "high", "critical", name="risklevel"), nullable=False),
        sa.Column("risk_reasoning", sa.Text(), nullable=True),
        sa.Column("deviation_from_standard", sa.Text(), nullable=True),
        sa.Column("suggested_redline", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("extracted_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extracted_clauses_contract_id", "extracted_clauses", ["contract_id"])
    op.create_index("ix_extracted_clauses_risk_level", "extracted_clauses", ["risk_level"])
    op.create_index("ix_extracted_clauses_clause_type", "extracted_clauses", ["clause_type"])

    # --- contract_reviews ---
    op.create_table(
        "contract_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_status", sa.Enum("pending", "in_progress", "completed", "failed", name="reviewstatus"), nullable=True),
        sa.Column("overall_risk_score", sa.Float(), nullable=True),
        sa.Column("overall_risk_level", sa.Enum("low", "medium", "high", "critical", name="risklevel"), nullable=True),
        sa.Column("total_clauses_found", sa.Integer(), nullable=True, default=0),
        sa.Column("high_risk_clause_count", sa.Integer(), nullable=True, default=0),
        sa.Column("critical_clause_count", sa.Integer(), nullable=True, default=0),
        sa.Column("extractor_output", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_analyst_output", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("comparator_output", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("synthesis_output", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("negotiation_priorities", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("review_duration_seconds", sa.Float(), nullable=True),
        sa.Column("total_tokens_used", sa.Integer(), nullable=True, default=0),
        sa.Column("total_cost_usd", sa.Float(), nullable=True, default=0.0),
        sa.Column("models_used", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contract_reviews_contract_id", "contract_reviews", ["contract_id"])
    op.create_index("ix_contract_reviews_review_status", "contract_reviews", ["review_status"])
    op.create_index("ix_contract_reviews_created_at", "contract_reviews", ["created_at"])

    # --- regulatory_documents ---
    op.create_table(
        "regulatory_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("document_title", sa.String(500), nullable=True),
        sa.Column("document_date", sa.DateTime(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=True, default=0),
        sa.Column("has_changes_from_previous", sa.Boolean(), nullable=True, default=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulatory_documents_source_url", "regulatory_documents", ["source_url"])
    op.create_index("ix_regulatory_documents_created_at", "regulatory_documents", ["created_at"])

    # --- regulatory_impacts ---
    op.create_table(
        "regulatory_impacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("regulatory_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("affected_clause_type", sa.String(200), nullable=True),
        sa.Column("impact_description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Enum("low", "medium", "high", "critical", name="risklevel"), nullable=False),
        sa.Column("compliance_gap", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["regulatory_document_id"], ["regulatory_documents.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulatory_impacts_contract_id", "regulatory_impacts", ["contract_id"])
    op.create_index("ix_regulatory_impacts_regulatory_document_id", "regulatory_impacts", ["regulatory_document_id"])

    # --- governance_records ---
    op.create_table(
        "governance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Enum("approved", "rejected", "escalated", name="governanceaction"), nullable=False),
        sa.Column("reviewer_id", sa.String(200), nullable=True),
        sa.Column("reviewer_name", sa.String(200), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["review_id"], ["contract_reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_governance_records_review_id", "governance_records", ["review_id"])
    op.create_index("ix_governance_records_created_at", "governance_records", ["created_at"])

    # --- evaluation_runs ---
    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_name", sa.String(200), nullable=False),
        sa.Column("total_contracts_evaluated", sa.Integer(), nullable=True, default=0),
        sa.Column("correctness_score", sa.Float(), nullable=True),
        sa.Column("severity_calibration_score", sa.Float(), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("actionability_score", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("results_detail", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_runs_created_at", "evaluation_runs", ["created_at"])

    # --- red_team_runs ---
    op.create_table(
        "red_team_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_name", sa.String(200), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=True, default=1),
        sa.Column("total_adversarial_contracts", sa.Integer(), nullable=True, default=0),
        sa.Column("failure_rate_before", sa.Float(), nullable=True),
        sa.Column("failure_rate_after", sa.Float(), nullable=True),
        sa.Column("attack_category_results", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("patches_applied", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_red_team_runs_created_at", "red_team_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("red_team_runs")
    op.drop_table("evaluation_runs")
    op.drop_table("governance_records")
    op.drop_table("regulatory_impacts")
    op.drop_table("regulatory_documents")
    op.drop_table("contract_reviews")
    op.drop_table("extracted_clauses")
    op.drop_table("contracts")

    op.execute("DROP TYPE IF EXISTS governanceaction")
    op.execute("DROP TYPE IF EXISTS reviewstatus")
    op.execute("DROP TYPE IF EXISTS risklevel")
