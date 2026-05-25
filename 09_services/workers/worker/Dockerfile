FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir redis psycopg[binary] httpx boto3 neo4j temporalio
COPY app /app

CMD ["python", "worker.py"]
