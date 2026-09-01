<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# Phase 0 Audit & Remediation Report (V4)

## 1. System & Deployment Baseline

- **Operating System**: Linux Mint 22.3 (Zena) / Ubuntu 24.04 (Noble), Kernel `7.0.0-30-generic x86_64`
- **Baseline Git Commit**: `ac3c158c41` (Pinned upstream `master` commit)
- **Base Docker Image**: `apachesuperset.docker.scarf.sh/apache/superset:latest-dev` (`sha256:25015af8efd5ff63bf33f74a7fe963d59837e0431305add2767ad3bd7dcfa6c9`)
- **Metadata Database Engine**: PostgreSQL 17 (`postgres:17`, `sha256:7958605b474b...`), volume `superset_db_home`, 53 tables, Alembic version `4b2a8c9d3e1f`
- **Cache & Message Broker**: Redis 7 (`redis:7`, `sha256:e9b2e45ecd47...`), volume `superset_redis`
- **Host Toolchains**: Python `3.12.3`, Node.js `v22.23.2`, npm `10.9.8`
- **Container Python**: Python `3.11.14`

---

## 2. Decision on Pre-Existing Modified Files (`SUPERSET_DASHBOARD_POSITION_DATA_LIMIT`)

### Investigation of Actual Database Payload Sizes
A SQL analysis of all 17 dashboards in the PostgreSQL metadata database was conducted to determine the actual serialized size distribution of the `position_json` layout column:

```sql
SELECT id, slug, dashboard_title, octet_length(position_json) AS bytes, round(octet_length(position_json) / 1024.0, 2) AS kb
FROM dashboards ORDER BY bytes DESC;
```

**Query Results**:
- **Dashboard ID 16** (`🏢 Cohort Intelligence Hub [copy]`): `124,247` bytes (**121.33 KB**)
- **Dashboard ID 1** (`🏢 Cohort Intelligence Hub`): `124,074` bytes (**121.17 KB**)
- **Dashboard ID 10** (`FCC New Coder Survey 2018`): `13,906` bytes (13.58 KB)
- **Remaining 14 Dashboards**: 730 bytes – 9,131 bytes (0.71 KB – 8.92 KB)
- **Dashboards exceeding default 65,535 bytes (64 KB)**: **2 dashboards (11.8%)**

### Explicit Decision: KEEP MODIFICATIONS
- **Decision**: **KEEP** `SUPERSET_DASHBOARD_POSITION_DATA_LIMIT=1048576` (1 MB) in `docker/.env` and `docker/pythonpath_dev/superset_config.py`.
- **Reasoning**: Two active dashboards currently in the metadata database exceed the default 64 KB limit by nearly 2x (121 KB). Reverting this setting would cause layout save failures on existing enterprise dashboards. The underlying database column in PostgreSQL is `TEXT` (1 GB max) and in MySQL `MEDIUMTEXT` (16 MB max), making 1 MB safe and appropriate.

---

## 3. Upstream Divergence Check

