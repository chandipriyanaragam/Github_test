FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir . \
    && useradd --system --uid 10001 --create-home appuser \
    && mkdir -p /data/documents \
    && chown -R appuser:appuser /app /data

USER 10001
EXPOSE 8000
CMD ["uvicorn", "app.start:app", "--host", "0.0.0.0", "--port", "8000"]
