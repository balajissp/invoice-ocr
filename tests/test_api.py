import logging
import time
from pathlib import Path

from fastapi.testclient import TestClient
from ui_server.app import app

client = TestClient(app)
logger = logging.getLogger(__name__)


def test_upload_invoice(filename="sample_invoice.jpg"):
    """Test invoice upload endpoint."""
    basepath = Path(__file__)
    sample_invoice = basepath.parent / "data" / filename
    with open(sample_invoice, "rb") as f:
        response = client.post(
            "/invoices/upload",
            files={
                "file": (sample_invoice.name, f, f"application/{sample_invoice.suffix}")
            },
        )
        logger.info(response.json())

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "PENDING"
    assert "invoice_id" in data

    # test retrieval
    sample_invoice_id = data["invoice_id"]

    for attempt in range(1, 6):  # 5 attempts
        response = client.get(f"/invoices/{sample_invoice_id}")

        assert response.status_code == 200
        data = response.json()
        logger.info(data)
        assert data["extracted_data"] is not None
        if data["status"] != "COMPLETED":
            time.sleep(5)
        else:
            break
    else:
        # did not work ever after multiple retries, notify user
        assert data["status"] != "COMPLETED", "Unable to parse despite multiple retries"


def test_upload_pdf():
    test_upload_invoice("sample.pdf")
