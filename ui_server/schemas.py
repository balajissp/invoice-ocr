from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ui_server.models import InvoiceStatus


class ExtractedDataSchema(BaseModel):
    """Schema for parsed invoice data."""

    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    line_items: Optional[list[Dict[str, Any]]] = None
    notes: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class ExtractionConfidenceSchema(BaseModel):
    """Confidence scores for extracted fields."""

    invoice_number: float = 0.0
    invoice_date: float = 0.0
    due_date: float = 0.0
    vendor_name: float = 0.0
    total_amount: float = 0.0
    model_config = ConfigDict(extra="allow")


class InvoiceUploadResponse(BaseModel):
    """Response after uploading an invoice."""

    invoice_id: UUID
    status: InvoiceStatus
    filename: str
    created_at: datetime
    model_config = ConfigDict(extra="allow")


class InvoiceGetResponse(BaseModel):
    """Response when retrieving an invoice."""

    invoice_id: str
    filename: str
    status: str
    extracted_data: Optional[ExtractedDataSchema] = None
    extraction_confidence: Optional[ExtractionConfidenceSchema] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(extra="allow")


class InvoiceResponse(BaseModel):
    id: UUID
    status: InvoiceStatus
    filename: str
    extracted_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(extra="allow")


class HealthResponse(BaseModel):
    status: str
    database: str
