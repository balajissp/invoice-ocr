# SQLAdmin Dashboard
from sqladmin import ModelView, Admin

from ui_server.db import engine
from ui_server.models import Invoice, ExtractionLog


class InvoiceAdmin(ModelView, model=Invoice):
    """Read-only invoice view."""
    page_size = 20
    can_create = False
    can_edit = False
    can_delete = False
    can_export = True
    column_list = [
        Invoice.id,
        Invoice.workflow_id,
        Invoice.filename,
        Invoice.status,
        Invoice.created_at,
        Invoice.updated_at,
    ]
    column_sortable_list = [Invoice.created_at, Invoice.status]
    column_searchable_list = [Invoice.filename, Invoice.id]


class LogAdmin(ModelView, model=ExtractionLog):
    """Read-only extraction log view."""
    page_size = 50
    can_create = False
    can_edit = False
    can_delete = False
    column_list = [
        ExtractionLog.id,
        ExtractionLog.invoice_id,
        ExtractionLog.step,
        ExtractionLog.created_at,
    ]
    column_sortable_list = [ExtractionLog.created_at, ExtractionLog.step]
    column_searchable_list = [ExtractionLog.invoice_id]


def register_admin(app):
    admin = Admin(app=app, engine=engine, title="Invoice Pipeline Dashboard")
    admin.add_view(InvoiceAdmin)
    admin.add_view(LogAdmin)
