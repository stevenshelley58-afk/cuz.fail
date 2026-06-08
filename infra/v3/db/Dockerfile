FROM postgis/postgis:16-3.5

ARG PGVECTOR_VERSION=0.8.0

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      build-essential \
      postgresql-server-dev-16 \
      wget; \
    wget -O /tmp/pgvector.tar.gz "https://github.com/pgvector/pgvector/archive/refs/tags/v${PGVECTOR_VERSION}.tar.gz"; \
    mkdir -p /tmp/pgvector; \
    tar -xzf /tmp/pgvector.tar.gz -C /tmp/pgvector --strip-components=1; \
    make -C /tmp/pgvector; \
    make -C /tmp/pgvector install; \
    rm -rf /tmp/pgvector /tmp/pgvector.tar.gz; \
    apt-get purge -y --auto-remove build-essential postgresql-server-dev-16 wget; \
    rm -rf /var/lib/apt/lists/*

COPY infra/v3/db/init-extensions.sql /docker-entrypoint-initdb.d/10-init-extensions.sql
COPY infra/v3/db/healthcheck.sh /usr/local/bin/draftcheck-v3-db-healthcheck

RUN chmod +x /usr/local/bin/draftcheck-v3-db-healthcheck
