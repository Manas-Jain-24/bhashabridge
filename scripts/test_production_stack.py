"""Run the production stack with a disposable database and locally trusted TLS."""

import argparse
import base64
import concurrent.futures
import hashlib
import http.cookiejar
import json
import os
import re
import secrets
import socket
import ssl
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
TEST_PASSWORD = "A synthetic production test password!"


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def run_stack(scratch, browser):
    project = "bb-smoke-" + secrets.token_hex(5)
    port = free_port()
    origin = f"https://localhost:{port}"
    owner, app = secrets.token_hex(20), secrets.token_hex(20)
    models = scratch / "models"
    models.mkdir(mode=0o755)
    models.chmod(0o755)
    config = scratch / "smoke.env"
    config.write_text(
        "\n".join(
            (
                f"PUBLIC_ORIGIN={origin}",
                "PUBLIC_HOST=localhost",
                "BB_BIND_ADDRESS=127.0.0.1",
                f"BB_HTTP_PORT={free_port()}",
                f"BB_HTTPS_PORT={port}",
                "CADDY_TLS_DIRECTIVE=tls internal",
                f"AUTH_RATE_SECRET={secrets.token_hex(32)}",
                f"POSTGRES_PASSWORD={owner}",
                f"BB_DB_PASSWORD={app}",
                f"DATABASE_URL=postgresql+psycopg://bhasha_app:{app}@postgres/bhashabridge",
                f"MIGRATION_DATABASE_URL=postgresql+psycopg://bhasha_owner:{owner}@postgres/bhashabridge",
                f"BB_MODEL_DIR={models}",
                "TRANSLATION_MODE=local",
                "GEMINI_API_KEY=",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    config.chmod(0o600)
    command = [
        "docker",
        "compose",
        "--project-name",
        project,
        "--env-file",
        str(config),
        "-f",
        str(ROOT / "compose.production.yml"),
    ]
    override = scratch / "smoke-overrides.json"
    environment = {
        "services": {
            name: {"volumes": ["smoke_models:/models:ro"]}
            for name in ("api", "migrate")
        },
        "volumes": {"smoke_models": {}},
    }
    image_project = os.getenv("BB_SMOKE_IMAGE_PROJECT")
    if image_project:
        if not re.fullmatch(r"bb-smoke-[0-9a-f]{10}", image_project):
            raise ValueError("Use the name of a previous disposable smoke build")
        for name in ("postgres", "proxy"):
            environment["services"].setdefault(name, {})["image"] = (
                f"{image_project}-{name}"
            )
    if ca_file := os.getenv("BB_BUILD_CA_FILE"):
        for name in ("api", "migrate", "proxy"):
            environment["services"].setdefault(name, {})["build"] = {
                "secrets": ["build_ca"]
            }
        environment["secrets"] = {
            "build_ca": {"file": str(Path(ca_file).resolve(strict=True))}
        }
    override.write_text(json.dumps(environment), encoding="utf-8")
    command.extend(("-f", str(override)))

    def compose(*args, capture=False, **kwargs):
        return subprocess.run(
            command + list(args),
            cwd=ROOT,
            check=True,
            capture_output=capture,
            text=True,
            **kwargs,
        )

    def invite(username):
        return compose(
            "exec",
            "-T",
            "api",
            "python",
            "scripts/issue_invitation.py",
            "--username",
            username,
            capture=True,
        ).stdout.strip()

    try:
        compose("config", "--quiet")
        compose(
            "up",
            "--no-build" if image_project else "--build",
            "--detach",
            "--wait",
            "--wait-timeout",
            "180",
        )
        cert = scratch / "root.crt"
        compose("cp", "proxy:/data/caddy/pki/authorities/local/root.crt", str(cert))
        context = ssl.create_default_context(cafile=str(cert))
        jar = http.cookiejar.CookieJar()
        client = build_opener(HTTPSHandler(context=context), HTTPCookieProcessor(jar))

        def api(path, data=None, *, origin_header=origin, method=None, csrf=True):
            headers = {"Content-Type": "application/json"}
            if origin_header:
                headers["Origin"] = origin_header
            if csrf:
                token = next(
                    (cookie.value for cookie in jar if cookie.name == "bb_csrf"), ""
                )
                if token:
                    headers["X-CSRF-Token"] = token
            request = Request(
                origin + path,
                data=json.dumps(data).encode() if data is not None else None,
                headers=headers,
                method=method,
            )
            try:
                response = client.open(request, timeout=70)
            except HTTPError as error:
                response = error
            with response:
                return response.status, response.headers, json.load(response)

        assert api("/api/health/live")[0] == 200
        assert api("/api/health/ready")[2] == {"status": "ready"}
        assert api("/api/progress")[0] == 401
        credentials = {"username": "smoke_learner", "password": TEST_PASSWORD}
        credentials["invitation_token"] = invite(credentials["username"])
        assert re.fullmatch(r"[A-Za-z0-9_-]{43}", credentials["invitation_token"])
        assert api("/api/auth/register", credentials, origin_header=None)[0] == 403
        status, headers, registered = api("/api/auth/register", credentials)
        assert status == 201 and registered["role"] == "learner"
        cookie = next(
            value
            for value in headers.get_all("Set-Cookie")
            if value.startswith("bb_session=")
        )
        assert all(
            flag in cookie.lower() for flag in ("httponly", "secure", "samesite=strict")
        )
        assert api("/api/auth/register", credentials)[0] == 403
        assert (
            api("/api/progress/bridge-mode", {"mode": "beginner"}, csrf=False)[0] == 403
        )
        assert api("/api/progress/bridge-mode", {"mode": "beginner"})[0] == 200
        status, _, translation = api(
            "/api/analyze",
            {
                "text": "Mujhe paani chahiye",
                "source_language": "hindi",
                "target_language": "marathi",
                "translation_mode": "local",
            },
        )
        assert (
            status == 200
            and translation["translation_native"]
            and translation["context_status"] in ("reviewed", "local_only")
        )
        unsupported = api(
            "/api/translate",
            {
                "text": "আমি এখন স্কুলে যাব।",
                "source_language": "bengali",
                "target_language": "hindi",
                "translation_mode": "hybrid",
            },
        )
        assert unsupported[0] == 503, unsupported
        assert api("/api/health/ready")[0] == 200
        vocabulary = api("/api/vocabulary/review?limit=1")[2][0]
        word_id = vocabulary.get("word_id") or vocabulary["id"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(
                pool.map(
                    lambda _: api(
                        f"/api/vocabulary/review/{word_id}", {"rating": "good"}
                    )[0],
                    range(2),
                )
            )
        assert sorted(statuses) == [200, 409], statuses
        print(
            "HTTPS, invite signup, secure cookies, CSRF, local fallback and concurrent SRS verified.",
            flush=True,
        )

        compose("restart", "postgres")
        compose("up", "--detach", "--wait", "--wait-timeout", "180")
        assert api("/api/auth/me")[2]["id"] == registered["id"]
        assert api("/api/progress")[2]["bridge_mode_level"] == "beginner"
        compose(
            "exec",
            "-T",
            "postgres",
            "sh",
            "-ec",
            """
            pg_dump --username "$POSTGRES_USER" --format=custom --file=/tmp/bb-drill.dump "$POSTGRES_DB"
            createdb --username "$POSTGRES_USER" bb_recovery_drill
            pg_restore --username "$POSTGRES_USER" --exit-on-error --dbname=bb_recovery_drill /tmp/bb-drill.dump
            test "$(psql --username "$POSTGRES_USER" --dbname=bb_recovery_drill -Atc 'SELECT max(version) FROM schema_versions')" = 2
            test "$(psql --username "$POSTGRES_USER" --dbname=bb_recovery_drill -Atc 'SELECT count(*) FROM account_credentials')" = 1
            test "$(psql --username "$POSTGRES_USER" --dbname=bb_recovery_drill -Atc 'SELECT count(*) FROM vocabulary_reviews')" = 1
        """,
        )
        print(
            "PostgreSQL restart, persistent session and pg_dump/pg_restore verified.",
            flush=True,
        )
        if browser:
            with socket.create_connection(("localhost", port), timeout=5) as connection:
                with context.wrap_socket(
                    connection, server_hostname="localhost"
                ) as tls:
                    leaf = tls.getpeercert(binary_form=True)
            public_key = subprocess.run(
                ["openssl", "x509", "-inform", "DER", "-pubkey", "-noout"],
                input=leaf,
                capture_output=True,
                check=True,
            ).stdout
            spki = subprocess.run(
                ["openssl", "pkey", "-pubin", "-outform", "DER"],
                input=public_key,
                capture_output=True,
                check=True,
            ).stdout
            pin = base64.b64encode(hashlib.sha256(spki).digest()).decode()
            browser_env = {
                **os.environ,
                "BB_PRODUCTION_ORIGIN": origin,
                "BB_TEST_TLS_SPKI": pin,
                "BB_BROWSER_INVITATION": invite("browser_learner"),
            }
            subprocess.run(
                ["npm", "run", "test:e2e", "--", "production.spec.ts"],
                cwd=ROOT / "frontend",
                env=browser_env,
                check=True,
            )
        assert api("/api/auth/logout", {})[0] == 200
        assert api("/api/auth/me")[0] == 401
    except Exception:
        compose("ps", "--all")
        compose("logs", "--tail", "20")
        raise
    finally:
        # The project name and all volumes above belong only to this run.
        compose("down", "--volumes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true")
    args = parser.parse_args()
    tmp = ROOT / ".pytest_tmp"
    tmp.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="production-smoke-", dir=tmp) as directory:
        run_stack(Path(directory), args.browser)
