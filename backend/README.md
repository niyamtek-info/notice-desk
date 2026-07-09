# Property Management System — Backend

This repository contains the backend for a property and loan document-extraction and processing service.
The application uses FastAPI and is organised with an API layer, services, gateways/repositories and AI agents.

---

## Quick start (Windows PowerShell)

1. **Create and activate a Python 3.11+ virtual environment:**

   ```powershell
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

3. **Copy environment template and populate secrets:**

   ```powershell
   copy .env.example .env
   # Populate AWS, Google Cloud, and Gemini keys
   notepad .env
   ```

4. **Start the development server:**

   ```powershell
   uvicorn app.main:app --reload
   ```

OpenAPI docs are available at `http://127.0.0.1:8000/docs`.

---

## Create the First User

The UI does not include a super admin page now. If you need a first admin account, create it directly in the database or through your own bootstrap process before starting the app.

---

## Background Services (Redis & Celery)

The recommendation engine requires **Redis** as a broker and a **Celery** worker to process tasks.

### 1. Start Redis in Docker
From `backend/`, run:
```powershell
docker compose -f docker/docker-compose.redis.yml up -d
```

This exposes Redis on `localhost:6379`.

### 2. Start Celery Worker
In a new terminal (with the virtual environment activated), run:
```powershell
# For Windows, use the 'threads' or 'solo' pool
celery -A app.core.celery_app:celery_app worker --loglevel=info -Q celery,extraction_queue,checklist_queue,translation_queue -P solo
```

Set these in `.env` so Celery uses the Docker Redis container:
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 3. Run the backend and Celery separately

Use separate terminals for the application processes:

```powershell
# Terminal 1: backend API
uvicorn app.main:app --reload
```

```powershell
# Terminal 2: Celery worker
celery -A app.core.celery_app:celery_app worker --loglevel=info -Q celery,extraction_queue,checklist_queue,translation_queue -P solo
```

---

## Environment Variables

Populate `.env` with values required by `app/core/settings.py`. Key groups:

- **Storage (S3):** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `AWS_REGION`
- **OCR (Google DocAI):** `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_PROJECT_ID`, `GOOGLE_LOCATION`, `GOOGLE_PROCESSOR_ID`
- **AI Agent (Gemini):** `GEMINI_API_KEY`
- **Paths:** `POPPLER_PATH`, `TMP_DIR`

---

## Repository Layout

```
Backend/
├─ app/
│  ├─ api/v1/           # controllers, routers, schemas
│  ├─ core/             # settings.py, logging.py
│  ├─ gateways/         # S3 gateway
│  ├─ services/         # business logic (Applications, Extraction, etc.)
│  ├─ db/               # repositories (Local JSON DB)
│  └─ utils/            # OCR, LLM, Prompt utilities
├─ ai/                  # Recommendation Agent & Background Workers
├─ metatable/           # Recommend_context.yaml (AI Knowledge Schema)
├─ json_db/             # Local database (applications, logs, recommendations)
├─ requirements.txt
└─ README.md
```

---

## Verifying Recommendations

1. **Create an Application** in the frontend.
2. **Observe Workers**: The Celery terminal will log `[Celery] Processing recommendations for APPxxx`.
3. **Verify Output**:
   - Check `Backend/json_db/recommendations/APPxxx.json`.
   - Check `Backend/json_db/recommendations/APPxxx_context.json` for the data used by the AI.
4. **Front-end View**: Refresh the "Information Gathering" page for the app to see the "Required Documents" list.

---

## Development commands

```powershell
# Format code
black .

# Linting
ruff check .

# Run tests
pytest
```
