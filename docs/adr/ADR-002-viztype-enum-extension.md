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

# ADR 002: VizType Enum Extension Policy for Visualization Plugins

## Metadata
- **Status**: Accepted (Transitioned from Proposed on Phase 3 Approval)
- **Status History**:
  - `Proposed`: 2026-09-01 (Phase 3 Submission)
  - `Accepted`: 2026-09-01 (Phase 3 Formal Approval)
- **Approver**: Platform Engineering & Security Review
- **Baseline Git Commit**: `ac3c158c41` (Upstream Apache Superset `master`)
- **Supersedes**: N/A
- **Related ADR**: [ADR 001: Preset-Like Capabilities Extension Strategy](file:///home/bi-tool-ryobilao/Documents/superset/docs/adr/ADR-001-preset-like-extensions-strategy.md)

---

## Context
In Apache Superset's frontend architecture, visualization plugin identifiers are defined in the canonical TypeScript enum `VizType` within `@superset-ui/core` (`packages/superset-ui-core/src/chart/types/VizType.ts`).

When introducing standalone visualization plugins (such as `@superset-ui/plugin-chart-enterprise-table`), plugin registration requires a visualization key string. Two implementation approaches exist:
1. **Raw String Literal Registration**: Using raw string literals (e.g. `'enterprise_table' as any` or `string` casts) in `MainPreset.ts` without modifying `VizType.ts`.
2. **Canonical VizType Enum Extension**: Extending the `VizType` enum in `VizType.ts` with a single entry (e.g. `EnterpriseTable = 'enterprise_table'`).

## Decision Drivers
- **Strict Type Safety**: Ensuring zero `any` or loose string casting across monorepo packages.
- **Monorepo Maintainability**: Providing IntelliSense, automated refactoring, and static compile-time checking across Explore, Dashboard, Chart, and Preset modules.
- **Minimal Patch Footprint**: Preserving git mergeability with upstream Apache Superset master branches.

---

## Decision

We formally authorize and standardize the pattern of extending `VizType.ts` with a single enum member for first-party visualization plugins maintained in the monorepo workspace.

Specifically:
```typescript
export enum VizType {
  // ... existing upstream chart types
  EnterpriseTable = 'enterprise_table',
}
```

### Precedent Justification:
1. **Zero Runtime Impact**: An enum extension adds a single key-value pair to the compiled JavaScript object with zero runtime overhead or side effects.
2. **Compile-Time Verification**: Guarantees that chart builders, control panels, metadata registries, and unit test suites use the exact identifier without risk of typos or runtime registration mismatches.
3. **Clean Upstream Merging**: Adding a single appended line to `VizType.ts` represents a minimal 1-line patch that merges cleanly against upstream Apache Superset master updates.
4. **Consistency with MainPreset Registration**: Parallels the standard 2-line registration in `MainPreset.ts` (`import ...` and `new Plugin().configure(...)`).

---

## Consequences

### Positive
- Enforces strict TypeScript compliance (zero implicit/explicit `any`).
- Enables centralized visibility and discovery of all registered plugin types across the codebase.
- Avoids fragile string-casting workarounds across frontend packages.

### Negative / Trade-offs
- Introduces a 1-line modification to `@superset-ui/core/src/chart/types/VizType.ts` that is tracked alongside plugin workspace packages.

---

## Guidelines for Future Plugins
When adding new first-party visualization plugins to the repository:
1. Add a single PascalCase enum member to `VizType.ts` with the snake_case plugin key.
2. Reference this ADR (ADR-002) as the established architectural precedent.
3. Avoid modifying any other core types or interfaces in `@superset-ui/core`.
