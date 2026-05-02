FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY entrypoint.sh ./

RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run injects PORT=8080; local dev defaults to 8000.
EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
