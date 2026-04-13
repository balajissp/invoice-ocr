from pathlib import Path

from fastapi.testclient import TestClient
from ui_server.app import app

client = TestClient(app)


def test_upload_invoice():
    """Test invoice upload endpoint."""
    basepath = Path(__file__)
    sample_invoice = basepath.parent / "data" / "sample_invoice.jpg"
    with open(sample_invoice, "rb") as f:
        response = client.post(
            "/invoices/upload",
            files={"file": (sample_invoice.name, f, "application/jpg")},
        )
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"
    assert "invoice_id" in data

    # test retrieval
    sample_invoice_id = data["invoice_id"]

    response = client.get(f"/invoices/{sample_invoice_id}")

    assert response.status_code == 200
    data = response.json()
    print(data)
    assert "extracted_data" in data
