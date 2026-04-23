from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from ui_server.config import construct_file_path
    from ui_server.db import get_db_context
    from ui_server.models import InvoiceStatus, Invoice
    from ui_server.parser import extract_text_from_file, parse_text


# ============= Pydantic Models =============
class ExtractionOutput(BaseModel):
    raw_text: str


class ParseOutput(BaseModel):
    data: dict
    confidence: dict


# ============= Activities =============
@activity.defn
def update_invoice_status(invoice_id: str, status: str) -> None:
    with get_db_context() as db:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.status = status


@activity.defn
def extract_text_activity(invoice_id: str, file_type: str) -> ExtractionOutput:
    file_path = construct_file_path(invoice_id, file_type)
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


# ============= Workflow =============
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
