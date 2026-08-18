FROM --platform=linux/amd64 python:3.11-slim-bookworm

ARG ODOO_VERSION=18.0

ENV ODOO_SRC=/opt/odoo \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates fonts-dejavu-core git libfreetype6-dev \
    libjpeg-dev libldap2-dev libpq-dev libsasl2-dev libssl-dev libxml2-dev \
    libxslt1-dev node-less npm zlib1g-dev \
    && git clone --depth 1 --branch "${ODOO_VERSION}" https://github.com/odoo/odoo.git "${ODOO_SRC}" \
    && python -m pip install --upgrade pip wheel setuptools \
    && pip install -r "${ODOO_SRC}/requirements.txt" \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
