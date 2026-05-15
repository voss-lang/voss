FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY voss ./voss
COPY voss_runtime ./voss_runtime

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN useradd --create-home --shell /bin/sh voss \
    && mkdir -p /workspace \
    && chown -R voss:voss /workspace

USER voss
WORKDIR /workspace

ENTRYPOINT ["voss"]
CMD ["--help"]
