FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY mock_apis ./mock_apis

RUN pip install --no-cache-dir -e ".[otel]"

ENV AIH_ENV=prod
ENV AIH_MOCK_API_BASE_URL=http://mock-apis:9000

EXPOSE 8000

CMD ["uvicorn", "aih.service.app:app", "--host", "0.0.0.0", "--port", "8000"]
