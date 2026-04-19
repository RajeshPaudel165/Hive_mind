FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv venv /opt/venv --python /usr/local/bin/python \
    && uv pip install --python /opt/venv/bin/python -r requirements.txt
RUN python -c "import fastapi, numpy; assert numpy.__version__.startswith('1.'), numpy.__version__"

COPY . .

RUN mkdir -p /app/data

EXPOSE 8010

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
