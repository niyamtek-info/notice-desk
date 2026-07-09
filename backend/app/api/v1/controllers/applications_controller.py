from app.services.applications_service import ApplicationsService
from typing import Optional
from app.api.v1.dependencies.auth import AuditUser



class ApplicationsController:

    def __init__(self):
        self.service = ApplicationsService()

    def create_record(self, data: dict, source_type: str = "Manual", audit_user: AuditUser | None = None):
        return self.service.create_record(data, source_type, audit_user=audit_user)
    
    def upload_file(self, file, audit_user: AuditUser | None = None):
        return self.service.upload_file(file, audit_user=audit_user)

    def get_record(self, record_id: str):
        return self.service.get_record(record_id)

    def list_records(self, **filters):
        return self.service.list_records(**filters)

    def search_records(self, query: str):
        return self.service.search_records(query)

    def update_record(self, record_id: str, data: dict, audit_user: AuditUser | None = None):
        return self.service.update_record(record_id, data, audit_user=audit_user)

    def delete_record(self, record_id: str, audit_user: AuditUser | None = None):
        return self.service.delete_record(record_id, audit_user=audit_user)

    def get_document_url(self, record_id: str, filename: str):
        return self.service.get_document_url(record_id, filename)
    
    def download_template(self):
        return self.service.download_template()