- **Git Remote**: `https://github.com/apache/superset`
- **Upstream Comparison**: `git log HEAD...origin/master` confirms exact parity at commit `ac3c158c41`.
- **"Subjects" Migration**: Upstream commit `33f0fc93edfa` (PR #38831) by Ville Brofeldt introduced Subject-Based Access Control (`ENABLE_VIEWERS`) to master. This is an upstream feature, not a custom fork.
- **"bi_owner" Entry**: A pre-configured database connection row in the metadata database (`public.dbs` table) referencing `postgresql+psycopg2://bi_owner:***@db_bi:5432/bi`.

---

## 4. Live Risk Remediation: `superset_pgadmin` Container

- **Origin**: Launched by a legacy compose file at `/home/bi-tool-ryobilao/Desktop/bi_tool/superset/docker-compose-image-tag.yml`.
- **Finding**: Bound to `0.0.0.0:5050` with default credentials on the `superset_default` network.
- **Action Taken**: Container `superset_pgadmin` was **STOPPED** to eliminate live network exposure. Confirmed with `docker ps` and `docker inspect superset_pgadmin`.
- **Project Scope**: pgAdmin is declared **OUT OF SCOPE** for Superset core and visual plugin development.

---

## 5. Endpoint Verification: WSGI-REACHABLE (In-Process)

Because the `superset` web container is currently stopped due to the base image dependency mismatch, API routes were evaluated via Flask's in-process `test_client()` within an ephemeral Python test runner.

### Status Classification Definitions
- **REGISTERED**: Route exists in Flask `url_map` / OpenAPI schemas.
- **WSGI-REACHABLE (in-process)**: In-process WSGI call successfully dispatches through Flask and returns an HTTP status code.
- **NETWORK-REACHABLE (live HTTP)**: Verified via real external HTTP network requests (`curl`) against a container in the `Up` state.
- **AUTHENTICATED**: Dispatches within a validated user security context.
- **FUNCTIONALLY VERIFIED**: End-to-end CRUD / query execution verified against persistent test data.

### WSGI Test Results

| Target Endpoint | Method | Path | Status Classification | Result |
| :--- | :---: | :--- | :---: | :--- |
| **Health Check** | `GET` | `/health` | **WSGI-REACHABLE (in-process)** | HTTP `200 OK` (Body: `"OK"`) |
| **Login** | `POST` | `/api/v1/security/login` | **WSGI-REACHABLE (in-process)** | HTTP `200 OK` (JWT token returned, redacted) |
| **CSRF Token** | `GET` | `/api/v1/security/csrf_token/` | **WSGI-REACHABLE (in-process)** | HTTP `401 Unauthorized` (unauthenticated) |
| **Chart CRUD** | `GET` | `/api/v1/chart/` | **REGISTERED / WSGI-REACHABLE** | HTTP `401 Unauthorized` (unauthenticated) |
| **Chart Data** | `POST` | `/api/v1/chart/data` | **REGISTERED / WSGI-REACHABLE** | HTTP `401 Unauthorized` (unauthenticated) |
| **Dashboard CRUD** | `GET` | `/api/v1/dashboard/` | **REGISTERED / WSGI-REACHABLE** | HTTP `401 Unauthorized` (unauthenticated) |
| **Dataset CRUD** | `GET` | `/api/v1/dataset/` | **REGISTERED / WSGI-REACHABLE** | HTTP `401 Unauthorized` (unauthenticated) |
| **Database CRUD** | `GET` | `/api/v1/database/` | **REGISTERED / WSGI-REACHABLE** | HTTP `401 Unauthorized` (unauthenticated) |
| **Row Level Security** | `GET` | `/api/v1/rowlevelsecurity/` | **REGISTERED / WSGI-REACHABLE** | HTTP `401 Unauthorized` (unauthenticated) |
| **Embedded Dashboard** | `GET` | `/api/v1/embedded_dashboard/<uuid>` | **REGISTERED** | Declared in URL map; pending guest token fixture |
| **FastMCP Service** | FastMCP | `superset.mcp_service` (41 tools) | **REGISTERED** | Discovered via `superset.core.mcp.core_mcp_injection` |

*Note*: Authenticated database operations fail with `psycopg2.errors.UndefinedTable: relation "subjects" does not exist` because Alembic migration `b1c2d3e4f5a6` is unapplied in the database volume. These will become **FUNCTIONALLY VERIFIED** once migrations are executed in Phase 0.5.

---

## 6. Dependency Conflict & Ephemeral Diagnostic Record

- **Baseline Failure**: The base Docker image contains `sqlalchemy==1.4.54`, while repository `pyproject.toml` mandates `sqlalchemy>=2.0.52,<2.1` and `apache-superset-core>=0.1.0`. In `docker-bootstrap.sh:L31`, `uv pip install -e .` fails dependency resolution against PyPI.
- **Ephemeral Interventions**: To inspect Flask URL maps during Phase 0, temporary packages (`apache-superset-core==0.1.0` editable, `sqlalchemy==2.0.52`, `flask-sqlalchemy==3.1.1`, `marshmallow-sqlalchemy==1.5.0`) were installed strictly within disposable test containers (`superset-superset-init-run-*`) and discarded.
- **Zero Repo Mutation**: No application source code, requirements files, or persistent Docker images were modified.

---

## 7. Phase 0.5 — Reproducible Baseline Repair (Hard Blocker)

To establish an immutable, reproducible baseline before any plugin or feature development:

- **Stage**: Phase 0.5 — Reproducible Baseline Repair
- **Prerequisite**: Phase 0 approval.
- **Gating Requirements**:
  1. Update `docker-bootstrap.sh` to install editable workspace packages with `--no-deps`.
  2. Build a reproducible local Docker image layer pinned to commit `ac3c158c41` with all required SQLAlchemy 2.0 dependencies.
  3. Execute `superset db upgrade` to apply pending schema migration `b1c2d3e4f5a6` (`add_subjects_tables`).
  4. Verify that `docker compose up` starts cleanly with `superset`, `superset-worker`, and `superset-worker-beat` reaching a verified `Up` state.
  5. Verify live HTTP health check `GET http://localhost:8088/health` returns HTTP 200 via network `curl`.
- **Scope Restriction**: No visualization plugins or application feature code will be developed in Phase 0.5.

---

## 8. Production Security Baseline Matrix

| Security Domain | Current Audit State | Production Standard | Risk Severity | Remediation Plan (Phase 9) |
| :--- | :--- | :--- | :--- | :--- |
| **`SECRET_KEY`** | Default dev secret ([REDACTED] - 19 bytes, triggers RFC 7518 HMAC warning) | Cryptographically random 64-byte secret from external secret store (Vault / AWS SSM) | **CRITICAL** | Rotate to generated 256-bit key via environment variable `SUPERSET_SECRET_KEY` before staging. |
| **Container User Privileges** | Containers run as `root` (UID 0) in `docker-compose.yml` (`superset`, `superset-init`, `superset-worker`) | Non-root execution (`USER superset:superset`, UID 10001) with dropped Linux capabilities | **HIGH** | Refactor Docker Compose / Helm templates to enforce non-root execution (`runAsNonRoot: true`). |
| **`superset_pgadmin` Exposure** | Container stopped; previously bound to `0.0.0.0:5050` with default credentials | Disabled in production or bound strictly to `127.0.0.1` behind VPN/SSO with strong credentials | **HIGH** | Remove pgAdmin from stack or restrict to internal loopback only; rotate credentials. |
| **Session Security** | Standard Flask cookie session, HTTP-only enabled | `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_SAMESITE = 'Lax'` | **HIGH** | Enforce secure cookie flags in `superset_config.py` when TLS is terminated. |
| **Cookie Flags** | `SECURE` flag not enforced on HTTP | Mandatory `Secure` attribute on all session and CSRF cookies | **HIGH** | Set `SESSION_COOKIE_SECURE = True` in production configuration. |
| **TLS / SSL** | Plain HTTP on ports 80, 8088, 9000, 8080 | Mandatory TLS 1.3 / HTTPS termination at reverse proxy / Ingress | **CRITICAL** | Terminate TLS via Nginx / AWS ALB with HSTS header (`Strict-Transport-Security`). |
| **CSP / Talisman** | `FLASK_DEBUG=true` served with relaxed dev CSP (`'unsafe-eval'` for React Refresh / HMR) | Strict Content Security Policy blocking unsafe-inline, unsafe-eval, and untrusted frame ancestors | **HIGH** | Enforce production `TALISMAN_CONFIG` in `superset_config.py` with explicit nonce/hash support. |
| **CORS & CSRF** | `WTF_CSRF_ENABLED = True` (default); `ENABLE_CORS = False` | Strict CSRF protection with domain-scoped CORS allowlist | **MEDIUM** | Maintain CSRF enforcement; configure `CORS_OPTIONS` with explicit trusted origins. |
| **Guest Token Secret Separation** | Shares default secret key | Distinct dedicated `GUEST_TOKEN_JWT_SECRET` isolated from root `SUPERSET_SECRET_KEY` | **HIGH** | Define distinct dedicated `GUEST_TOKEN_JWT_SECRET` for embedded dashboard token signing. |
| **Default Credentials** | `admin` / default dev password | Force mandatory password reset on initial setup; enforce enterprise SSO (OAuth2/OIDC/SAML) | **CRITICAL** | Eliminate default dev passwords; configure OIDC / SAML authentication provider. |
| **Public Role Permissions** | FAB `Public` role has minimal default permissions | Read-only / no data access permissions on `Public` role (`PUBLIC_ROLE_LIKE_GAMMA = False`) | **HIGH** | Audit and lockdown all `ab_permission_view_role` entries assigned to `Public`. |
| **Database Least Privilege** | `superset` Postgres user owns public schema; direct DDL access | Superset app connects via restricted role (DML only, no superuser/drop database privileges) | **HIGH** | Separate migration runner credentials (DDL) from application runtime credentials (DML). |
| **Redis / DB Exposure** | Exposed on host interface `127.0.0.1:5432` and `127.0.0.1:6379` | Internal VPC / container network only; zero public or host port exposure | **MEDIUM** | Remove host port publishing for database and Redis in production compose/Helm manifests. |
| **Debug Mode** | `FLASK_DEBUG = true`, Werkzeug debugger disabled by default | `FLASK_DEBUG = false`, `SUPERSET_ENV = production`, Werkzeug debugger strictly disabled | **HIGH** | Set `FLASK_DEBUG=false` and `SUPERSET_ENV=production` in production environment files. |
| **Embedded Origins** | Open frame ancestors in development | Explicit `TALISMAN_CONFIG['frame_ancestors']` allowlist restricted to approved host domains | **HIGH** | Define strict domain allowlist for embedded dashboard iframes. |
| **Audit Logging** | Local container stdout logging | Structured JSON logs shipped to centralized SIEM / CloudWatch with automated alerting | **MEDIUM** | Configure structured JSON log formatting with secret redaction filters. |

---

## 9. Safe Rollback Procedures

Rollback uses explicit file paths rather than broad directory-wide deletion:

```bash
# 1. Pre-rollback status check
git status --short

# 2. Restore modified configuration files
git restore docker/.env docker/pythonpath_dev/superset_config.py

# 3. Explicitly remove only the documentation and evidence artifacts created for Phase 0
rm -f docs/phase-0-report-v3.md \
      docs/phase-0-report-v4.md \
      docs/preset-like-roadmap.md \
      docs/adr/ADR-001-preset-like-extensions-strategy.md \
      docs/evidence/docker-compose-rendered-redacted.yml \
      docs/evidence/environment-package-report.txt \
      docs/evidence/git-diff-redacted.txt \
      docs/evidence/redacted-command-output.txt \
      docs/evidence/security-baseline-redacted.md
```
