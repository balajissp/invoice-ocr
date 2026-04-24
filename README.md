# Invoice OCR

A FastAPI-based REST API for automated invoice processing. Extracts text from invoice files (PDF, images, text) using OCR and parses structured data using GPT-4 via Temporal workflows.

## Features

- Multi-format invoice upload (PDF, PNG, JPG, TIFF, TXT)
- Optical character recognition with text extraction
- Structured data extraction using LLM
- Asynchronous workflow processing via Temporal
- PostgreSQL persistence with SQLAlchemy ORM
- Admin dashboard for database management
- Real-time extraction logging for debugging
- Health checks for database and Temporal connectivity
- OpenAPI documentation

## Requirements

- Python 3.10+
- PostgreSQL 13+
- Temporal Server
- Docker (optional, for containerized deployment)

## Installation

```bash
git clone <repository>
cd invoice-ocr
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and set required secrets:

```bash
cp .env.example .env
```

Update these values in `.env`:
- `POSTGRES_PASSWORD` - PostgreSQL password
- `OPENAI_API_KEY` - OpenAI API key for GPT-4
- `LANGFUSE_PUBLIC_KEY` - Langfuse observability key (optional)
- `LANGFUSE_SECRET_KEY` - Langfuse secret (optional)
- `TMP_DIR` - Directory for temporary file storage

## Quick Start with Docker Compose

```bash
docker-compose up -d
```

This starts all services: PostgreSQL, Temporal, Temporal worker, and FastAPI server.

Access:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Admin Dashboard: http://localhost:8000/admin
- Temporal UI: http://localhost:8233

## Manual Setup

```bash
# Migrate database
alembic upgrade head

# Start Temporal worker
python -m invoiceocr.workflows.worker

# Start API server
python -m invoiceocr.app.main
```

API documentation available at `http://localhost:8000/docs`

## API Endpoints

- `POST /invoices/upload` - Upload invoice for processing
- `GET /invoices/{invoice_id}` - Get extraction results
- `GET /invoices/{invoice_id}/logs` - View extraction logs
- `GET /health` - Health check

## Testing

```bash
pytest tests/
```

Run with Docker Compose:
```bash
docker-compose run tests
```

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/your-feature`)
5. Open a pull request

## Issues

Found a bug or have a feature request? Open an issue on GitHub. Include:
- Clear description of the problem or request
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (OS, Python version, Docker, etc.)

## License

MIT
