import logging
import re
from datetime import timedelta
from pathlib import Path

from liteparse import LiteParse
from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from invoiceocr.models.config import settings, ALLOWED_EXTENSIONS
from invoiceocr.models.db import get_db_context, Invoice
from invoiceocr.models.schemas import (
    InvoiceStatus,
    ExtractedDataSchema,
    ExtractionConfidenceSchema,
    ExtractionOutput,
    ParseOutput,
)

logger = logging.getLogger(__name__)


@activity.defn
def update_invoice_status(invoice_id: str, status: str) -> None:
    with get_db_context() as db:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.status = status


@activity.defn
def extract_text_activity(invoice_id: str, file_type: str) -> ExtractionOutput:
    file_path = settings.construct_file_path(invoice_id, file_type)
    raw_text = extract_text_from_file(file_path)
    return ExtractionOutput(raw_text=raw_text)


@activity.defn
def parse_text_activity(raw_text: str) -> ParseOutput:
    data, confidence = parse_text(raw_text)
    return ParseOutput(data=data.model_dump(), confidence=confidence.model_dump())


@activity.defn
def save_extraction_results(
    invoice_id: str,
    raw_text: str,
    data: dict,
    confidence: dict,
) -> None:
    with get_db_context() as db:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.status = InvoiceStatus.COMPLETED
            invoice.raw_ocr_output = raw_text
            invoice.extracted_data = data
            invoice.extraction_confidence = confidence


@workflow.defn
class InvoiceProcessingWorkflow:
    @workflow.run
    async def run(self, invoice_id: str, file_type: str) -> None:
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

        await workflow.execute_activity(
            update_invoice_status,
            args=[invoice_id, InvoiceStatus.EXTRACTING],
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        extraction = await workflow.execute_activity(
            extract_text_activity,
            args=[invoice_id, file_type],
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        parse_output = await workflow.execute_activity(
            parse_text_activity,
            extraction.raw_text,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        await workflow.execute_activity(
            save_extraction_results,
            args=[
                invoice_id,
                extraction.raw_text,
                parse_output.data,
                parse_output.confidence,
            ],
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )


def extract_text_from_file(file_path: str) -> str:
    file_path = Path(file_path)
    if file_path.suffix in ALLOWED_EXTENSIONS:
        # Parse file directly - LiteParse handles PDF/image conversion
        parser = LiteParse()
        result = parser.parse(file_path)
        logger.info(f"OCR result for {file_path.name}: {result}")
        if hasattr(result, "text"):
            raw_text = result.text.strip()
        else:
            raw_text = str(result)
    else:
        raw_text = ""  # Not supported file type
    return raw_text


def parse_text(raw_text: str) -> tuple[ExtractedDataSchema, ExtractionConfidenceSchema]:
    """Parse extracted text into structured invoice fields."""
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
