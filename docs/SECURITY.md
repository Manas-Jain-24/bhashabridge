# Security and privacy

Production validates the PostgreSQL configuration, canonical HTTPS origin, HTTP host, secure cookies, and authentication rate-limit secret. The reverse proxy overwrites the forwarded client address. The API accepts that header only from the configured private proxy IP. Authenticated mutations also require a session-bound CSRF header. Password hashes use scrypt, and session and CSRF tokens are stored as hashes. Login rotates the current session. Logout and account deletion revoke server-side sessions.

Production registration uses username-bound invitations. Review access is assigned through the operator CLI. Learning operations use the account ID from the session. Reviewers can access other accounts’ submitted reports for moderation. Login uses generic credential errors and separate per-address and per-username limits.

Production application logs record request IDs, route templates, status, latency and failure classes. Disable access logs in the proxy and Uvicorn configuration. Restrict access to operator exports, deployment configuration, database backups and provider keys. Protect backups and exports with encryption.

Hybrid requests can send learner text to Gemini. Local-only translation disables those calls. Learner-initiated browser speech recognition may use the browser vendor’s service. Browser and vendor processing are subject to their terms. Review those terms before offering production speech and cloud features.

Account deletion clears owned learning data and credentials. An anonymized actor ID remains on reviews of other learners’ corrections. Previously published contributions and data in retained backups can persist. Review publication and request handling with the operator. Publication requires contributor consent and review. Dataset licenses and provenance are recorded in [data/README.md](../data/README.md).

Account recovery and email verification require an operator procedure. Model checks enforce schema, provenance and some entity invariants. Independently reviewed evaluation is needed to establish semantic quality. Report suspected vulnerabilities privately to the deployment operator or repository owner with the affected version, a request ID if available, and synthetic inputs.
