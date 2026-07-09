# New Property Management System

Full-stack property and loan management system with:

- FastAPI backend
- Next.js frontend
- MySQL database
- Redis + Celery for background tasks

## Prerequisites

1. Python 3.11+
2. Node.js 18+
3. MySQL 8+
4. Redis 7+ running in Docker
5. Google Cloud Document AI credentials
6. AWS credentials for S3
7. Gemini API key

## Environment Variables

Create `backend/.env` with the values used by `app/core/settings.py`.
The database details should be updated in `backend/app/core/settings.py` as well, since it builds the MySQL connection settings from those values.

Required backend variables usually include:

- `DATABASE_URL`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_PROJECT_ID`
- `GOOGLE_LOCATION`
- `GOOGLE_PROCESSOR_ID`
- `GEMINI_API_KEY`
- `TMP_DIR`
- `POPPLER_PATH`

Create `frontend/.env.local` with:

- `NEXT_PUBLIC_API_URL`

## Deployment Steps

### 1. Clone the repository

```powershell
git clone <repo-url>
cd new-property-management-system
```

### 2. Prepare the backend environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

### 3. Configure backend settings

1. Copy your environment template to `backend/.env`.
2. Fill in the database, Redis, AWS, Google, and Gemini values.
3. Confirm `DATABASE_URL` points to the target MySQL database.

### 4. Create and migrate the database

1. Create the MySQL database if it does not exist.
2. Run Alembic migrations:

```powershell
alembic upgrade head
```

### 5. Create the first user

The UI no longer has a super admin page. If you need a first admin account, create it directly in the database or via your preferred admin bootstrap workflow before starting the app.

### 6. Start Redis and Celery

Start Redis in Docker from the `backend/` directory:

```powershell
docker run -d -p 6379:6379 --name matex-redis redis
```

Then start the Celery worker in a separate terminal:

If single worker:
```powershell
celery -A app.core.celery_app:celery_app worker --loglevel=info -Q celery,extraction_queue,checklist_queue,translation_queue -P solo
```
If multiple worker:
```powershell
celery -A app.core.celery_app worker --loglevel=info -Q celery,extraction_queue,checklist_queue,translation_queue -P threads --concurrency=6 
```


### 7. Start the backend API

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API docs will be available at:

- `http://127.0.0.1:8000/docs`

### 8. Prepare the frontend

```powershell
cd ..\frontend
npm install
```

Create `frontend/.env.local` and set:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

### 9. Build and start the frontend

```powershell
npm run build
npm start
```

The frontend will usually be available at:

- `http://127.0.0.1:3000`

### 10. Verify the deployment

1. Open the frontend home page.
2. Confirm login works.
3. Create or open an application.
4. Verify the backend API returns records correctly.
5. Confirm report availability is populated from the reports table.

## Local Run Layout

This project is intended to run with:

1. Redis in Docker only.
2. Backend in one terminal with `uvicorn`.
3. Celery in a second terminal.
4. Frontend in a third terminal.

The frontend should point at the backend API URL through `NEXT_PUBLIC_API_URL`.

## Repository Layout

```text
new-property-management-system/
  backend/
  frontend/
  README.md
```

## Notes

- The backend automatically creates ORM-managed tables on startup, but production deployments should still run Alembic first.
- Keep the backend and frontend environment variables in sync with the deployed API URL.
- If you change the database schema, run the migration before starting the app.
