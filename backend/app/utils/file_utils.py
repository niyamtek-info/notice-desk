import os
from datetime import datetime


UPLOAD_FOLDER = "bulk_uploads/bulk_notices"


def generate_upload_batch_name(bank_name: str):

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"{bank_name}_{timestamp}"


def save_excel(file, upload_batch_name):

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    file_path = f"{UPLOAD_FOLDER}/{upload_batch_name}.xlsx"

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return file_path