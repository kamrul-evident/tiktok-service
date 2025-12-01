# Builder stage
FROM python:3.13-alpine AS builder
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends build-essential curl ca-certificates \
#     && rm -rf /var/lib/apt/lists/*
RUN apk add --no-cache build-base gcc libffi-dev musl-dev openssl-dev
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_SYSTEM_PYTHON=1

WORKDIR /src

COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt

# Final stage - a minimal image
FROM python:3.13-alpine AS final

ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Dhaka

RUN apk add --no-cache tzdata && \
    ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime && \
    echo "$TZ" > /etc/timezone

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# COPY --from=builder /bin/uv /bin/uv
# COPY --from=builder /bin/uvx /bin/uvx

WORKDIR /src
COPY src .

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000","--reload"]