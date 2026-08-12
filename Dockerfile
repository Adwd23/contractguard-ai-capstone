FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONTRACTGUARD_ROOT=/app

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY scripts ./scripts
RUN pip install --no-deps -e . && mkdir -p /app/evidence && chown -R app:app /app

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["python", "-m", "contractguard.server"]
