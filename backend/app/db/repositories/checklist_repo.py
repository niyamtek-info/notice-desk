from sqlalchemy import case
from sqlalchemy.orm import Session

from app.api.v1.schemas.checklist_schema import ApplicationChecklistCreate, ApplicationChecklistUpdate
from app.db.models.extracted_data import ApplicationChecklist
from app.db.versioning import clone_version, close_version, current_actor, live_filter, mark_created, utcnow


class ChecklistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_application(self, application_number: str) -> list[ApplicationChecklist]:
        attribute_order = case(
            (ApplicationChecklist.attribute_code == "date", 1),
            (ApplicationChecklist.attribute_code == "borrower_name", 2),
            (ApplicationChecklist.attribute_code == "address", 3),
            (ApplicationChecklist.attribute_code == "loan_amount", 4),
            (ApplicationChecklist.attribute_code == "property_address", 5),
            (ApplicationChecklist.attribute_code == "co_borrower_1_name", 10),
            (ApplicationChecklist.attribute_code == "co_borrower_1_address", 11),
            (ApplicationChecklist.attribute_code == "co_borrower_2_name", 12),
            (ApplicationChecklist.attribute_code == "co_borrower_2_address", 13),
            (ApplicationChecklist.attribute_code == "co_borrower_3_name", 14),
            (ApplicationChecklist.attribute_code == "co_borrower_3_address", 15),
            (ApplicationChecklist.attribute_code == "co_borrower_4_name", 16),
            (ApplicationChecklist.attribute_code == "co_borrower_4_address", 17),
            (ApplicationChecklist.attribute_code == "co_borrower_5_name", 18),
            (ApplicationChecklist.attribute_code == "co_borrower_5_address", 19),
            else_=100,
        )
        return self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            *live_filter(ApplicationChecklist),
        ).order_by(
            ApplicationChecklist.pair_code.asc(),
            attribute_order.asc(),
            ApplicationChecklist.attribute_code.asc(),
            ApplicationChecklist.id.asc(),
        ).all()

    def get_entry(
        self,
        application_number: str,
        attribute_code: str,
    ) -> ApplicationChecklist:
        return self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            ApplicationChecklist.attribute_code == attribute_code,
            *live_filter(ApplicationChecklist),
        ).first()

    def create(self, audit_user=None, initial_version=1, **kwargs) -> ApplicationChecklist:
        db_obj = ApplicationChecklist(**kwargs)
        mark_created(db_obj, audit_user)
        db_obj.version = initial_version  # Set initial version (default 1 for checklist)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_row_values(
        self,
        application_number: str,
        attribute_code: str,
        values: dict,
        audit_user=None,
    ) -> ApplicationChecklist:
        db_obj = self.get_entry(application_number, attribute_code)
        if not db_obj:
            return None

        close_version(db_obj, audit_user)
        new_obj = clone_version(db_obj, audit_user, **values)
        self.db.add(new_obj)
        self.db.commit()
        self.db.refresh(new_obj)
        return new_obj

    def update_row_values_without_versioning(
        self,
        application_number: str,
        attribute_code: str,
        values: dict,
        audit_user=None,
    ) -> ApplicationChecklist:
        """
        Update checklist row values WITHOUT creating new versions.
        Used during validation to batch update all fields before creating final snapshot.
        """
        db_obj = self.get_entry(application_number, attribute_code)
        if not db_obj:
            return None

        # Update fields directly without versioning
        for key, val in values.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, val)

        db_obj.updated_at = utcnow()
        db_obj.updated_by = current_actor(audit_user)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_row_values_without_versioning_by_id(
        self,
        row_id: int,
        values: dict,
        audit_user=None,
    ) -> ApplicationChecklist:
        db_obj = self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.id == row_id,
            *live_filter(ApplicationChecklist),
        ).first()
        if not db_obj:
            return None

        for key, val in values.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, val)

        db_obj.updated_at = utcnow()
        db_obj.updated_by = current_actor(audit_user)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_single_row_by_id(
        self,
        row_id: int,
    ):
        return self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.id == row_id,
            *live_filter(ApplicationChecklist),
        ).first()

    def batch_snapshot_validation_results(self, application_number: str, audit_user=None):
        """
        Create a single version snapshot for all checklist rows after validation completes.
        This is called ONCE at the end of trigger_matching to create the final version.
        """
        rows = self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            *live_filter(ApplicationChecklist),
        ).all()

        new_rows = []
        for row in rows:
            close_version(row, audit_user)
            new_row = clone_version(row, audit_user)
            self.db.add(new_row)
            new_rows.append(new_row)

        self.db.commit()
        return new_rows

    def get_single_row(
        self,
        application_number: str,
        attribute_code: str,
    ):
        return self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            ApplicationChecklist.attribute_code == attribute_code,
            *live_filter(ApplicationChecklist),
        ).first()

    def delete_by_application(self, application_number: str, audit_user=None) -> int:
        rows = self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            *live_filter(ApplicationChecklist),
        ).all()
        count = len(rows)
        for row in rows:
            close_version(row, audit_user, deleted=True)
        self.db.commit()
        return count

    def update_rerun_validation(self, application_number: str, flag: int, audit_user=None):
        rows = self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            *live_filter(ApplicationChecklist),
        ).all()

        new_rows = []
        for row in rows:
            close_version(row, audit_user)
            new_row = clone_version(row, audit_user, rerun_validation=int(flag))
            self.db.add(new_row)
            new_rows.append(new_row)

        self.db.commit()
        return new_rows

    def set_rerun_flag_without_versioning(self, application_number: str, flag: int, audit_user=None) -> int:
        """
        Set the rerun_validation flag WITHOUT creating new versions.
        This is used for automatic updates (e.g., when extracted data changes).
        Only creates versions when user explicitly clicks "Run Validation".
        """
        rows = self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.application_number == application_number,
            *live_filter(ApplicationChecklist),
        ).all()

        count = 0
        actor = current_actor(audit_user)
        now = utcnow()
        for row in rows:
            row.rerun_validation = int(flag)
            row.updated_at = now
            row.updated_by = actor
            count += 1

        self.db.commit()
        return count


class MasterChecklistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        from app.db.models.extracted_data import MasterChecklist
        return self.db.query(MasterChecklist).order_by(MasterChecklist.id.asc()).all()

    def seed_default_fields(self):
        from app.db.models.extracted_data import MasterChecklist
        seed_data = [
            {"pair_code": "SL_LA", "document_a": "Sanction Letter", "document_b": "Loan Agreement", "attribute_code": "date", "attribute_label": "Date", "is_must": True},
            {"pair_code": "SL_LA", "document_a": "Sanction Letter", "document_b": "Loan Agreement", "attribute_code": "borrower_name", "attribute_label": "Borrower Name", "is_must": True},
            {"pair_code": "SL_LA", "document_a": "Sanction Letter", "document_b": "Loan Agreement", "attribute_code": "address", "attribute_label": "Address", "is_must": True},
            {"pair_code": "SL_LA", "document_a": "Sanction Letter", "document_b": "Loan Agreement", "attribute_code": "loan_amount", "attribute_label": "Loan Amount", "is_must": True},
            {"pair_code": "SL_LA", "document_a": "Sanction Letter", "document_b": "Loan Agreement", "attribute_code": "property_address", "attribute_label": "Property Address", "is_must": True},
            {"pair_code": "SL_LA", "document_a": "Sanction Letter", "document_b": "Loan Agreement", "attribute_code": "co_borrower_name", "attribute_label": "Co-Borrower Name", "is_must": False},
            {"pair_code": "SL_LA", "document_a": "Sanction Letter", "document_b": "Loan Agreement", "attribute_code": "co_borrower_address", "attribute_label": "Co-Borrower Address", "is_must": False},
            {"pair_code": "MODT_SD", "document_a": "MODT", "document_b": "Sale Deed", "attribute_code": "property_description", "attribute_label": "Property Description", "is_must": True},
        ]

        for data in seed_data:
            existing = self.db.query(MasterChecklist).filter(
                MasterChecklist.pair_code == data["pair_code"],
                MasterChecklist.attribute_code == data["attribute_code"],
            ).first()
            if not existing:
                self.db.add(MasterChecklist(**data))
        self.db.commit()
