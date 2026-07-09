from sqlalchemy.orm import Session
from app.db.models.checklist import ChecklistItem
from app.schemas.checklist import ChecklistItemCreate, ChecklistItemUpdate
from typing import List

# Define the standard rows and columns
STANDARD_FIELDS = [
    "Loan Account No.",
    "Borrower Name",
    "Date of allocation to Niyamtech",
    "Borrower Address",
    "Borrower Address_(Also At)",
    "Co-Borrower Name_1",
    "Co-Borrower Address_1",
    "Co-Borrower Address_1 (Also At)",
    "Co-Borrower Name_2",
    "Co-Borrower Address_2",
    "Co-Borrower Address_2 (Also At)",
    "Co-Borrower Name_3",
    "Co-Borrower Address_3",
    "Co-Borrower Address_3 (Also At)",
    "Co-Borrower Name_4",
    "Co-Borrower Address_4",
    "Co-Borrower Address_4 (Also At)",
    "Co-Borrower Name_5",
    "Co-Borrower Address_5",
    "Co-Borrower Address_5 (Also At)",
    "<Description of Schedule Property>",
    "Sanction Date",
    "Sanction Amount",
    "Loan Agreement Date",
    "Loan Amount"
]

STANDARD_DOCUMENTS = [
    "Sanction_Letter",
    "Loan_Agreement",
    "Memorandum_of_Deposit_of_Title_Deeds",
    "Sale Deed"
]

def get_checklist_by_application(db: Session, application_id: str):
    return db.query(ChecklistItem).filter(ChecklistItem.application_id == application_id).all()

def initialize_checklist(db: Session, application_id: str) -> List[ChecklistItem]:
    existing = get_checklist_by_application(db, application_id)
    if existing:
        return existing

    new_items = []
    for field in STANDARD_FIELDS:
        for doc in STANDARD_DOCUMENTS:
            item = ChecklistItem(
                application_id=application_id,
                field_name=field,
                document_type=doc,
                is_checked=False
            )
            db.add(item)
            new_items.append(item)
    
    db.commit()
    return new_items

def update_checklist_item(db: Session, item_id: int, update_data: ChecklistItemUpdate):
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        return None
    
    if update_data.is_checked is not None:
        item.is_checked = update_data.is_checked
    if update_data.remarks is not None:
        item.remarks = update_data.remarks
        
    db.commit()
    db.refresh(item)
    return item
