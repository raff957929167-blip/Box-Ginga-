FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml ./
RUN pip install "mistralai-workflows[mistralai]>=3.10,<4"

COPY src ./src

CMD ["python", "src/entrypoints/worker.py"]
