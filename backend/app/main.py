# main.py
import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

if os.name == "nt":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        pass


from app.core.settings import settings
from app.db.base import Base
from app.db.session import engine
from app.core.background_store import start_background_writer

# -------------------------- #
# Routers
# -------------------------- #
from app.api.v1.routers.extractor_router import router as extractor_router
from app.api.v1.routers.applications_router import router as application_router
from app.api.v1.routers.observation_router import router as observation_router
from app.api.v1.routers.translation_router import router as translation_router
from app.api.v1.routers.upload_router import router as upload_router
from app.api.v1.routers.health_router import router as health_router
from app.api.v1.routers.auth_router import router as auth_router
from app.api.v1.routers.checklist_router import router as checklist_router
from app.api.v1.routers.client_router import router as client_router
from app.api.v1.routers.files_router import router as files_router



def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Property and Loan Management Service",
        version="1.0.0",
    )

    @app.on_event("startup")
    def on_startup():
        print("Checking database tables on startup...")
        Base.metadata.create_all(bind=engine)
        
        # Initialize background store writer for non-blocking Redis operations
        print("Starting background store writer...")
        start_background_writer()
        print("Background store writer started successfully")


    origins = [
        "http://3.110.135.254:3000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.0.34:3000"
        
    ]

    # -------------------------- #
    # CORS
    # -------------------------- #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------- #
    # Routers
    # -------------------------- #
    from fastapi import APIRouter
    api_router = APIRouter(prefix="/api/v1")

    api_router.include_router(
        extractor_router,
        prefix="/extract",
        tags=["Extractor"]
    )

    api_router.include_router(
        application_router,
        prefix="/applications",
        tags=["Applications"]
    )


    api_router.include_router(
        observation_router,
        prefix="/observations", # removed /api from prefix
        tags=["Observations"]
    )

    api_router.include_router(
        translation_router,
        prefix="/translate",
        tags=["Translation"]
    )

    api_router.include_router(
        upload_router,
        prefix="/uploads",
        tags=["Uploads"]
    )

    api_router.include_router(
        health_router,
        prefix="/health",
        tags=["Health"]
    )

    api_router.include_router(
        auth_router,
        prefix="/auth",
        tags=["Auth"]
    )

    api_router.include_router(
        checklist_router,
        prefix="/checklist",
        tags=["Checklist"]
    )

    api_router.include_router(
        client_router,
        prefix="/client",
        tags=["Client"]
    )

    api_router.include_router(
        files_router,
        tags=["Files"]
    )


    from app.api.v1.routers.report_router import router as report_router
    api_router.include_router(
        report_router,
        tags=["Report"] # prefix is already defined in the router itself as /report
    )

    from app.api.v1.routers.mail_router import router as mail_router
    api_router.include_router(
        mail_router,
        prefix="/mail",
        tags=["Mail"]
    )
    from app.api.v1.routers.template_router import router as template_router
    api_router.include_router(
        template_router,
        tags=["Templates"]
    )

    from app.api.v1.routers.sarfaesi_router import router as sarfaesi_router
    api_router.include_router(
        sarfaesi_router,
        prefix="/sarfaesi",
        tags=["Sarfaesi"]
    )

    # from app.api.v1.routers.notice_router import router as notice_router
    # api_router.include_router(
    #     notice_router,
    #     prefix="/notice",
    #     tags=["Notice Generator"]
    # )

    app.include_router(api_router)

    # -------------------------- #
    # Static Files
    # -------------------------- #
    uploads_dir = os.path.join(settings.BASE_DIR, "app", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount(
        "/uploads",
        StaticFiles(directory=uploads_dir),
        name="uploads",
    )

    # Keep temp files available separately if needed
    os.makedirs(settings.TMP_DIR, exist_ok=True)
    app.mount(
        "/tmp",
        StaticFiles(directory=settings.TMP_DIR),
        name="tmp",
    )

    # Mount logo directory
    logo_dir = os.path.join(settings.BASE_DIR, "logo")
    if os.path.exists(logo_dir):
        app.mount(
            "/logo",
            StaticFiles(directory=logo_dir),
            name="logo",
        )





    # -------------------------- #
    # Root
    # -------------------------- #
    @app.get("/")
    def root():
        return {"message": "Property and Loan Management Service Running"}

    return app


app = create_app()
