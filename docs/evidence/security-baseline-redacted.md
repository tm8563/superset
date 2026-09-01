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

# Production Security Baseline Audit & Gap Matrix

This document benchmarks the audited development configuration against Apache Superset enterprise production security standards.

---

## Security Baseline Matrix

| Security Domain | Current Audit State | Production Standard | Risk Severity | Remediation Plan (Phase 9) |
| :--- | :--- | :--- | :--- | :--- |
| **`SECRET_KEY`** | Default dev secret ([REDACTED] - 19 bytes, triggers RFC 7518 HMAC length warning) | Cryptographically random 64-byte secret from external secret store (Vault / AWS SSM) | **CRITICAL** | Rotate to generated 256-bit key via environment variable `SUPERSET_SECRET_KEY` before staging. |
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

## Authentication & Authorization Guardrails

1. **Authorized Query Path**: All data queries must route through `/api/v1/chart/data` or `/api/v1/dataset/` under the authenticated user session. Direct client-side SQL generation or parallel unauthenticated data endpoints are strictly forbidden.
2. **Row-Level Security (RLS)**: All supported query execution must use Superset's authorized query path under the originating user context. RBAC and RLS enforcement must be verified with positive and negative end-to-end tests.
3. **No Secret Ingestion**: Secrets (passwords, tokens, database URIs) must never be stored in Git repositories, log files, or frontend client bundles.
