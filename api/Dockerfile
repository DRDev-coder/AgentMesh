FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KNOWLEDGE_BASE_PATH=/app/data/product_docs.json

WORKDIR /app
COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY api/ /app/api/
COPY agents/ /app/agents/
COPY consensus/ /app/consensus/
COPY shared/ /app/shared/
COPY data/ /app/data/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini

RUN addgroup --system agentmesh \
    && adduser --system --ingroup agentmesh agentmesh \
    && mkdir -p /app/state \
    && chown -R agentmesh:agentmesh /app/state
USER agentmesh
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
