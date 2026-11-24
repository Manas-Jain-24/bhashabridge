# Single-server production deployment

Use Docker Engine with Compose v2 and BuildKit, a domain pointed at the host, and inbound TCP 80 and 443. The proxy serves the built React app and forwards `/api/*` on the same origin. PostgreSQL and the API have no host ports. The migrator and the API use separate database roles. The existing `docker-compose.yml` provides loopback-only development infrastructure.

## Configure and start

```sh
umask 077
cp .env.production.example .env.production
mkdir -p models
chmod 0755 models
openssl rand -hex 32
```

Generate a separate random value for `AUTH_RATE_SECRET`, `POSTGRES_PASSWORD`, and `BB_DB_PASSWORD`. Configure `MIGRATION_DATABASE_URL` with the owner and `DATABASE_URL` with the API role. Percent-encode passwords in URLs or use generated hex values. Set `PUBLIC_HOST` and the canonical HTTPS `PUBLIC_ORIGIN`. Keep the environment file at mode `0600` and outside build contexts.

```sh
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.production.yml up --build --detach --wait
curl --fail https://learn.example.org/api/health/ready
docker compose --env-file .env.production -f compose.production.yml exec -T api python scripts/deployment_check.py
```

Compose waits for PostgreSQL, runs the versioned migration and catalog seed, and waits for API and proxy health. Public HTTPS requires working DNS and Caddy certificate issuance. Set `BB_IMAGE_TAG` to the release identifier and record the Git and image digests. Rehearse upgrades on a restored copy and schedule a maintenance window for production schema changes.

The role bootstrap runs when initializing a new PostgreSQL volume. For an existing volume, the database owner provisions the API role, grants CONNECT and schema USAGE, grants table SELECT/INSERT/UPDATE/DELETE and sequence USAGE/SELECT, and sets the same default privileges for future tables and sequences. The migration leaves existing rows in place. Existing SQLite databases can be upgraded for development. Transferring learner data from SQLite to PostgreSQL needs a staged transfer and integrity review.

## Invite users and reviewers

```sh
docker compose --env-file .env.production -f compose.production.yml exec -T api \
  python scripts/issue_invitation.py --username learner_name
```

Share the username and invitation privately. The token is bound to that username, expires after 24 hours by default, and is consumed by successful signup. Set `ALLOW_REGISTRATION=false` to pause enrollment. To grant reviewer access, run `python scripts/review_workflow.py set-reviewer --username NAME` inside the API service.

## Select inference capabilities

The sample uses the core image in local mode. It serves reviewed and modular Hindi–Marathi translation, rule transliteration, and learning features. Unreviewed Bengali translation directions need verified IndicTrans2 weights or opted-in hybrid assistance. If neither produces a result, the API returns 503 and the application remains ready.

For neural inference, use `BB_BACKEND_TARGET=neural` on Linux x86-64 with the CPU dependency lock. Provision exact model commits outside the application, review executable model code, and use regular files and Safetensors weights. Place the following manifest and snapshots under the directory mounted at `/models`:

```json
{
  "models": {
    "ai4bharat/indictrans2-indic-indic-dist-320M": {
      "directory": "indictrans2",
      "revision": "<40 lowercase hex digits>",
      "sha256": {"config.json": "<sha256>", "model.safetensors": "<sha256>"}
    }
  }
}
```

Include every snapshot file in the checksum map, including tokenizer and reviewed Python files. Set `MODEL_MANIFEST=/models/manifest.json` and `MODEL_MANIFEST_SHA256` to the manifest’s approved digest. Make the files readable by UID 10001 and mount them read-only. Provision M2M100 similarly when selecting that engine. Use a separate download environment for gated models.

For hybrid mode, set `TRANSLATION_MODE=hybrid`, supply a Gemini key, and configure both application quotas and provider billing limits. Learners can choose Local model. Review provider privacy terms before enabling it. Start capacity planning for one IndicTrans2 CPU worker at **4 vCPU, 8–16 GiB RAM, and 20–40 GiB free disk**, plus backup storage. Measure warm and cold latency, memory and disk usage before serving traffic. Keep one API worker until model capacity has been measured.
