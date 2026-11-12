# Operating BhashaBridge

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
Production configuration requires:

```dotenv
APP_ENV=production
AUTH_MODE=accounts
COOKIE_SECURE=true
ALLOW_SQLITE_FALLBACK=false
TESTING=false
USE_MOCK_MODELS=false
ALLOW_REGISTRATION=true
REQUESTS_PER_MINUTE=120
CLOUD_CALLS_PER_DAY=100
CLOUD_USER_CALLS_PER_DAY=25
GEMINI_MAX_OUTPUT_TOKENS=2048
REQUEST_TIMEOUT_SECONDS=60
INFERENCE_WORKERS=2
```

Set `DATABASE_URL` to the environment's database and `CORS_ORIGINS` to its exact
HTTPS application origin. Serve the built frontend and `/api` on the **same
origin**. Forward the original Host header to FastAPI; do not rewrite it to
localhost. Bind FastAPI to loopback/private networking. Configure trusted proxy
addresses explicitly; do not trust arbitrary forwarded client-IP headers.

The Vite development proxy preserves Host. It is not a production web server.
Cookie authentication uses opaque random session tokens, hashed server-side,
HttpOnly session cookies, SameSite=Strict and a CSRF header on mutations. Passwords
use scrypt N=32768, r=8, p=3 with random salts, one of the configurations in the
[OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
Sessions expire after 24 hours by default and are revoked on sign-out/deletion.
There is no email verification or self-service password recovery yet; do not
promise those capabilities to users.

## Database lifecycle and rollback

SQLite remains suitable for this single-machine application. Run one API process
initially; additional workers multiply model memory and inference capacity.
Database-backed quotas coordinate workers, while model locks, circuit breakers
and metrics are process-local. A database change cannot improve translation quality.

Before changing code/schema, stop accepting writes and take a backup. The SQLite
online backup API includes committed WAL contents. Commands refuse to overwrite
an existing destination:

```powershell
python scripts/database_ops.py backup --source backend/bhashabridge.db --destination .demo/backups/before-upgrade.db
python scripts/database_ops.py drill --source .demo/backups/before-upgrade.db --destination .demo/backups/restore-drill.db
```

Each command verifies integrity and writes a manifest with table counts and a
SHA-256 hash. Backups contain personal data and authentication material; restrict
access and define retention. Account deletion does not erase older backups.
Use database-native backup tools if choosing PostgreSQL later; this utility is
deliberately SQLite-only.

On startup, ordered migrations run before seeding. Version 1 adds authentication,
review, quota and practice-ownership tables without rewriting existing tables.
Future schema changes require a new numbered migration; `create_all` does not
upgrade existing columns. The app refuses a schema newer than it understands.

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
