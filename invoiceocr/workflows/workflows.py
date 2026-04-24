from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from invoiceocr.models.schemas import InvoiceStatus
from invoiceocr.workflows.activities import (
    update_invoice_status,
    extract_text_activity,
    parse_text_with_llm,
    save_extraction_results,
)


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
            parse_text_with_llm,
            extraction.raw_text,
            schedule_to_close_timeout=timedelta(seconds=60),
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
