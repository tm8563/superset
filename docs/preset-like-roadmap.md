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

# Preset-Like Capabilities Roadmap for Apache Superset

This roadmap tracks the phased development and integration of Preset-like enterprise features into a self-hosted Apache Superset deployment.

---

## 1. Immutable Baseline Specification

- **Baseline Git Commit**: `ac3c158c41` (Pinned upstream `master` commit)
- **Baseline Docker Image**: `apachesuperset.docker.scarf.sh/apache/superset:latest-dev` (`sha256:25015af8efd5ff63bf33f74a7fe963d59837e0431305add2767ad3bd7dcfa6c9`)
- **Metadata Database Engine**: PostgreSQL 17 (`postgres:17`, `sha256:7958605b474b...`)
- **Cache & Message Broker**: Redis 7 (`redis:7`, `sha256:e9b2e45ecd47...`)
- **Policy on Upstream Tracking**: Tracking a floating `master` branch in production is strictly prohibited due to active SQLAlchemy 2.0 refactoring and pending schema migrations. All extensions build upon this pinned baseline.

### Baseline Compatibility & Upgrade Risk Matrix

| Component Layer | Baseline Version | Upgrade Risk | Risk Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Python Backend Core** | Python 3.11 / Flask 2.3+ / SQLAlchemy 2.0 transitional | High | Pinned lockfiles; strict type hinting (`mypy`); test coverage. |
| **Database Metadata Schema** | PostgreSQL 17 / Alembic `4b2a8c9d3e1f` -> `b1c2d3e4f5a6` | High | Automated DB migration testing; pre-migration custom-format pg_dump backups. |
| **Frontend Framework** | React 18 / TypeScript 5+ / Webpack 5 | Medium | Isolated plugin workspace packages; zero direct antd imports. |
| **Chart Plugin SDK** | `@superset-ui/core` | Low | Conform to standard `Preset` / `ChartPlugin` interfaces and `transformProps` contracts. |

---

## 2. Cumulative Integration Branching Strategy

To maintain strict release integrity and avoid drift:
1. **Cumulative Integration Branch**: `project/preset-like-base` is the single source of truth for integrated, approved phases.
2. **Phase Branch Lifecycle**:
   - Each phase branch (`feature/phase-<number>-<name>`) is cut exclusively from `project/preset-like-base` after the prior phase is approved and merged.
   - Phase branches are NEVER cut directly from `master` or dangling feature branches.
3. **Approved Phase Tagging**:
   - Upon explicit user approval ("APPROVE PHASE <number>"), the feature branch is merged into `project/preset-like-base` and tagged with an immutable tag: `preset-like-phase<number>-approved`.

```mermaid
gitGraph
   commit id: "baseline (ac3c158c41)"
   branch "project/preset-like-base"
   commit id: "tag: preset-like-phase0-approved"
   branch "feature/phase-0.5-baseline-repair"
   commit id: "Phase 0.5: Baseline Stabilization"
   checkout "project/preset-like-base"
   merge "feature/phase-0.5-baseline-repair" tag: "preset-like-phase0.5-approved"
   branch "feature/phase-1-table-v2"
   commit id: "Phase 1: Table V2 Evaluation"
   checkout "project/preset-like-base"
   merge "feature/phase-1-table-v2" tag: "preset-like-phase1-approved"
```

---

## 3. Capability Matrix & Repository Evidence

