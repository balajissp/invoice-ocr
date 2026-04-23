import logging
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ui_server.admin import register_admin
from ui_server.config import settings
from ui_server.db import get_db, engine, Base
from ui_server.models import ExtractionLog
from ui_server.models import Invoice, InvoiceStatus
from ui_server.parser import extract_invoice, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from ui_server.schemas import (
    InvoiceUploadResponse,
    InvoiceResponse,
    HealthResponse,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(os.getenv("TMP_DIR", "../.temp"))
UPLOADS_DIR.mkdir(exist_ok=True)


# Startup/shutdown
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup: Create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready")
    yield
    # Shutdown
    logger.info("Database shutting down...")
    engine.dispose()


app = FastAPI(
    title="Invoice Pipeline API",
    description="REST API for invoice processing and extraction",
    version="1.0.0",
    lifespan=lifespan,
)
register_admin(app)


@app.get("/", tags=["Home"])
def home(request: Request):
    base_url = str(request.url).rstrip("/")

    return {
        "message": "Invoice Pipeline API",
        "homepage": base_url,
        "api_docs": base_url + "/docs",
        "api_reference": base_url + "/redoc",
        "database_dashboard": base_url + "/admin",
        "health_check": request.url_for("health"),
    }


# Health check
@app.get("/health", tags=["Health"], response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    # Test DB connection
    db.execute(select(1))
    return HealthResponse(status="healthy", database="connected")


# Upload endpoint
@app.post(
    "/invoices/upload",
    summary="Upload invoice file",
    description="Upload an invoice file (PDF/image/text) for OCR extraction",
    tags=["Invoices"],
    response_model=InvoiceUploadResponse,
)
async def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    logger.info(f"Upload started: {file.filename}")

    # try:
    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {(MAX_FILE_SIZE >> 10) / 1024:.1f}MB)",
        )
    # Create invoice record
    invoice = Invoice(
        filename=file.filename, file_type=file_ext, status=InvoiceStatus.PENDING
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    # Update invoice with saved filename
    invoice.filename = f"{invoice.id}.{invoice.file_type}"
    db.commit()
    db.refresh(invoice)

    # Persist
    (UPLOADS_DIR / f"{invoice.id}.{invoice.file_type}").write_bytes(file_bytes)

    return InvoiceUploadResponse(
        invoice_id=invoice.id,
        filename=invoice.filename,
        status=invoice.status.value,
        extracted_data=invoice.extracted_data,
        extraction_confidence=invoice.extraction_confidence,
        error_message=invoice.error_message,
        created_at=invoice.created_at,
    )


# Get invoice status
@app.get("/invoices/{invoice_id}", tags=["Invoices"], response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """
    Get invoice by ID.
    Returns: parsed extracted_data + status
    """
    invoice: Invoice = (
        db.query(Invoice).filter(Invoice.id == uuid.UUID(invoice_id)).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice not found {invoice_id}")

    if invoice.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]:
        invoice = await extract_invoice(db, invoice)

    return InvoiceResponse(
        id=invoice_id,
        filename=invoice.filename,
        status=invoice.status,
        extracted_data=invoice.extracted_data,
        # extraction_confidence=invoice.extraction_confidence,
        error_message=invoice.error_message,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


@app.get(
    "/invoices/{invoice_id}/logs",
    summary="Get extraction logs",
    description="View detailed extraction workflow logs for debugging",
    tags=["Debug"],
)
async def get_extraction_logs(invoice_id: str, db: Session = Depends(get_db)):
    """
    Get extraction workflow logs for an invoice.
    """

    logs = db.query(ExtractionLog).filter(ExtractionLog.invoice_id == invoice_id).all()
    return {
        "invoice_id": invoice_id,
        "logs": [
            {
                "step": log.step,
                "status": log.status,
                "details": log.details,
                "timestamp": log.timestamp,
            }
            for log in logs
        ],
    }


@app.exception_handler(Exception)
async def debug_exception_handler(_: Request, exc: Exception):
    return Response(
        content="".join(traceback.TracebackException.from_exception(exc).format())
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.fastapi_host, port=settings.fastapi_port)
