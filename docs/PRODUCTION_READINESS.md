# Production readiness verification

**Verdict: incomplete.** Verification used a disposable workspace and synthetic accounts. The core, proxy and PostgreSQL images built, but the workspace Docker daemon exhausted its VFS storage while creating the deployment containers. The complete HTTPS Compose journey, hardware sizing and live provider verification remain release gates.

| Check | Status | Evidence |
| --- | --- | --- |
| Backend unit and API integration tests | PASS | 282 passed, 30 skipped, one Starlette TestClient deprecation warning in 105.69 seconds. Skips include four PostgreSQL tests run separately below. |
| Final focused backend run | PASS | 62 passed, one skipped, and the same warning in 29.80 seconds after the logging changes. A separate production-mode ASGI probe returned 404 for the three documentation routes. |
| Production settings, invitations, account scope, CSRF and session expiry | PASS | Regression cases cover unsafe settings, strict host and origin, invitation binding and reuse, reviewer escalation, cookie rotation and expiry. |
| PostgreSQL migration and concurrent writes | PASS | Four tests passed against disposable PostgreSQL 16. Covered unversioned and v1 upgrades, preservation of a legacy row, user sequence alignment, concurrent quota admission, concurrent first vocabulary review, account separation and logout. |
| PostgreSQL recovery fixture | PASS | A real custom-format `pg_dump` was restored to a separate database and the restored fixture row matched. |
| Frontend build | PASS | TypeScript and Vite completed successfully. |
| Development browser journeys | PASS | Six Playwright journeys passed in 32.9 seconds. The outage and malformed-response cases inject failures. The backend uses disposable SQLite and test model settings. |
| Production Compose config and core image build | PASS | Compose and Caddy configuration validated. The core, proxy and PostgreSQL images built during verification, before final source fixes. The build used the workspace CA as a transient build secret. |
| Compose startup, persistent storage across restart and production HTTPS browser journeys | BLOCKED | Docker refused to create the full stack because it ran out of VFS storage. Run `python scripts/test_production_stack.py --browser` on a host with sufficient capacity. |
| Local-only provider isolation and fault injection | PASS | Regression tests exercise local-only and simulated provider timeout, quota, invalid structured output and fallback behavior. |
| Live Gemini hybrid, provisioned neural inference and neural quality benchmark | NOT TESTED | Requires authorized provider calls, verified model weights and a suitable runtime. |
| Deployment load, cold/warm resource usage and off-host recovery | NOT TESTED | Requires a deployment-sized host, production weights and an operator-owned backup target. |
| Dataset and language structure checks | PASS | Five commands succeeded. Expanded, v1, and v2 checks verified 7, 3, and 5 hashes and detected zero overlap under their respective assertions. Human language-quality review remains pending. |
| Core dependency advisories | PASS | `pip-audit` reported no known vulnerabilities in the core lock. `npm audit` reported zero vulnerabilities. The optional neural lock and container OS layers need separate advisory scans. |
| Git secret scan | PASS | Gitleaks reported zero findings in 14 baseline commits and in the staged implementation. |
| GitHub Actions for these changes | NOT TESTED | Workflows are configured. A completed run for this branch has yet to be observed. |

## Translation measurements

The modular engine ran against the existing 219-item Hindi–Marathi diagnostic set in each direction. The set contains suspected reference misalignments. These scores describe that engine and benchmark only.

| Direction | BLEU | chrF++ | Normalized exact match |
| --- | ---: | ---: | ---: |
| Hindi → Marathi | 2.06 | 19.52 | 0.91% |
| Marathi → Hindi | 1.92 | 20.03 | 0.91% |

After an initial timed-out run, the frozen six-direction runtime diagnostic completed **480 requests** in local mode on the workspace CPU with neural weights absent. Each direction used 40 native and 40 Roman inputs. Here, p95 includes error responses. The Bengali results measure missing-model behavior, and the draft set lacks reviewed references for an accuracy score.

| Direction | Successful responses | HTTP 503 | p95 |
| --- | ---: | ---: | ---: |
| Hindi → Marathi | 80/80 | 0 | 18 ms |
| Marathi → Hindi | 80/80 | 0 | 19 ms |
| Hindi → Bengali | 0/80 | 80 | 3 ms |
| Marathi → Bengali | 0/80 | 80 | 2 ms |
| Bengali → Hindi | 0/80 | 80 | 3 ms |
| Bengali → Marathi | 0/80 | 80 | 3 ms |

The protected-value comparison reported zero changes across the 160 successful requests. The evaluator checks identifiers and numbers. Human adequacy and broader entity preservation remain separate checks. The opt-in neural evaluator reports per-direction exact match, CER/WER, BLEU, chrF++, identifiable-value preservation, elapsed time and failure rate. Model promotion still requires the project’s existing gates.

## Repeat the release checks

```sh
python -m pytest backend/tests -q
python scripts/check_corpus_leakage.py
python scripts/check_expanded_data.py
python scripts/check_language_readiness.py
python scripts/prepare_translation_quality.py --audit
python scripts/prepare_translation_quality_v2.py --audit
python ml/evaluation/eval_translation.py --engine modular --output output/production-modular.json
cd frontend && npm ci && npm run build && npm run test:e2e -- journeys.spec.ts
```

Run the PostgreSQL integration suite with `BB_TEST_POSTGRES_URL` set to a disposable database, and run the full Compose browser and recovery drill from the repository root on a larger host. See [Deployment](DEPLOYMENT.md), [Security](SECURITY.md), and [Operations](OPERATIONS.md).
