from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from ui_server.models import InvoiceStatus


class InvoiceUploadResponse(BaseModel):
    invoice_id: UUID
    status: InvoiceStatus
    message: str = "Invoice uploaded, processing started"


class InvoiceResponse(BaseModel):
    id: UUID
    status: InvoiceStatus
    original_filename: str
    extracted_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy -> Pydantic


class HealthResponse(BaseModel):
    status: str
    database: str