| Feature / Capability | Already Available in Base | Feature Flag / Route | Proposed Path | Backend Required | Core Modification Required | Risk |
| :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| **Table V1 (Standard)** | Yes | None (Default) | Built-in baseline | No | No | Low |
| **Table V2 (AG Grid)** | Partial (In Dev) | `AG_GRID_TABLE_ENABLED` | Phase 1: Evaluate existing plugin before custom development | No | No | Low |
| **Advanced Interactive Table** | No | Optional / Custom | Phase 3–4: Standalone `@superset-ui/plugin-chart-enterprise-table` | No (Uses `/api/v1/chart/data` & KV store) | No | Medium |
| **Interactive Pivot Table** | Partial (Built-in V2) | `VizType.PivotTable` | Phase 5: Evaluate existing Pivot Table V2, harden DB-side rollups | No (Uses `/api/v1/chart/data`) | No | High |
| **Safe Template Chart (KPI/Card)** | Partial (Built-in Handlebars) | `VizType.Handlebars` | Phase 6: Audit & harden existing Handlebars chart with strict sanitization | No | No | High (XSS / Injection) |
| **AI Chart Assistant** | No | New Service Route | Phase 7: Structured JSON specification generator with human approval gate | Yes (Assistant API) | No | High (Prompt injection / Auth) |
| **Superset FastMCP Server** | Partial (Built-in) | `superset.mcp_service` | Phase 8: Audit, scope, and harden existing 41+ MCP tools | Yes (FastMCP container) | No | Medium |

---

## 4. Phase Breakdown & Gated Milestones

### Phase 0: Environment and Gap Audit
- **Status**: APPROVED (Approved by User on 2026-09-01)
- **Objective**: Audit deployment environment, software dependencies, OpenAPI endpoints, database models, and security baseline without altering application source code.
- **Deliverables**: Environment report, package mismatch root cause, security baseline matrix, ADR-001 (Proposed), and roadmap.

### Phase 0.5: Reproducible Baseline Repair (Hard Blocker)
- **Status**: APPROVED (Approved by User on 2026-09-01)
- **Objective**: Resolve the SQLAlchemy 1.4/2.0 dependency mismatch in the container build and apply pending Alembic schema migration `b1c2d3e4f5a6` (`add_subjects_tables`).
- **Gating Requirement**: `docker compose up` must start cleanly with `superset`, `superset-worker`, and `superset-worker-beat` reaching a verified `Up` state, real HTTP health check `GET http://localhost:8088/health` returning 200 via network curl, and zero editable package resolution crashes.
- **Scope Restriction**: No visualization plugins or application feature code may be written in Phase 0.5.

### Phase 1: Enable and Evaluate Existing Table V2
- **Status**: APPROVED (Evaluated in Phase 1)
- **Objective**: Safely activate `AG_GRID_TABLE_ENABLED` in `docker/pythonpath_dev/superset_config.py`, create a representative test dataset, and evaluate sorting, filtering, formatting, and export against Preset capabilities.
- **Deliverables**: Gap report comparing existing Table V2 against requirements; test dataset; rollback verification.

### Phase 2: Hello World Visualization Plugin
- **Status**: APPROVED (Bootstrapped in Phase 2)
- **Objective**: Bootstrap `@superset-ui/plugin-chart-enterprise-table` with TypeScript strict mode, React component lifecycle, unit tests, and gallery registration.
- **Deliverables**: Standalone plugin package, clean build pipeline, verified gallery registration.

### Phase 3: Interactive Table MVP
- **Status**: APPROVED (Completed in Phase 3)
- **Objective**: Implement core Interactive Table with multi-column sorting, column resizing/reordering, text/numeric filtering, and verified RLS enforcement.
- **Deliverables**: MVP plugin, automated RTL and Playwright tests, RLS positive/negative tests.

### Phase 4: Advanced Interactive Table
- **Status**: APPROVED (Approved by User on 2026-09-01)
- **Objective**: Extend table with column pinning, per-user saved layouts, cell bars, conditional formatting, virtualized rendering, and Excel export.
- **Deliverables**: Advanced table features, layout isolation tests, 10k+ row performance benchmark.

### Phase 5: Interactive Pivot Table
- **Status**: APPROVED (Approved by User on 2026-09-02; confirmed empty backend diff)
- **Objective**: Evaluate and extend pivot capabilities with drag-and-drop dimensions, DB-side rollup aggregation, and subtotal/grand total calculations.
- **Deliverables**: Database-side aggregation validation, hierarchy expand/collapse tests, Excel export.

