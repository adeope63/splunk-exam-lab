FROM python:3.12-slim
WORKDIR /lab/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app app
COPY backend/migrations migrations
COPY backend/alembic.ini .
COPY question_bank /lab/question_bank
COPY references /lab/references
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
