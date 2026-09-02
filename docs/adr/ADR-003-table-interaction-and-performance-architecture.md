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

# ADR 003: Table Interaction, Column Pinning, Layout Persistence, and Virtualization Architecture

## Metadata
- **Status**: Proposed (Phase 4 Submission)
- **Decision Date**: 2026-09-01
- **Approver**: Platform Engineering / Peer Review
- **Baseline Git Commit**: `ac3c158c41` (Upstream Apache Superset `master`)
- **Supersedes**: N/A
- **Related ADRs**:
  - [ADR 001: Preset-Like Capabilities Extension Strategy](file:///home/bi-tool-ryobilao/Documents/superset/docs/adr/ADR-001-preset-like-extensions-strategy.md)
  - [ADR 002: VizType Enum Extension Policy for Visualization Plugins](file:///home/bi-tool-ryobilao/Documents/superset/docs/adr/ADR-002-viztype-enum-extension.md)

---

## Context
Phase 4 of the Enterprise Interactive Table (`@superset-ui/plugin-chart-enterprise-table`) expands the core MVP with advanced interactive capabilities:
1. **Column Reordering**: Choosing between native HTML5 drag-and-drop vs button-based reordering.
2. **Column Pinning**: Pinning columns left and right with high-performance CSS sticky positioning.
3. **Per-User Saved Layouts**: Persisting custom table configurations (order, widths, pinning, visibility, page size) across browser sessions.
4. **Data Visualization Enhancements**: Cell formatting (conditional highlights, positive/negative value coloring, horizontal cell bars).
5. **Secure Hyperlink Rendering**: Safe URL validation to prevent XSS attacks.
6. **Data Export**: Client-side XLSX (Excel) and CSV export.
7. **Performance & Virtualization**: Handling 10,000+ rows smoothly with sub-second rendering and defensible Playwright benchmark validation.

---

## Decision Drivers
- **Zero Third-Party Bloat**: Avoid adding heavy external drag-and-drop or table libraries that degrade bundle size or introduce license risks.
- **Accessibility & UX**: Support both mouse drag-and-drop and accessible button controls.
- **Strict Security**: Prevent DOM XSS vulnerabilities from untrusted URL strings or unescaped HTML.
- **Memory & Lifecycle Safety**: Clean up all mouse listeners and timers on unmount to prevent leaks during mid-interaction unmounting.
- **Defensible Performance**: Support 10,000+ data rows with responsive 60fps scrolling and rapid rendering.

---

## Decision

### 1. Column Reordering: Hybrid HTML5 Drag-and-Drop + Button Controls
We adopt a **dual-mode interaction model**:
- **HTML5 Drag-and-Drop**: Column headers are draggable (`draggable={true}`) with `onDragStart`, `onDragOver`, `onDragEnter`, and `onDrop` events, rendering visual drop indicators for intuitive mouse reordering.
- **Accessible Button Controls**: Accessible left (`◀`) and right (`▶`) buttons remain available for keyboard navigation, screen readers, and precise pointer control.

### 2. Resizing & Gesture Event Cleanup
All window-level event listeners (`mousemove`, `mouseup`) registered during column resizing are tracked in a mutable ref and strictly cleaned up in a `useEffect` return handler to handle mid-drag component unmounting without memory leaks.

### 3. Column Pinning via Multi-Zone CSS Sticky Positioning
Pinned columns use CSS `position: sticky` with dynamically calculated `left` and `right` offset boundaries and elevated `z-index` layers, ensuring hardware-accelerated 60fps scrolling without DOM duplication.

### 4. Per-User Saved Layout Persistence
User table customizations (column order, widths, pinning, hidden columns, page size, sort configuration) are serialized to `localStorage` under a namespaced key (`superset_enterprise_table_layout_${sliceId || 'default'}`). Users can save views, automatically reload their preference, or reset to dashboard defaults with one click.

### 5. Conditional Cell Formatting, Positive/Negative Coloring, & Cell Bars
- **Positive/Negative Coloring**: Automatic green/red color styling for numeric metrics based on value polarity.
- **Cell Bars**: Proportional horizontal bar backgrounds rendered via inline CSS gradients/divs calculated from `(value - min) / (max - min) * 100%`.
- **Conditional Rules**: Threshold-based styling for min, max, target bounds.

### 6. Safe Hyperlink URL Validation
Automatic URL detection requires strict protocol whitelist validation (`http:`, `https:`, `mailto:`). Potentially dangerous protocols (`javascript:`, `data:`, `vbscript:`) are rejected and rendered as safe plain text. All hyperlinks are rendered with `target="_blank"` and `rel="noopener noreferrer"`.

### 7. Client-Side Excel (.xlsx / XML) & CSV Export
Table data is exported directly from the active dataset using UTF-8 BOM CSV and XML-based Excel format, preserving formatting, numeric types, and headers without external API roundtrips.

### 8. Virtualized Rendering & Benchmark
High-density rendering is validated via Playwright browser tests using synthetic 10,000+ row datasets, measuring initial render times, scroll responsiveness, and frame rates.

---

## Consequences
- **Positive**: Provides enterprise-grade interactive grid capabilities matching commercial BI tools without runtime bloat or security vulnerabilities.
- **Positive**: Guarantees zero DOM XSS and strict RLS compatibility.
- **Negative / Trade-offs**: Complex state interactions (pinning + reordering + resizing) require thorough multi-aspect unit and E2E test coverage.
