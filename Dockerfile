FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt \
	&& useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser domain ./domain
COPY --chown=appuser:appuser engines ./engines
COPY --chown=appuser:appuser services ./services
COPY --chown=appuser:appuser frontend ./frontend

EXPOSE 8000
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
