from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.dependencies.auth import AuditUser, get_current_audit_user
from app.services.template_service import MasterTemplateService

router = APIRouter()


@router.post("/master-template/upload")
def upload_master_template(
    client_code: str = Form(...),
    client_name: str = Form(...),
    template_type: str = Form(...),
    batch_code: str = Form(None),
    file: UploadFile = File(None),
    file_path: UploadFile = File(None),
    template_string: str = Form(None),
    header_image: UploadFile = File(None),
    footer_image: UploadFile = File(None),
    header_image_name: str = Form(None),
    footer_image_name: str = Form(None),
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return MasterTemplateService(db).upload_template(
        client_code,   
        client_name,
        template_type,
        file,
        file_path,
        template_string,
        batch_code,
        header_image,
        footer_image,
        header_image_name,
        footer_image_name,
        audit_user
    )


@router.post("/master-template/master-template/upload", include_in_schema=False)
def upload_master_template_compat(
    client_code: str = Form(...),
    client_name: str = Form(...),
    template_type: str = Form(...),
    batch_code: str = Form(None),
    file: UploadFile = File(None),
    file_path: UploadFile = File(None),
    template_string: str = Form(None),
    header_image: UploadFile = File(None),
    footer_image: UploadFile = File(None),
    header_image_name: str = Form(None),
    footer_image_name: str = Form(None),
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return MasterTemplateService(db).upload_template(
        client_code,
        client_name,
        template_type,
        file,
        file_path,
        template_string,
        batch_code,
        header_image,
        footer_image,
        header_image_name,
        footer_image_name,
        audit_user,
    )


@router.put("/master-template/{template_id}")
def update_master_template(
    template_id: int,
    client_code: str = Form(None),
    client_name: str = Form(None),
    template_type: str = Form(None),
    batch_code: str = Form(None),
    file: UploadFile = File(None),
    file_path: UploadFile = File(None),
    template_string: str = Form(None),
    header_image: UploadFile = File(None),
    footer_image: UploadFile = File(None),
    header_image_name: str = Form(None),
    footer_image_name: str = Form(None),
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return MasterTemplateService(db).update_template(
        template_id=template_id,
        client_code=client_code,
        client_name=client_name,
        template_type=template_type,
        file=file,
        file_path=file_path,
        template_string=template_string,
        batch_code=batch_code,
        header_image=header_image,
        footer_image=footer_image,
        header_image_name=header_image_name,
        footer_image_name=footer_image_name,
        audit_user=audit_user,
    )


@router.put("/templates/{template_id}", include_in_schema=False)
def update_master_template_alias(
    template_id: int,
    client_code: str = Form(None),
    client_name: str = Form(None),
    template_type: str = Form(None),
    batch_code: str = Form(None),
    file: UploadFile = File(None),
    file_path: UploadFile = File(None),
    template_string: str = Form(None),
    header_image: UploadFile = File(None),
    footer_image: UploadFile = File(None),
    header_image_name: str = Form(None),
    footer_image_name: str = Form(None),
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return MasterTemplateService(db).update_template(
        template_id=template_id,
        client_code=client_code,
        client_name=client_name,
        template_type=template_type,
        file=file,
        file_path=file_path,
        template_string=template_string,
        batch_code=batch_code,
        header_image=header_image,
        footer_image=footer_image,
        header_image_name=header_image_name,
        footer_image_name=footer_image_name,
        audit_user=audit_user,
    )


@router.get("/master-template")
def get_all_templates(db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_all_templates()

@router.get("/templates", include_in_schema=False)
def get_all_templates_alias(db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_all_templates()

@router.get("/master-template/client/{client_code}")
def get_templates_by_client(client_code: str, db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_templates_by_client(client_code)


@router.get("/master-template/master-template/client/{client_code}", include_in_schema=False)
def get_templates_by_client_compat(client_code: str, db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_templates_by_client(client_code)

@router.get("/templates/client/{client_code}", include_in_schema=False)
def get_templates_by_client_alias(client_code: str, db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_templates_by_client(client_code)

@router.get("/master-template/type/{template_type}")
def get_templates_by_type(template_type: str, db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_templates_by_type(template_type)

@router.get("/templates/type/{template_type}", include_in_schema=False)
def get_templates_by_type_alias(template_type: str, db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_templates_by_type(template_type)


@router.get("/master-template/template-types")
def get_template_types(db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_template_types()


@router.get("/master-template/master-template/template-types", include_in_schema=False)
def get_template_types_compat(db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_template_types()

@router.get("/templates/template-types", include_in_schema=False)
def get_template_types_alias(db: Session = Depends(get_db)):
    return MasterTemplateService(db).get_template_types()


@router.delete("/master-template/{template_id}")
def delete_master_template(
    template_id: int,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return MasterTemplateService(db).delete_template(template_id, audit_user=audit_user)


@router.delete("/templates/{template_id}", include_in_schema=False)
def delete_master_template_alias(
    template_id: int,
    db: Session = Depends(get_db),
    audit_user: AuditUser = Depends(get_current_audit_user),
):
    return MasterTemplateService(db).delete_template(template_id, audit_user=audit_user)
