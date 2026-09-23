FROM node:22-bookworm-slim AS harness-source
# Local prefetch (GitHub often unreachable inside Docker build).
# Prepare with: git clone + checkout commit into .build-harness
ARG DEEPSEEK_HARNESS_COMMIT=00102833dfaee1da9f48a3a8eae9d34005a75218
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN apt-get update && apt-get install -y --no-install-recommends \
      git python3 python3-venv python3-pip build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*
COPY .build-harness /opt/deepseek-harness
RUN git -C /opt/deepseek-harness rev-parse HEAD | grep -Fx "$DEEPSEEK_HARNESS_COMMIT"
WORKDIR /opt/deepseek-harness
RUN corepack enable \
    && npm config set registry "$NPM_REGISTRY" \
    && pnpm config set registry "$NPM_REGISTRY" \
    && pnpm install --frozen-lockfile \
    && pnpm run build:official

FROM python:3.11-slim
ARG NPM_REGISTRY=https://registry.npmmirror.com
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm git \
    && npm install -g pnpm@11 --registry="$NPM_REGISTRY" \
    && rm -rf /var/lib/apt/lists/*
COPY --from=harness-source /opt/deepseek-harness /opt/deepseek-harness
COPY pyproject.toml harness/UPSTREAM.lock ./
RUN git -C /opt/deepseek-harness rev-parse HEAD | grep -Fx "00102833dfaee1da9f48a3a8eae9d34005a75218" \
    && pip install --no-cache-dir /opt/deepseek-harness/python/sdk-runtime /opt/deepseek-harness/python/sdk \
    && command -v dsh \
    && pip install --no-cache-dir fastapi "uvicorn[standard]" httpx redis pydantic pydantic-settings sse-starlette PyJWT structlog mcp pymupdf beautifulsoup4
COPY app app
COPY harness harness
RUN mkdir -p /opt/jiheng-dsh-template \
    && DSH_HOME=/opt/jiheng-dsh-template JIHENG_APP_ROOT=/app dsh --profile jiheng --dump-default-config >/dev/null \
    && DSH_HOME=/opt/jiheng-dsh-template JIHENG_APP_ROOT=/app dsh plugin --profile jiheng add file:/opt/deepseek-harness/packages/mcp/mcp-client
ENV JIHENG_AGENT_RUNTIME=harness-sdk
ENV JIHENG_APP_ROOT=/app
ENV JIHENG_DSH_TEMPLATE_HOME=/opt/jiheng-dsh-template
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
