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

# ADR 001: Preset-Like Capabilities Extension Strategy

## Metadata
- **Status**: Proposed
- **Decision Date**: 2026-09-01
- **Approver**: Pending User Review
- **Baseline Git Commit**: `ac3c158c41` (Upstream Apache Superset `master`)
- **Baseline Docker Image**: `apachesuperset.docker.scarf.sh/apache/superset:latest-dev` (`sha256:25015af8efd5...`)
- **Supersedes**: N/A (Initial ADR)
- **Superseded By**: N/A

---

## Context
Apache Superset is a modern data exploration and visualization platform. To deliver Preset-like capabilities (such as interactive enterprise data tables, dynamic drag-and-drop pivot tables, secure template KPI cards, AI chart assistants, and MCP servers) within a self-hosted environment, an architectural strategy is required that balances feature velocity, platform upgradeability, security boundaries, and performance.

## Decision Drivers
- **Upgradeability**: Minimizing merge conflicts during upstream Apache Superset version upgrades.
- **Security & Authorization**: Strict preservation of Superset RBAC and Row-Level Security (RLS) policies; elimination of arbitrary JavaScript and SQL injection surfaces.
- **Maintainability & Isolation**: Clear architectural boundaries separating core Superset code from custom extensions.
- **Performance**: Enforcing database-side aggregation, server-side pagination, and virtualized frontend rendering.

---

## Alternatives Considered

1. **Monolithic Core Fork**:
   - *Description*: Directly modifying Apache Superset core frontend and backend components.
   - *Pros*: Direct access to all internal states and components.
   - *Cons*: Severe technical debt, impossible upstream synchronization, high maintenance cost.
   - *Verdict*: Rejected.

2. **External Microservice Proxy**:
   - *Description*: Running separate external web applications and proxying data queries outside Superset.
   - *Pros*: Full technology stack independence.
   - *Cons*: Duplicates authentication, bypasses native dashboard filter state, breaks embedded dashboard context, fragments user experience.
   - *Verdict*: Rejected for visualizations; adopted selectively for FastMCP gateway.

3. **Layered Plugin & Configuration Architecture (Selected)**:
   - *Description*: Leveraging native Superset visualization plugins (`@superset-ui/core`), built-in feature flags, and official REST API endpoints.
   - *Pros*: Clean package isolation, zero core modification, seamless dashboard integration, fully preserves upstream compatibility.
   - *Verdict*: **Proposed**.

---

## Decision

We adopt a layered extension hierarchy in strict order of preference:
1. **Existing Superset Capabilities & Feature Flags**: Evaluate and utilize built-in features (such as `AG_GRID_TABLE_ENABLED`, Handlebars chart, and Pivot Table V2) prior to introducing custom plugins.
2. **Standalone Visualization Plugins**: Implement custom chart types (such as Enterprise Interactive Table) as isolated npm workspace packages (`packages/*` or `plugins/*` in `superset-frontend`) conforming to `@superset-ui/core` contracts.
3. **Official REST API & Semantic Querying**: All supported query execution must use Superset's authorized query path under the originating user context. RBAC and RLS enforcement must be verified with positive and negative end-to-end tests.
4. **FastMCP & Structured AI Assistant**: LLM interactions are decoupled via FastMCP with JSON Schema validation and mandatory human approval gates, strictly avoiding autonomous unrestricted SQL generation.
5. **Minimal Integration Patches**: Registration of new plugins is confined to `MainPreset.ts` and `setupPlugins.ts` with zero invasive modifications to core rendering or data engine pipelines.

---

## Consequences

### Positive
- Isolates custom visualization logic into dedicated plugin packages.
- Guarantees standard authorization and RLS policies are applied across all queries.
- Enables safe rollout and rollback via configuration toggles and feature flags.
- Preserves upstream git sync capabilities with minimal patch surface.

### Negative / Trade-offs
- Requires maintaining custom Docker build layers for plugin bundling.
- Plugin developers must adhere strictly to Superset UI component contracts and typing constraints.

---

## Revisit Triggers
This ADR must be formally re-evaluated if:
1. Upstream Apache Superset introduces breaking architectural changes to `@superset-ui/core` or the plugin lifecycle.
2. Upstream Superset promotes Table V2 (AG Grid) or Pivot Table V2 to stable default status with full feature parity.
3. A security audit identifies an architectural flaw in the FastMCP or plugin sandboxing model.
