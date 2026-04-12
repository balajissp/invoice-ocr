from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

from ui_server.config import settings
from ui_server.db import get_db, engine, Base
from ui_server.models import Invoice, InvoiceStatus
from ui_server.schemas import InvoiceUploadResponse, InvoiceResponse, HealthResponse
import logging

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
    logger.info("✓ Database ready")
    yield
    # Shutdown
    logger.info("Shutting down...")
    engine.dispose()


app = FastAPI(
    title="Invoice Pipeline API",
    description="REST API for invoice processing and extraction",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc (alternative)
    openapi_url="/openapi.json",  # OpenAPI schema
    lifespan=lifespan,
)


# Health check
@app.get("/health", tags=["Health"], response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    try:
        # Test DB connection
        db.execute(select(1))
        return HealthResponse(status="healthy", database="connected")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unreachable")


# Upload endpoint
@app.post(
    "/invoices/upload",
    summary="Upload invoice file",
    description="Upload an invoice file (PDF/image/text) for processing",
    tags=["Invoices"],
    response_model=InvoiceUploadResponse,
)
def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    logger.info(f"Upload started: {file.filename}")

    try:
        # Read file content
        content = file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")

        # Create invoice record
        invoice = Invoice(original_filename=file.filename, status=InvoiceStatus.PENDING)
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        logger.info(f"✓ Invoice created: {invoice.id}")

        return InvoiceUploadResponse(invoice_id=invoice.id, status=invoice.status)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Get invoice status
@app.get("/invoices/{invoice_id}", tags=["Invoices"], response_model=InvoiceResponse)
def get_invoice(invoice_id: UUID, db: Session = Depends(get_db)):
    stmt = select(Invoice).where(Invoice.id == invoice_id)
    result = db.execute(stmt)
    invoice = result.scalar_one_or_none()

    if not invoice:
        logger.warning(f"Invoice not found: {invoice_id}")
        raise HTTPException(status_code=404, detail="Invoice not found")

    logger.info(f"Fetched invoice {invoice_id}: status={invoice.status}")
    return InvoiceResponse.model_validate(invoice)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.fastapi_host, port=settings.fastapi_port)
