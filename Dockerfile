FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir .

CMD ["trusted-network-registry", "--help"]
