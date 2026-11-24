FROM python:3.13-slim

# uv, copied from its official image (pin this to your local uv version)
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 1. Dependencies only: this layer is cached until uv.lock changes
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# 2. The project itself
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Run as an unprivileged user, not root
RUN useradd --create-home appuser
USER appuser

ENTRYPOINT ["haa"]
CMD ["--help"]