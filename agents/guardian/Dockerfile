FROM python:3.11-slim
WORKDIR /app
COPY agents/guardian/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY agents/ /app/agents/
COPY shared/ /app/shared/
RUN addgroup --system agentmesh && adduser --system --ingroup agentmesh agentmesh
USER agentmesh
EXPOSE 5000
CMD ["uvicorn", "agents.guardian.main:app", "--host", "0.0.0.0", "--port", "5000"]
