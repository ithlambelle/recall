FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY recall/ ./recall/
COPY static/ ./static/
COPY api.py scenario.py experiment.py demo.py ./
COPY tests/ ./tests/

# Fail the build if the invariants the demo claims do not hold.
RUN pip install --no-cache-dir pytest && python -m pytest tests/ -q

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
