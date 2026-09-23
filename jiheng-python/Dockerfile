# syntax=docker/dockerfile:1
# Builder stage: Node/npm/git/pnpm are only needed to resolve the
# @deepseek-ai/dsh-mcp-client plugin's JS dependency tree into the profile
# template. The `dsh` runtime is a self-contained compiled binary at
# execution time and does not need any of this toolchain once the profile
# directory (with its node_modules already resolved) exists on disk.
FROM node:20-bookworm-slim AS node-base

FROM python:3.11-slim AS harness-builder
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
WORKDIR /app
COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npm install -g pnpm@10 --registry="$NPM_REGISTRY"
COPY pyproject.toml harness/UPSTREAM.lock ./
# deepseek-harness-sdk on PyPI trails the npm-published plugin packages
# (0.1.5rc1 is PyPI's newest as of this writing, vs 0.1.7-alpha.2 on npm
# below); pin both explicitly so builds don't silently drift when either
# side cuts a new release.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install deepseek-harness-sdk==0.1.5rc1 deepseek-harness-runtime-bin==0.1.5rc1 \
    && command -v dsh
COPY harness harness
RUN --mount=type=cache,target=/root/.npm \
    npm config set registry "$NPM_REGISTRY" \
    && DSH_HOME=/opt/jiheng-dsh-template JIHENG_APP_ROOT=/app dsh plugin --profile jiheng add @deepseek-ai/dsh-mcp-client@0.1.7-alpha.2 @deepseek-ai/dsh-mcp-resources@0.1.7-alpha.2 \
    && python3 -c "import json; p='/opt/jiheng-dsh-template/profiles/jiheng/package.json'; d=json.load(open(p)); d['dsh']['profile']['bundles']=[]; json.dump(d, open(p,'w'), indent=2)" \
    && cp harness/jiheng.cordis.patch.yml /opt/jiheng-dsh-template/profiles/jiheng/cordis.patch.yml \
    && DSH_HOME=/opt/jiheng-dsh-template JIHENG_APP_ROOT=/app DEEPSEEK_API_KEY=build-time-placeholder dsh --profile jiheng --dump-config >/dev/null

FROM python:3.11-slim
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
WORKDIR /app
COPY pyproject.toml harness/UPSTREAM.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install deepseek-harness-sdk==0.1.5rc1 deepseek-harness-runtime-bin==0.1.5rc1 \
    && command -v dsh \
    && pip install fastapi "uvicorn[standard]" httpx pydantic pydantic-settings sse-starlette PyJWT structlog "mcp>=1.1.2,<2" pymupdf beautifulsoup4
COPY --from=harness-builder /opt/jiheng-dsh-template /opt/jiheng-dsh-template
COPY app app
COPY harness harness
ENV JIHENG_AGENT_RUNTIME=harness-sdk
ENV JIHENG_APP_ROOT=/app
ENV JIHENG_DSH_TEMPLATE_HOME=/opt/jiheng-dsh-template
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
