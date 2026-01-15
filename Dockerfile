FROM ghcr.io/astral-sh/uv:0.9-python3.14-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt update && apt install --no-install-recommends -y \
    build-essential \
    libpq-dev tree

WORKDIR /app
COPY ./pyproject.toml ./uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --all-groups
COPY /src /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-groups

# Start runtime image,
FROM ghcr.io/astral-sh/uv:0.9-python3.14-trixie-slim

# Create user beheeromgeving with the same UID as github actions runner.
RUN groupadd --system --gid 999  beheeromgeving  && useradd --system --gid 999 \
    --uid 1001 --create-home beheeromgeving
RUN apt update && apt install --no-install-recommends -y \
    curl \
    libpq5

WORKDIR /app
# Copy python build artifacts from builder image
COPY --from=builder /app /app

# Have some defaults so the container is easier to start
ENV DJANGO_SETTINGS_MODULE=beheeromgeving.settings \
    DJANGO_DEBUG=false \
    UWSGI_HTTP_SOCKET=:8000 \
    UWSGI_MODULE=beheeromgeving.wsgi \
    UWSGI_CALLABLE=application \
    UWSGI_MASTER=1
RUN uv run manage.py collectstatic --noinput
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT []
EXPOSE 8000

USER beheeromgeving
CMD ["uv", "run","uwsgi"]
