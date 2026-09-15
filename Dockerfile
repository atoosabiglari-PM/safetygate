FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN groupadd --system safetygate \
    && useradd --system --gid safetygate --create-home safetygate

COPY pyproject.toml README.md alembic.ini ./
COPY backend ./backend
COPY alembic ./alembic

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN chown -R safetygate:safetygate /app

USER safetygate

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
