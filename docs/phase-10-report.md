# Phase 10 Engineering & Security Audit Report: Dashboard Filter Sets / Saved Filter Presets (Tableau-Parity Saved Views)

**Date**: 2026-09-02  
**Phase**: 10 (Dashboard Filter Sets / Saved Filter Presets)  
**Status**: COMPLETE & FULLY VERIFIED (Awaiting User Sign-off)  
**Target Milestone**: Tableau-Parity Saved Views & Filter Presets  
**Architecture Reference**: [ADR-005](file:///home/bi-tool-ryobilao/Documents/superset/docs/adr/ADR-005-dashboard-filter-presets-architecture.md)

---

## 1. Executive Summary

Phase 10 addresses the single most frequently cited usability gap for enterprise analytics teams migrating from Tableau to Apache Superset: **Saved Views / Bookmarks**. When native "Filter Sets" were removed in Superset 4.0 (PR #26369) due to code maintenance and UI fragility in the legacy implementation, users lost the ability to name, persist, and restore combinations of native filter values.

In Phase 10, this capability has been rebuilt from first principles as an isolated, production-grade extension:
1. **Zero Database Migrations Required**: Reuses the native `key_value` table infrastructure (`resource="dashboard_filter_preset"`), eliminating migration risks and metadata fragmentation.
2. **Zero Row-Level Security (RLS) Bypass**: Presets store exclusively client-side filter input values (`dataMask`). When applied, all data-bearing queries are issued under the active user's session and executed against the database under their individual dataset RLS constraints.
3. **Automatic Filter Schema Drift Engine**: Detects when dashboard editors add, remove, or modify native filter columns after a preset is saved, offering an interactive reconciliation modal to apply compatible filters or update the view.
4. **Strict Personal vs. Shared RBAC**: Dashboard viewers can create private Personal views; Shared views visible to all dashboard viewers can only be authored and managed by dashboard editors.
5. **Modern Type-Safe Implementation**: 100% TypeScript with strict compile (`npx tsc --noEmit` = exit 0), 0 `: any` types, 0 `dangerouslySetInnerHTML`, 9 passing backend pytest tests, and 13 passing frontend Jest tests.

---

## 2. Architecture & Design Specification (ADR-005)

### 2.1 Storage & Model Architecture
Filter presets are persisted in Superset's unified `key_value` table using the `JsonKeyValueCodec`:
- **`resource`**: `"dashboard_filter_preset"`
- **`uuid`**: Standard UUIDv4 unique preset identifier.
- **`created_by_fk` / `changed_by_fk`**: Foreign keys to `ab_user` ensuring ownership tracking.
- **`expires_on`**: `None` (permanent storage).
- **`value`**: JSON-serialized payload containing:
  ```json
  {
    "dashboard_id": "13",
    "name": "North America - Q3 Highlights",
    "description": "Filters region to NA and sales > 5k",
    "is_shared": false,
    "filter_config_checksum": "5a2f8b1c4e90d231",
    "filter_summary": {
      "NATIVE_FILTER-region": { "name": "Region", "type": "filter_select", "column": "region" }
    },
    "data_mask": {
      "NATIVE_FILTER-region": {
        "id": "NATIVE_FILTER-region",
        "filterState": { "value": ["North America"] }
      }
    }
  }
  ```

### 2.2 RBAC & Permission Matrix

| Operation | Target View Scope | User Role Requirement | Permission Rule |
| :--- | :--- | :--- | :--- |
| **List Presets** | Personal | Any Dashboard Viewer | Returns only presets where `created_by_fk == user.id` |
| **List Presets** | Shared | Any Dashboard Viewer | Returns presets where `is_shared == True` on accessible dashboard |
| **Create Preset** | Personal | Any Dashboard Viewer | Allowed for any user with dashboard read access |
| **Create Preset** | Shared | Dashboard Editor / Owner | Requires `can_edit_dashboard` or Admin role |
| **Update / Refresh** | Personal | Preset Creator / Admin | Requires `created_by_fk == user.id` or Admin |
| **Update / Refresh** | Shared | Dashboard Editor / Owner | Requires `can_edit_dashboard` or Admin |
| **Delete Preset** | Personal | Preset Creator / Admin | Requires `created_by_fk == user.id` or Admin |
| **Delete Preset** | Shared | Dashboard Editor / Owner | Requires `can_edit_dashboard` or Admin |

---

## 3. Implementation Details

### 3.1 Backend Module (`superset/dashboards/filter_presets/`)
- **`api.py`**: REST API endpoints under `/api/v1/dashboard/<pk>/filter_preset`:
  - `POST /api/v1/dashboard/<pk>/filter_preset` — Create preset (HTTP 201).
  - `GET /api/v1/dashboard/<pk>/filter_preset` — List accessible presets (HTTP 200).
  - `GET /api/v1/dashboard/<pk>/filter_preset/<preset_id>` — Get preset by ID (HTTP 200).
  - `PUT /api/v1/dashboard/<pk>/filter_preset/<preset_id>` — Update preset (HTTP 200).
  - `DELETE /api/v1/dashboard/<pk>/filter_preset/<preset_id>` — Delete preset (HTTP 200).
- **`commands/`**: Command pattern implementation (`CreateFilterPresetCommand`, `GetFilterPresetCommand`, `ListFilterPresetsCommand`, `UpdateFilterPresetCommand`, `DeleteFilterPresetCommand`).
- **`schemas.py`**: Marshmallow schemas (`DashboardFilterPresetPostSchema`, `DashboardFilterPresetPutSchema`, `DashboardFilterPresetResponseSchema`).
- **`initialization/__init__.py`**: Registered `DashboardFilterPresetRestApi` with Flask-AppBuilder.

### 3.2 Frontend Components (`FilterBar/FilterPresets/`)
- **`FilterPresetsDropdown.tsx`**: Header drop-down button displaying saved views badge count, search filtering, Personal vs Shared tabs, 1-click apply, 1-click update/refresh, and deletion with confirmation.
- **`SavePresetModal.tsx`**: Modal for capturing preset name, description, and Personal vs Shared visibility (with editor permission enforcement).
- **`DriftWarningModal.tsx`**: Modal warning when dashboard filters have drifted, identifying removed/modified filters and allowing users to apply compatible filters or update the view.
- **`utils.ts`**: Deterministic checksum algorithm (`computeFilterConfigChecksum`), drift detection engine (`detectFilterDrift`), and dataMask sanitizer (`sanitizePresetDataMask`).
- **`api.ts`**: Clean `SupersetClient` API client methods.
- **`types.ts`**: Full TypeScript definitions (**zero `: any`**).

---

## 4. Verification & Testing Evidence

### 4.1 Backend Pytest Unit Tests
**Command**: `docker exec superset-superset-1 pytest tests/unit_tests/dashboards/filter_presets/test_filter_presets_api.py`
```
============================= test session starts ==============================
platform linux -- Python 3.11.14, pytest-7.4.4, pluggy-1.5.0
collected 9 items

tests/unit_tests/dashboards/filter_presets/test_filter_presets_api.py ......... [100%]

======================== 9 passed, 19 warnings in 0.40s ========================
```

### 4.2 Frontend Jest Unit Tests
**Command**: `npm run test -- FilterPresets.test.tsx FilterBar/Header/`
```
PASS src/dashboard/components/nativeFilters/FilterBar/Header/Header.test.tsx
PASS src/dashboard/components/nativeFilters/FilterBar/FilterPresets/FilterPresets.test.tsx

Test Suites: 2 passed, 2 total
Tests:       13 passed, 13 total
Snapshots:   0 total
Time:        2.467 s
```

### 4.3 TypeScript Compiler Check
**Command**: `npx tsc --noEmit`
- **Exit Code**: `0` (Zero compilation or type errors).

### 4.4 Live Docker REST API Verification
**Execution**: Verified live inside `superset-superset-1` on Dashboard 13:
```
Login status: 200
Testing filter preset API on dashboard 13...
Create preset status: 201 {'result': {'changed_on': '2026-09-02T03:48:19.391090', 'created_by': {'first_name': 'Superset', 'id': 1, 'last_name': 'Admin', 'username': 'admin'}, 'created_on': '2026-09-02T03:48:19.391090', 'dashboard_id': '13', 'data_mask': {'NATIVE_FILTER-1': {'filterState': {'value': ['SampleVal']}, 'id': 'NATIVE_FILTER-1'}}, 'description': 'Live API Verification', 'filter_config_checksum': 'a1b2c3d4e5f6', 'filter_summary': {}, 'id': '4093de0e-d51d-47e8-9b91-dd1b86f7f6fc', 'is_owner': True, 'is_shared': False, 'name': 'Test Live Preset'}}
List presets status: 200 Count: 1
Get preset status: 200 Test Live Preset
Update preset status: 200 Updated Live Preset
Delete preset status: 200 {'message': 'OK'}
```

### 4.5 Security & Code Quality Audits
1. **Any Type Audit**:
   - `grep -rn ": any" superset-frontend/src/dashboard/components/nativeFilters/FilterBar/FilterPresets/` -> **0 matches**.
2. **XSS Sanitization Audit**:
   - Preset names and descriptions rendered strictly as safe JSX text strings without `dangerouslySetInnerHTML`.
3. **Secret Leak Audit**:
   - Scanned all created/modified files for credentials or unredacted tokens -> **0 secrets found**.

---

## 5. Conclusion & Status

Phase 10 is complete, fully tested, and verified in both backend and frontend layers. It achieves full feature parity with Tableau Saved Views / Bookmarks while adhering strictly to Apache Superset architectural principles, zero core database migrations, and complete dataset RLS isolation.
