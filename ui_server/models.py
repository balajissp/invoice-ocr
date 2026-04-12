import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Enum, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ui_server.db import Base


class InvoiceStatus(str, PyEnum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


def utcnow():
    return datetime.now(timezone.utc)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(String, nullable=True, unique=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    file_type = Column(String(10), nullable=True)
    status = Column(Enum(InvoiceStatus, native_enum=True), default=InvoiceStatus.PENDING)
    extracted_data = Column(JSONB, nullable=True)  # Flexible schema
    error_message = Column(Text, nullable=True)
    raw_ocr_output = Column(Text, nullable=True)
    extraction_confidence = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    logs = relationship(
        "ExtractionLog", back_populates="invoice", cascade="all, delete-orphan"
    )


class ExtractionLog(Base):
    __tablename__ = "extraction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    step = Column(String, nullable=False)  # e.g., "ocr", "validation", "persist"
    result = Column(Text, nullable=True)  # JSON or text result
    created_at = Column(DateTime(timezone=True), default=utcnow)

    invoice = relationship("Invoice", back_populates="logs")
