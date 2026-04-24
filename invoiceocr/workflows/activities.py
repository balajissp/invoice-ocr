import json
import logging
import re
from pathlib import Path

from liteparse import LiteParse
from temporalio import activity, workflow

from invoiceocr.models.config import settings, ALLOWED_EXTENSIONS
from invoiceocr.models.db import get_db_context, Invoice
from invoiceocr.models.schemas import (
    InvoiceStatus,
    ExtractedDataSchema,
    ExtractionConfidenceSchema,
    ExtractionOutput,
    ParseOutput,
)

with workflow.unsafe.imports_passed_through():
    from langfuse.openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@activity.defn
async def parse_text_with_llm(raw_text: str) -> ParseOutput:
    """Parse extracted text using ChatGPT via Langfuse."""
    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        max_retries=0,
    )

    system_prompt = """You are an invoice parsing expert. Extract structured data from the provided invoice text.

    Return a JSON object with these fields:
    {
        "invoice_number": string or null,
        "invoice_date": string (YYYY-MM-DD format) or null,
        "due_date": string (YYYY-MM-DD format) or null,
        "vendor_name": string or null,
        "vendor_address": string or null,
        "total_amount": float or null,
        "currency": string or null,
        "line_items": array of {description, quantity, unit_price, total} or null,
        "notes": string or null,
        "confidence": {
            "invoice_number": float (0-1),
            "invoice_date": float (0-1),
            "due_date": float (0-1),
            "vendor_name": float (0-1),
            "total_amount": float (0-1)
        }
    }

    Only return valid JSON, no additional text."""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.3,
    )

    response_text = response.choices[0].message.content
    parsed_response = json.loads(response_text)

    # Extract confidence scores
    confidence_dict = parsed_response.pop("confidence", {})

    # Create schemas
    data = ExtractedDataSchema(**parsed_response)
    confidence = ExtractionConfidenceSchema(**confidence_dict)

    return ParseOutput(
        data=data.model_dump(),
        confidence=confidence.model_dump(),
    )


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
