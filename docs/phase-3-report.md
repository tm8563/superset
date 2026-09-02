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

# Phase 3 Report: Interactive Table MVP (`@superset-ui/plugin-chart-enterprise-table`)

## 1. Current State
- **Branch**: `feature/phase-1-table-v2-evaluation` (Phase 3 Interactive Table MVP).
- **Target Plugin Package**: `@superset-ui/plugin-chart-enterprise-table` (Version `0.1.0`).
- **Plugin Registration Key**: `VizType.EnterpriseTable` (`enterprise_table`).
- **Architectural Policy**: Formally documented in [`ADR-002`](file:///home/bi-tool-ryobilao/Documents/superset/docs/adr/ADR-002-viztype-enum-extension.md).
- **Component Capabilities**:
  - Multi-column sorting (single click & Shift+click multi-sort with priority badges).
  - Column resizing (draggable resize handles with width boundaries).
  - Column reordering (interactive move left/right controls).
  - Per-column text filters (`contains`, `equals`, `startsWith`) and numeric filters (`greaterThan`, `lessThan`, `equals`, `between`).
  - Global search box with instant substring filtering.
  - Client-side pagination with page size selector, jump controls, and filter count badges.
  - Reset filters action button.
- **Test Coverage**: 100% test pass rate across 3 test suites and 15 tests. Zero `any` types. Clean TypeScript compilation (exit code 0).

---

## 2. Mandatory Prerequisite: Multi-Role RLS Verification

As mandated prior to implementing RLS-dependent features, a full multi-role cross-role RLS test suite was executed against the live Superset metadata and query engine.

| Test Step | Security Context | Role / Subject | Executed Operation | Expected Result | Verified Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Baseline** | Admin | Admin (Subject 1) | `POST /api/v1/chart/data` | All 4 regions returned (12,500 rows) | `['APAC', 'EMEA', 'LATAM', 'North America']` (12,500 rows) |
| **2. Rule Creation** | Admin | `Regional_Analyst_Role` (Subject 7) | `POST /api/v1/rowlevelsecurity/` | Create Regular RLS rule on dataset 28 | `HTTP 201 Created` (RLS ID: 2) |
| **3. Non-Admin Query** | Non-Admin (`regional_user`) | `Regional_Analyst_Role` (Subject 7) | `POST /api/v1/chart/data` | Strictly isolated to North America (3,125 rows, 0 leak) | `['North America']` (3,125 rows, 0 leaked) |
| **4. Cross-Role Query** | Admin | Admin (Subject 1) | `POST /api/v1/chart/data` | Unaffected; sees all 4 regions | `['APAC', 'EMEA', 'LATAM', 'North America']` (12,500 rows) |
| **5. Cleanup** | Admin | Admin (Subject 1) | `DELETE /api/v1/rowlevelsecurity/2` | Delete RLS rule | `HTTP 200 OK` |
| **6. Post-Cleanup** | Non-Admin (`regional_user`) | `Regional_Analyst_Role` (Subject 7) | `POST /api/v1/chart/data` | Unrestricted dataset restored | `['APAC', 'EMEA', 'LATAM', 'North America']` (12,500 rows) |

---

## 3. Version Compatibility

| Component / Dependency | Baseline Specification | Phase 3 Implementation Status | Validation Result |
| :--- | :--- | :--- | :--- |
| **React** | `^18.3.0` | React 18 functional component with hooks | Fully interactive state management |
| **TypeScript** | Strict mode (`noImplicitAny: true`) | Strict interfaces; 0 `: any` occurrences | Exit code 0 |
| **@superset-ui/core** | Core chart plugin lifecycle | `ChartPlugin`, `ChartMetadata`, `buildQueryContext`, `rawFormData` | Clean registration & data flow |
| **MainPreset** | Visualization Preset Registry | Registered under `VizType.EnterpriseTable` | Verified in preset registry |

---

## 4. Feature Implementation Details

### 1. Multi-Column Sorting
- **Interaction**:
  - Regular click: toggles column sort (asc -> desc -> none).
  - Shift+click: appends column to multi-sort hierarchy.
- **Indicators**: Renders `▲` / `▼` with sort priority indicators (`1`, `2`, `3`...) when multi-sorting.
- **Comparator**: Handles typed numbers, localized strings, and null/undefined values properly.

### 2. Column Resizing
- **Interaction**: Draggable resize handle at the right edge of each header cell.
- **Constraints**: Enforces minimum width of 60px and maximum width of 800px.
- **Layout**: Utilizes `table-layout: fixed` and pixel-width cell clipping with ellipsis.

### 3. Column Reordering
- **Interaction**: Left (`◀`) and right (`▶`) header action buttons to swap column positions.
- **State**: Dynamically managed in local component state.

### 4. Column Filtering (Text & Numeric)
- **Text Columns**: In-header popover supporting `contains`, `equals`, and `startsWith`.
- **Numeric Columns**: In-header popover supporting `greaterThan` (`>`), `lessThan` (`<`), `equals` (`=`), and `between` (min/max).
- **Indicators**: Active filter dot (`●`) indicates applied column filters; "Reset Filters" button restores default view.

### 5. Pagination & Controls
- **Page Size**: Configurable page sizes (10, 20, 50, 100, 200).
- **Navigation**: First (`⏮`), Previous (`◀`), Next (`▶`), Last (`⏭`) with current page indicator.
- **Summary**: Displays dynamic entry counts (e.g. `Showing 1 to 20 of 100 entries (filtered from 12,500 total entries)`).

---

## 5. Security & Threat Model Compliance

1. **XSS Prevention**: Zero usage of `dangerouslySetInnerHTML`. All cell values and header labels render strictly as escaped JSX text children.
2. **RLS & Authorization**: All queries execute through Superset's standard `/api/v1/chart/data` endpoint with user JWT context, strictly bound by backend Row-Level Security rules.
3. **Bounded Client-Side Processing**: Client-side filtering and sorting operate strictly on the backend-authorized dataset bounded by `row_limit`.

---

## 6. Files Changed & Created

### [NEW] [docs/adr/ADR-002-viztype-enum-extension.md](file:///home/bi-tool-ryobilao/Documents/superset/docs/adr/ADR-002-viztype-enum-extension.md)
- Formal architectural decision record authorizing 1-line VizType enum extension for first-party plugins.

### [NEW] [docs/evidence/phase-3-mvp-evidence.txt](file:///home/bi-tool-ryobilao/Documents/superset/docs/evidence/phase-3-mvp-evidence.txt)
- Raw command execution logs for multi-role RLS test, Jest test suite, TypeScript check, and REST API queries.

### [NEW] [docs/phase-3-report.md](file:///home/bi-tool-ryobilao/Documents/superset/docs/phase-3-report.md)
- Complete Phase 3 technical report.

### [MODIFY] [src/types.ts](file:///home/bi-tool-ryobilao/Documents/superset/superset-frontend/plugins/plugin-chart-enterprise-table/src/types.ts)
- Added types for sorting, resizing, reordering, filtering, pagination, and snake_case form data.

### [MODIFY] [src/transformProps.ts](file:///home/bi-tool-ryobilao/Documents/superset/superset-frontend/plugins/plugin-chart-enterprise-table/src/transformProps.ts)
- Cleaned up camelCase fallback casts; uses `rawFormData` for direct snake_case properties.

### [MODIFY] [src/controlPanel.tsx](file:///home/bi-tool-ryobilao/Documents/superset/superset-frontend/plugins/plugin-chart-enterprise-table/src/controlPanel.tsx)
- Added controls for interactive sorting, resizing, reordering, column filtering, and page size.

### [MODIFY] [src/EnterpriseTableChart.tsx](file:///home/bi-tool-ryobilao/Documents/superset/superset-frontend/plugins/plugin-chart-enterprise-table/src/EnterpriseTableChart.tsx)
- Full interactive table implementation with multi-column sort, resizing, reordering, filters, and pagination.

### [MODIFY] [test/EnterpriseTableChart.test.tsx](file:///home/bi-tool-ryobilao/Documents/superset/superset-frontend/plugins/plugin-chart-enterprise-table/test/EnterpriseTableChart.test.tsx)
- Comprehensive Jest tests for all interactive features.

### [MODIFY] [test/transformProps.test.ts](file:///home/bi-tool-ryobilao/Documents/superset/superset-frontend/plugins/plugin-chart-enterprise-table/test/transformProps.test.ts)
- Verified transform props with snake_case form data and inferred data types.

---

## 7. Automated Test Results

```bash
$ npm --prefix superset-frontend run test -- plugins/plugin-chart-enterprise-table/test/

PASS plugins/plugin-chart-enterprise-table/test/transformProps.test.ts
  ✓ transforms chart props into component props correctly with snake_case formData

PASS plugins/plugin-chart-enterprise-table/test/EnterpriseTableChart.test.tsx
  ✓ renders empty state when data array is empty
  ✓ renders loading state when isLoading is true
  ✓ renders error state when errorMessage is provided
  ✓ renders table headers and data rows correctly with pagination
  ✓ supports single column sorting and multi-column sorting
  ✓ supports column reordering with left/right buttons
  ✓ supports column resizing drag handle interaction
  ✓ filters rows with per-column text filter
  ✓ filters rows with per-column numeric filter
  ✓ filters rows when global search term is entered
  ✓ supports pagination next, prev, and page size selection
  ✓ resets all filters, search, and sorts when reset button is clicked

PASS plugins/plugin-chart-enterprise-table/test/buildQuery.test.ts
  ✓ builds correct query context with dimensions and metrics
  ✓ applies default row limit when unspecified

Test Suites: 3 passed, 3 total
Tests:       15 passed, 15 total
Snapshots:   0 total
Time:        1.691 s
```
