# Operating BhashaBridge

## PostgreSQL production operations

Use [Deployment](DEPLOYMENT.md) for production configuration and database roles. Use a separate target for recovery drills. The SQLite commands below apply to development.

```sh
umask 077
docker compose --env-file .env.production -f compose.production.yml exec -T postgres \
  sh -ec 'pg_dump --username "$POSTGRES_USER" --format=custom "$POSTGRES_DB"' > backup.dump
sha256sum backup.dump
docker compose --env-file .env.production -f compose.production.yml exec -T postgres \
  sh -ec 'createdb --username "$POSTGRES_USER" bhashabridge_restore_drill'
docker compose --env-file .env.production -f compose.production.yml exec -T postgres \
  sh -ec 'pg_restore --username "$POSTGRES_USER" --exit-on-error --dbname=bhashabridge_restore_drill' < backup.dump
```

Encrypt backups and transfer an encrypted copy off host. Start with daily backups and 30 days of retention, adjusted to recovery and privacy requirements. Back up role configuration separately. Check schema versions, counts, login, and learning state after restore. Record recovery time and verify backup expiry. Roll back to a compatible prior image when possible. Otherwise restore into a new database and reconcile writes made since the backup before switching traffic.

Monitor HTTPS and `/api/health/ready`, database pool use, backup age, inference latency, saturation, and error counts. An authenticated reviewer can read `/api/operations/metrics`. Include request IDs and aggregate counts in alerts. Metrics reset on restart. Record `docker stats` under representative load and budget for compute, disk, backups, and opted-in provider traffic. Application quotas bound attempts. Set a provider billing limit separately.

Schedule `python scripts/maintenance.py` inside the API service. Review the preview before enabling `--apply`, which removes expired sessions, invitations, quota windows, and practice issues.

The default remains a local workspace. Account mode, migrations and bounded
provider usage are implemented; a public deployment still needs a host, TLS,
load testing and an operator. No production deployment is implied by CI passing.

## Local and shared environments

Use separate databases and environment files for development, tests, staging
and production. Tests and browser CI create disposable databases. Never point a
test server at a learner database. Keep `.env`, databases, backups, session cookies
and account exports outside Git. `backend/.env.example` lists supported settings.

For local account testing set `AUTH_MODE=accounts` and restart the backend.
The UI then offers registration/sign-in. The existing local profile stays intact;
new accounts have separate progress, arcade sessions, reports and rewards.
Production uses the dedicated environment template and HTTPS proxy described in
[Deployment](DEPLOYMENT.md). The Vite development proxy preserves Host for local use.
Cookie authentication uses opaque random session tokens, hashed server-side,
HttpOnly session cookies, SameSite=Strict and a CSRF header on mutations. Passwords
use scrypt N=32768, r=8, p=3 with random salts, one of the configurations in the
[OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
Sessions expire after 24 hours by default and are revoked on sign-out/deletion.
There is no email verification or self-service password recovery yet; do not
promise those capabilities to users.

## Database lifecycle and rollback

SQLite remains available for local development. Run one production API process
initially; additional workers multiply model memory and inference capacity.
Database-backed quotas coordinate workers, while model locks, circuit breakers
and metrics are process-local.

Before changing code/schema, stop accepting writes and take a backup. The SQLite
online backup API includes committed WAL contents. Commands refuse to overwrite
an existing destination:

```powershell
python scripts/database_ops.py backup --source backend/bhashabridge.db --destination .demo/backups/before-upgrade.db
python scripts/database_ops.py drill --source .demo/backups/before-upgrade.db --destination .demo/backups/restore-drill.db
```

Each command verifies integrity and writes a manifest with table counts and a
SHA-256 hash. Backups contain personal data and authentication material; restrict
access and define retention. Use the PostgreSQL backup commands above for production.

The migrator applies ordered revisions before seeding. Version 1 introduced authentication,
review, quota and practice-ownership tables. Version 2 adds invitations, correction
publication consent, user sequence alignment and history indexes. Apply new revisions
through the migrator. Readiness requires the expected schema history.

Rehearse an upgrade on a restored **staging copy** first, then run:

```powershell
python scripts/deployment_check.py
python -m pytest backend/tests -q
```

The readiness command is read-only and prints no credentials. It intentionally
fails in local development mode. It does not certify TLS, translation accuracy
or production capacity. For rollback, stop writes, start the previous code/model
artifact with a compatible restored database at a **new** path, check health and
two-account isolation, then switch traffic. Never overwrite a live database or
discard writes made after a backup without an explicit recovery decision.

## Limits and observability

`GET /api/health` distinguishes a configured provider from its last actual success
or failure. Those observations reset on process restart. `GET /api/operations/metrics`
requires the local operator or reviewer role and exposes the last 2,000 request
timings, cold/warm slices, stage distributions, context failures and fallback
counts. It contains no raw sentences or credentials. Export aggregate metrics
to external monitoring before scaling; this is not a durable monitoring system.

The overall deadline includes model loading and inference. A request returns 504
at its time budget; later cloud stages cannot start after that deadline. Python
cannot safely kill an in-flight native model thread: its worker slot remains
occupied until it exits, and excess work receives 503 instead of queueing without
bound. A hung native library requires an operator restart. Process isolation would
be the next step if hard worker termination becomes a deployment requirement.

Provider limits count reserved attempts, including failures, across translation,
tutor and gloss routes. They enforce global/per-account daily call caps and output
token caps, **not an exact currency ceiling**. Provider rates and input costs vary;
configure a billing/project cap with the provider as well. Zero cloud budgets
disable network assistance. Local mode and labelled fallbacks remain available.

The optional GitHub workflow is manual, takes 1–6 calls, uses no retries and needs
a repository `GEMINI_API_KEY` secret. Regular CI does not need credentials or neural
downloads. A local equivalent is:

```powershell
python scripts/live_provider_smoke.py --max-calls 3 --output output/provider-smoke.json
```

Expired sessions, rate windows and issued practice questions can be pruned without
deleting learning history. Preview counts first; `--apply` makes the change:

```powershell
python scripts/maintenance.py
python scripts/maintenance.py --apply
```

Account settings provide export and password-confirmed deletion. Exports omit
credentials and active game answer keys, and include the owner's correction audit
history. Deletion anonymizes an actor identifier retained in other users' review
audits. Publish these retention rules before inviting real users.
