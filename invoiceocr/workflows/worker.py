import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

# with workflow.unsafe.imports_passed_through():
from invoiceocr.models.config import settings
from invoiceocr.workflows.tasks import (
    update_invoice_status,
    extract_text_activity,
    parse_text_activity,
    save_extraction_results,
    InvoiceProcessingWorkflow,
)


async def main():
    client = await Client.connect(settings.temporal_url)
    worker = Worker(
        client,
        task_queue="invoice-processing",
        workflows=[InvoiceProcessingWorkflow],
        activities=[
            update_invoice_status,
            extract_text_activity,
            parse_text_activity,
            save_extraction_results,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=10),
    )
    print("Worker started")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
