FROM postgres:16-alpine@sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d
COPY --chmod=0644 deploy/postgres-init.sh /docker-entrypoint-initdb.d/10-app.sh
USER postgres
