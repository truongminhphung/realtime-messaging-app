FROM python:3.12-slim
WORKDIR /app
RUN pip install uv==0.7.8
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.realtime_messaging.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
