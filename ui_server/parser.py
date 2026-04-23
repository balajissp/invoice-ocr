import logging
import os
import re
from pathlib import Path

from liteparse import LiteParse
from sqlalchemy.orm import Session

from ui_server.models import Invoice, InvoiceStatus
from ui_server.schemas import ExtractedDataSchema, ExtractionConfidenceSchema

UPLOADS_DIR = Path(os.getenv("TMP_DIR", "../.temp"))
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

logger = logging.getLogger(__name__)
parser = LiteParse()


async def extract_invoice(db: Session, invoice: Invoice) -> Invoice:
    """Extract text from file and populate invoice record."""

    # Get file type and extract text
    file_path = UPLOADS_DIR / f"{invoice.id}.{invoice.file_type}"
    file_ext = invoice.file_type

    raw_text = await parse_blob(file_path)

    invoice.raw_ocr_output = raw_text
    # Parse extracted text
    if raw_text:
        extracted_data, confidence = parse_text(raw_text)
        invoice.extracted_data = extracted_data.model_dump()
        invoice.extraction_confidence = confidence.model_dump()
        invoice.status = InvoiceStatus.COMPLETED
    else:
        invoice.extracted_data = {}
        invoice.extraction_confidence = {}
        invoice.status = InvoiceStatus.PARTIAL
        invoice.error_message = "No text extracted"

    db.commit()
    return invoice


async def parse_blob(file_path: Path) -> str:
    if file_path.suffix in ALLOWED_EXTENSIONS:
        # Parse file directly - LiteParse handles PDF/image conversion
        result = await parser.parse_async(file_path)
        logger.debug(f"{file_path=}, {result=}")
        if hasattr(result, "text"):
            raw_text = result.text.strip()
        else:
            raw_text = str(result)
    else:
        raw_text = ""  # Not supported file type
    return raw_text


def parse_text(raw_text: str) -> tuple:
    """Parse raw OCR text into structured fields. Returns (ExtractedDataSchema, ExtractionConfidenceSchema)."""
    extracted = ExtractedDataSchema()
    confidence = ExtractionConfidenceSchema()

    # Invoice number
    inv_match = re.search(r"Invoice[\s:#]*([\w-]+)", raw_text, re.IGNORECASE)
    if inv_match:
        extracted.invoice_number = inv_match.group(1).strip()
        confidence.invoice_number = 0.85

    # Invoice date
    date_match = re.search(r"Invoice Date[\s:#]*([\d/-]+)", raw_text, re.IGNORECASE)
    if date_match:
        extracted.invoice_date = date_match.group(1).strip()
        confidence.invoice_date = 0.80

    # Due date
    due_match = re.search(r"Due Date[\s:#]*([\d/-]+)", raw_text, re.IGNORECASE)
    if due_match:
        extracted.due_date = due_match.group(1).strip()
        confidence.due_date = 0.80

    # Total amount
    amount_match = re.search(r"Total[\s:#$]*([\d,.]+)", raw_text, re.IGNORECASE)
    if amount_match:
        amount_str = amount_match.group(1).replace(",", "")
        extracted.total_amount = float(amount_str)
        confidence.total_amount = 0.90

    # Currency
    if "$" in raw_text:
        extracted.currency = "USD"
    elif "€" in raw_text:
        extracted.currency = "EUR"
    elif "£" in raw_text:
        extracted.currency = "GBP"

    return extracted, confidence
