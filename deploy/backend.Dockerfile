FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS dependencies
WORKDIR /build
COPY backend/requirements-production.txt ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir \
      --require-hashes -r requirements-production.txt

FROM dependencies AS neural-dependencies
COPY backend/requirements-production-neural.txt ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    /opt/venv/bin/pip install --no-cache-dir --require-hashes \
      --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-production-neural.txt

FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS assets
ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/app/backend PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/tmp/hf \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
WORKDIR /app
RUN groupadd --gid 10001 bhasha && useradd --uid 10001 --gid 10001 --no-create-home bhasha
COPY --link --chown=10001:10001 . /app
USER 10001:10001
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--timeout-graceful-shutdown", "25", "--limit-concurrency", "64"]

FROM assets AS neural
COPY --link --from=neural-dependencies /opt/venv /opt/venv

FROM assets AS core
COPY --link --from=dependencies /opt/venv /opt/venv
