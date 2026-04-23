import asyncio
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

load_dotenv()
with workflow.unsafe.imports_passed_through():
    from ui_server.workflows import (
        InvoiceProcessingWorkflow,
        update_invoice_status,
        extract_text_activity,
        parse_text_activity,
        save_extraction_results,
    )


async def main():
    client = await Client.connect("temporal:7233")
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