### Phase 6: Safe Template Chart
- **Status**: APPROVED (Approved by User on 2026-09-02; confirmed empty backend diff)
- **Objective**: Audit and harden Handlebars-like template cards with strict HTML/CSS allowlisting, DOMPurify/nh3 sanitization, and CSP enforcement.
- **Deliverables**: Sandboxed template component, triple-mustache live-browser XSS defense verification, role permission matrix, audit logging verification.

### Phase 7: AI Chart Assistant
- **Status**: APPROVED (Approved by User on 2026-09-02; confirmed empty core backend diff)
- **Objective**: Implement natural language chart authoring via schema-validated JSON specifications (not raw SQL), query preview (`save_chart=False`), and mandatory human confirmation (`save_chart=True`).
- **Deliverables**: Assistant service, multi-role RLS query isolation tests, prompt injection and adversarial defense test suite, audit logging.

### Phase 8: Superset MCP Server
- **Status**: APPROVED (Approved by User on 2026-09-02; AST hardening and live red-teaming verified)
- **Objective**: Harden the existing FastMCP service with sqlglot AST-based SQL allowlisting, live prompt-injection red-teaming, user-scoped JWT authentication, strict JSON Schema tool validation across 70 tools, and rate limiting.
- **Deliverables**: Hardened `sanitize_sql_expression` AST allowlist, prompt-injection red-teaming test suite, 70-tool inventory validation, tool permission matrix.

### Phase 9: Tableau-Parity Table Calculations & Highlight Table
- **Status**: APPROVED (Approved by User on 2026-09-02)
- **Objective**: Deliver client-side Tableau-parity quick table calculations (Percent of Total, Standard/Dense Rank, Running Total, Difference From, Percent Difference From, Moving Average, Percentile Rank) with strict dataset RLS scoping; and Highlight Table continuous color gradients (Sequential and Diverging color scales, per-column and per-table scopes), WCAG 2.1 gamma-corrected relative luminance text contrast maximization, and SpreadsheetML `ss:Interior` Excel export formatting.
- **Deliverables**: `@superset-ui/plugin-chart-enterprise-table` Table Calculations & Color Scales engine, 51 passing Jest unit tests, Playwright browser test, live RLS isolation verification on Dataset 28, full WCAG 2.1 gamma-corrected luminance engine.

### Phase 10: Dashboard Filter Sets / Saved Filter Presets (Tableau-Parity: Saved Views / Bookmarks equivalent)
- **Status**: APPROVED (Approved by User on 2026-09-02)
- **Objective**: Deliver Tableau-parity saved views / bookmarks allowing dashboard viewers and editors to save, manage, and restore named combinations of native filter values without any core database schema migrations.
- **Architecture**:
  - Leverages existing Superset `key_value` table infrastructure (`resource="dashboard_filter_preset"`), requiring **0 new Alembic migrations**.
  - Strict Personal vs Shared RBAC model: Personal views visible only to creator; Shared views creatable/editable only by dashboard editors.
  - Zero RLS bypass: presets store only filter input values (`dataMask`); live chart queries are executed against the loading user's active session and bound to their individual dataset RLS rules.
  - Automatic Filter Drift Engine: SHA256 checksums over native filter configurations detect additions, deletions, or column modifications, providing a graceful fallback with interactive warning and compatible filter application.
  - Complete REST API (`/api/v1/dashboard/<pk>/filter_preset`) and intuitive UI controls in the FilterBar header (`FilterPresetsDropdown`, `SavePresetModal`, `DriftWarningModal`).
- **Deliverables**: ADR-005, backend `filter_presets` module and REST API, 9 passing pytest unit tests, frontend React components in `@superset-ui/core` ecosystem, 13 passing Jest unit tests, verified live Docker integration, 0 `: any` occurrences.

---

## 5. Development Cycle Conclusion

With the implementation and verification of **Phase 10**, Tableau-parity saved views and filter presets are fully realized as an isolated extension adhering strictly to Superset architectural boundaries, zero core database modifications, and robust dataset RLS protection.

