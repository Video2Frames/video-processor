# Base stage
FROM python:3.14-slim AS base

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./

# Production builder
FROM base AS prod-builder

RUN poetry install --only=main --no-root && \
    rm -rf $POETRY_CACHE_DIR

# Development builder
FROM base AS dev-builder

RUN poetry install --no-root && \
    rm -rf $POETRY_CACHE_DIR

# Production runtime
FROM python:3.14-slim AS production

ARG USER_UID=1000
ARG VERSION=1.0.0

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

LABEL author="SOAT Team"
LABEL version=${VERSION}
LABEL description="Video2Frame - Video Processor"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -d /app -u ${USER_UID} -s /bin/bash soat

WORKDIR /app

COPY --from=prod-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

USER soat

COPY --chown=${USER_UID}:${USER_UID} ./docker-entrypoint ./docker-entrypoint
COPY --chown=${USER_UID}:${USER_UID} ./video_processor ./video_processor
COPY --chown=${USER_UID}:${USER_UID} ./logging.ini ./logging.ini

EXPOSE 8000

ENTRYPOINT ["sh", "/app/docker-entrypoint/start_video_uploaded_listener.sh"]

# Development/Test runtime
FROM python:3.14-slim AS development

ARG USER_UID=1000
ARG VERSION=1.0.0-dev

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

LABEL author="SOAT Team"
LABEL version=${VERSION}
LABEL description="Video2Frame - Video Processor - Development"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -d /app -u ${USER_UID} -s /bin/bash soat

WORKDIR /app

COPY --from=dev-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

USER soat

COPY --chown=${USER_UID}:${USER_UID} ./docker-entrypoint ./docker-entrypoint
COPY --chown=${USER_UID}:${USER_UID} ./video_processor ./video_processor
# COPY --chown=${USER_UID}:${USER_UID} ./tests ./tests
COPY --chown=${USER_UID}:${USER_UID} ./logging.ini ./logging.ini
# COPY --chown=${USER_UID}:${USER_UID} ./pytest.ini ./pytest.ini
COPY --chown=${USER_UID}:${USER_UID} ./pyproject.toml ./pyproject.toml
# COPY --chown=${USER_UID}:${USER_UID} ./.coveragerc ./.coveragerc

EXPOSE 8000

ENTRYPOINT ["sh", "/app/docker-entrypoint/start_video_uploaded_listener.sh"]
