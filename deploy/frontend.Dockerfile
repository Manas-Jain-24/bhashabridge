FROM node:24-alpine@sha256:116b800c3754b440ee0aa3ed2f20f5bf3d99a554bfd9adeea09ea8017f6e85f5 AS build
WORKDIR /build
COPY frontend ./frontend
COPY shared ./shared
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi; \
    cd frontend && npm ci --no-audit && npm run build && rm -rf node_modules && npm cache clean --force

FROM caddy:2-alpine@sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0
COPY --link --chown=10001:10001 --from=build /build/frontend/dist /srv
COPY --chown=10001:10001 deploy/Caddyfile /etc/caddy/Caddyfile
RUN mkdir -p /data/caddy /config/caddy && chown -R 10001:10001 /data /config
USER 10001:10001
