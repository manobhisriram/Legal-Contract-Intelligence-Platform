from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean,
    DateTime, JSON, Enum as SAEnum, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum


class Base(DeclarativeBase):
    pass


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class GovernanceAction(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    contract_type = Column(String(100), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    has_vision_processing = Column(Boolean, default=False)
    upload_status = Column(String(50), default="processing")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reviews = relationship("ContractReview", back_populates="contract", cascade="all, delete-orphan")
    clauses = relationship("ExtractedClause", back_populates="contract", cascade="all, delete-orphan")
    regulatory_impacts = relationship("RegulatoryImpact", back_populates="contract")

    __table_args__ = (
        Index("ix_contracts_created_at", "created_at"),
        Index("ix_contracts_contract_type", "contract_type"),
    )


class ExtractedClause(Base):
    __tablename__ = "extracted_clauses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    clause_type = Column(String(200), nullable=False)
    clause_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    risk_level = Column(SAEnum(RiskLevel), nullable=False, default=RiskLevel.LOW)
    risk_reasoning = Column(Text, nullable=True)
    deviation_from_standard = Column(Text, nullable=True)
    suggested_redline = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    extracted_by = Column(String(100), default="extractor_agent")
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="clauses")

    __table_args__ = (
        Index("ix_extracted_clauses_contract_id", "contract_id"),
        Index("ix_extracted_clauses_risk_level", "risk_level"),
        Index("ix_extracted_clauses_clause_type", "clause_type"),
    )


class ContractReview(Base):
    __tablename__ = "contract_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    review_status = Column(SAEnum(ReviewStatus), default=ReviewStatus.PENDING)
    overall_risk_score = Column(Float, nullable=True)
    overall_risk_level = Column(SAEnum(RiskLevel), nullable=True)
    total_clauses_found = Column(Integer, default=0)
    high_risk_clause_count = Column(Integer, default=0)
    critical_clause_count = Column(Integer, default=0)
    extractor_output = Column(JSON, nullable=True)
    risk_analyst_output = Column(JSON, nullable=True)
    comparator_output = Column(JSON, nullable=True)
    synthesis_output = Column(JSON, nullable=True)
    negotiation_priorities = Column(JSON, nullable=True)
    review_duration_seconds = Column(Float, nullable=True)
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    models_used = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    contract = relationship("Contract", back_populates="reviews")
    governance_records = relationship("GovernanceRecord", back_populates="review")

    __table_args__ = (
        Index("ix_contract_reviews_contract_id", "contract_id"),
        Index("ix_contract_reviews_review_status", "review_status"),
        Index("ix_contract_reviews_created_at", "created_at"),
    )


class RegulatoryDocument(Base):
    __tablename__ = "regulatory_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(String(1000), nullable=False)
    source_name = Column(String(200), nullable=False)
    document_title = Column(String(500), nullable=True)
    document_date = Column(DateTime, nullable=True)
    content_hash = Column(String(64), nullable=False)
    chunk_count = Column(Integer, default=0)
    has_changes_from_previous = Column(Boolean, default=False)
    change_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    impacts = relationship("RegulatoryImpact", back_populates="regulatory_document")

    __table_args__ = (
        Index("ix_regulatory_documents_source_url", "source_url"),
        Index("ix_regulatory_documents_created_at", "created_at"),
    )


class RegulatoryImpact(Base):
    __tablename__ = "regulatory_impacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulatory_document_id = Column(UUID(as_uuid=True), ForeignKey("regulatory_documents.id"), nullable=False)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    affected_clause_type = Column(String(200), nullable=True)
    impact_description = Column(Text, nullable=False)
    severity = Column(SAEnum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    compliance_gap = Column(Text, nullable=True)
    recommended_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    regulatory_document = relationship("RegulatoryDocument", back_populates="impacts")
    contract = relationship("Contract", back_populates="regulatory_impacts")

    __table_args__ = (
        Index("ix_regulatory_impacts_contract_id", "contract_id"),
        Index("ix_regulatory_impacts_regulatory_document_id", "regulatory_document_id"),
    )


class GovernanceRecord(Base):
    __tablename__ = "governance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("contract_reviews.id"), nullable=True)
    action = Column(SAEnum(GovernanceAction), nullable=False)
    reviewer_id = Column(String(200), nullable=True)
    reviewer_name = Column(String(200), nullable=True)
    reason = Column(Text, nullable=True)
    # Attribute is renamed because "metadata" is reserved by SQLAlchemy Declarative;
    # the database column keeps its original name.
    extra_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("ContractReview", back_populates="governance_records")

    __table_args__ = (
        Index("ix_governance_records_review_id", "review_id"),
        Index("ix_governance_records_created_at", "created_at"),
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_name = Column(String(200), nullable=False)
    total_contracts_evaluated = Column(Integer, default=0)
    correctness_score = Column(Float, nullable=True)
    severity_calibration_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    actionability_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    results_detail = Column(JSON, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_evaluation_runs_created_at", "created_at"),
    )


class RedTeamRun(Base):
    __tablename__ = "red_team_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_name = Column(String(200), nullable=False)
    iteration_number = Column(Integer, default=1)
    total_adversarial_contracts = Column(Integer, default=0)
    failure_rate_before = Column(Float, nullable=True)
    failure_rate_after = Column(Float, nullable=True)
    attack_category_results = Column(JSON, nullable=True)
    patches_applied = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_red_team_runs_created_at", "created_at"),
    )
