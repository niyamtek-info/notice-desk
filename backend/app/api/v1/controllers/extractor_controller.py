from fastapi import UploadFile, HTTPException
from fastapi.responses import JSONResponse
from app.services.extractor_service import ExtractorService


async def process_document_controller(file, doc_type, application_number, username, language, format):
    return await ExtractorService.process_document(
        file, doc_type, application_number, username, language, format
    )


async def get_local_document_controller(application_id: str):
    return await ExtractorService.get_local_document(application_id)


async def update_document_controller(application_number: str, file_id: str, edited_json: dict):
    return await ExtractorService.update_document(application_number, file_id, edited_json)


async def list_documents_controller(application_number: str):
    return await ExtractorService.list_documents(application_number)


async def get_document_controller(application_number: str, file_id: str):
    return await ExtractorService.get_document(application_number, file_id)


async def delete_document_controller(application_number: str, file_id: str):
    return await ExtractorService.delete_document(application_number, file_id)


async def get_recommendations_controller(application_id: str):
    return await ExtractorService.get_recommendations(application_id)
