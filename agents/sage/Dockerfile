FROM python:3.11-slim
WORKDIR /app
COPY agents/sage/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY agents/ /app/agents/
COPY shared/ /app/shared/
COPY data/ /app/data/
ENV KNOWLEDGE_BASE_PATH=/app/data/product_docs.json
RUN addgroup --system agentmesh && adduser --system --ingroup agentmesh agentmesh
USER agentmesh
EXPOSE 5000
CMD ["uvicorn", "agents.sage.main:app", "--host", "0.0.0.0", "--port", "5000"]
