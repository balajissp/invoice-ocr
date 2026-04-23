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
from ui_server.config import (
    settings,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    construct_file_path,
)
from ui_server.db import get_db, engine, Base
from ui_server.models import ExtractionLog
from ui_server.models import Invoice, InvoiceStatus
from ui_server.parser import (
    extract_text_from_file,
    parse_text,
)
from ui_server.schemas import (
    InvoiceUploadResponse,
    InvoiceResponse,
    HealthResponse,
)
from fastapi import BackgroundTasks

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


@app.exception_handler(Exception)
async def debug_exception_handler(_: Request, exc: Exception):
    return Response(
        content="".join(traceback.TracebackException.from_exception(exc).format())
    )


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
async def health(db: Session = Depends(get_db)):
    # Test DB connection
    db.execute(select(1))
    return HealthResponse(status="healthy", database="connected")


def simple_chained_task(invoice_id: str, file_type: str, db: Session):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    invoice.status = InvoiceStatus.EXTRACTING
    db.commit()
    db.refresh(invoice)
    workflow_input = str(construct_file_path(invoice_id, file_type))
    raw_text = extract_text_from_file(workflow_input)
    data, confidence = parse_text(raw_text)

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    invoice.status = InvoiceStatus.COMPLETED
    invoice.raw_ocr_output = raw_text
    invoice.extracted_data = data.model_dump()
    invoice.extraction_confidence = confidence.model_dump()
    db.commit()
    db.refresh(invoice)


# Upload endpoint
@app.post(
    "/invoices/upload",
    summary="Upload invoice file",
    description="Upload an invoice file (PDF/image/text) for OCR extraction",
    tags=["Invoices"],
    response_model=InvoiceUploadResponse,
    status_code=202,
)
async def upload_invoice(
    bg_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    logger.info(f"Upload started: {file.filename}")

    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower()
    if f".{file_ext}" not in ALLOWED_EXTENSIONS:
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
    file_path = construct_file_path(invoice.id, invoice.file_type)
    invoice.filename = file_path.name
    db.commit()
    db.refresh(invoice)

    # Persist
    file_path.write_bytes(file_bytes)
    # add background task
    bg_tasks.add_task(simple_chained_task, invoice.id, invoice.file_type, db)

    return InvoiceUploadResponse(
        invoice_id=invoice.id,
        filename=invoice.filename,
        status=invoice.status.value,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.fastapi_host, port=settings.fastapi_port)
