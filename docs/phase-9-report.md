# Phase 9 Engineering Report: Tableau-Parity Table Calculations & Highlight Table

## Overview
Phase 9 delivers two major capabilities for the Enterprise Interactive Table visualization plugin (`@superset-ui/plugin-chart-enterprise-table`), matching the most commonly used table features in Tableau:

1. **Quick Table Calculations Engine**: Client-side, RLS-enforced transformations computed purely on the query result delivered by `/api/v1/chart/data` without re-querying or modifying Superset core.
2. **Highlight Table / Heat Map Continuous Color Gradient**: Dynamic continuous color scales (*Sequential* and *Diverging*), configurable scoping (*Per Column* and *Per Table*), automated WCAG-compliant relative luminance text contrast selection, and SpreadsheetML (`ss:Interior`) background color preservation in native Excel export.

---

## 1. Quick Table Calculations Engine

Seven Tableau-parity calculation operators were implemented in `src/tableCalculations.ts`:
- **Percent of Total**: Supports *Percent of Column Total*, *Percent of Row Total*, and *Percent of Grand Total*. Guaranteed to sum to 100%.
- **Rank**: Supports *Standard Rank* (competition ties, next rank skipped: 1, 2, 2, 4) and *Dense Rank* (ties shared, next rank not skipped: 1, 2, 2, 3) with *Ascending* and *Descending* direction options.
- **Running Total**: Cumulative sum along column order from top to bottom.
- **Difference From**: Supports difference relative to *Previous Row* or *First Row*.
- **Percent Difference From**: Relative percentage delta from *Previous Row* or *First Row*.
- **Moving Average**: Configurable sliding window size (e.g. 3, 7, 30 periods).
- **Percentile**: Standard percentile rank (0–100%) within partition.

### Visual & Security Guarantees
- **Visual Distinction**: Calculated columns display an `fx` badge and italicized header label.
- **Null Safety**: All calculation types gracefully handle `null`, `undefined`, and `0` divisors, rendering safe `'-'` placeholders with zero `NaN` values or runtime errors.
- **Zero Core Modification**: Built entirely inside the plugin.
- **Strict RLS Scoping**: Calculations execute on the authorized dataset only. When a user with RLS restrictions (e.g., `regional_user`) queries dataset 28, percentages compute strictly over visible rows and sum to 100.00%.

---

## 2. Highlight Table / Heat Map Continuous Color Gradient

Continuous heat map coloring was implemented in `src/colorScales.ts`:
- **Color Modes**:
  - `none`: Standard binary positive/negative coloring (preserved as backward-compatible default).
  - `sequential`: Single-hue light-to-dark gradient based on value magnitude.
  - `diverging`: Two-hue gradient centered on a configurable midpoint (e.g., zero for profit/loss).
- **Palette Registry**: Integrates with Superset's sequential/diverging palette registry (`schemeRdYlGn`, `schemeRdBu`, `dark_blue`, `greens`, `purples`, `blue_white_yellow`).
- **Scoping**:
  - `per_column`: Independent min/max calculated for each column.
  - `per_table`: Shared global min/max across all numeric columns.
- **WCAG 2.1 Relative Luminance & Contrast**: Full WCAG 2.1 compliant implementation using gamma-corrected linear sRGB transformation ($C_{\text{linear}} = C \le 0.04045 ? C/12.92 : ((C+0.055)/1.055)^{2.4}$) and luminance equation ($L = 0.2126 R + 0.7152 G + 0.0722 B$), calculating contrast ratios $(L_1+0.05)/(L_2+0.05)$ to pick maximum contrast text between `#ffffff` and `#1f1f1f`.
- **Excel SpreadsheetML Styling**: Generates `<Style ss:ID="...">` with `<Interior ss:Color="#HEX" ss:Pattern="Solid"/><Font ss:Color="#TEXT_HEX"/>`, preserving the on-screen gradient in exported Excel `.xls` / `.xlsx` files.

---

## 3. Test & Verification Summary

| Test Suite / Tool | Target | Result |
| :--- | :--- | :--- |
| **Jest Unit Tests** | `plugins/plugin-chart-enterprise-table/test/` (5 test suites) | **48 / 48 Passed** (1.815s) |
| **TypeScript Strict Check** | `tsc --noEmit` on plugin package | **Exit Code 0** |
| **Type Safety Check** | `grep -rn ": any" src/` | **0 occurrences** |
| **Playwright E2E Browser Test** | `table-calculations-and-heatmap.spec.ts` | **Passed (1.4s)** |
| **Live RLS Security Test** | `scratch/phase_9_live_verification.py` (Dataset 28) | **Passed** |
| **Excel Export Color Verification** | `ss:Interior` XML style tag generation | **Passed** |
