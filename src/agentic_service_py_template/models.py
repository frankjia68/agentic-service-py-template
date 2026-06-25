from pydantic import BaseModel as PydanticBase
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
)
from sqlalchemy.orm import DeclarativeBase


# ─── SQLAlchemy ORM Models ───────────────────────────────────────

class Base(DeclarativeBase):
    pass


class AiObservabilityLog(Base):
    __tablename__ = "ai_observability_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_name = Column(String(128), nullable=True, index=True)
    request = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    user_id = Column(String(64), nullable=True)
    requested_at_utc = Column(DateTime, nullable=True)
    responded_at_utc = Column(DateTime, nullable=True)
    llm_session_id = Column(String(128), nullable=True)
    llm_audit_entry_id = Column(String(128), nullable=True)
    correlation_id = Column(String(36), nullable=True, index=True)


class RequestLog(Base):
    __tablename__ = "request_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(36), nullable=False, index=True)
    endpoint = Column(String(256), nullable=True)
    method = Column(String(8), nullable=True)
    protocol = Column(String(8), nullable=True)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    user_id = Column(String(64), nullable=True)
    requested_at_utc = Column(DateTime, nullable=True)


# ─── Pydantic Models ───────────────────────────────────────────────

class InvestmentSummary(PydanticBase):
    summary_highlights: list[str] = []
    risk_factors: list[str] = []
    investment_profile: str = ""
