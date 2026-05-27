FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] psycopg[binary] redis neo4j boto3 httpx
COPY app /app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
