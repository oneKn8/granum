# Granum API — thin static server over the evolution artifacts (Cloud Run target).
# The API (granum.web.api) imports only FastAPI + stdlib, so this image is lean:
# no Vertex/Phoenix/MCP deps and no live dependencies at request time.
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.32"

# Minimal package surface for `granum.web.api`.
COPY src/granum/__init__.py /app/granum/__init__.py
COPY src/granum/web /app/granum/web
# Curated CellPayload artifacts (populated by infra/deploy.sh from runs/).
COPY api_data /app/api_data

ENV PYTHONPATH=/app \
    GRANUM_DATA_DIR=/app/api_data \
    PORT=8080

EXPOSE 8080
CMD ["sh", "-c", "uvicorn granum.web.api:app --host 0.0.0.0 --port ${PORT}"]
