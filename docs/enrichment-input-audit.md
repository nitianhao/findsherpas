# Enrichment Input Audit

Generated: 2026-04-10

---

## Spreadsheet Files Found

| # | File | Location |
|---|------|----------|
| 1 | `EU_Ecommerce_Prospects_SiteSearch.xlsx` | project root |
| 2 | `US_Ecommerce_Prospects_SiteSearch.xlsx` | project root |

No `.csv`, `.xlsm`, or `.xls` files found (excluding `node_modules`).

---

## Per-File Schema Summary

### 1. EU_Ecommerce_Prospects_SiteSearch.xlsx

**Sheets:** `EU Ecommerce Prospects`, `Legend & Notes`, `Summary by Country`

#### Sheet: EU Ecommerce Prospects (PRIMARY) -- 377 data rows, 13 columns

| Column | Type | Fill Rate |
|--------|------|-----------|
| `#` | Row number | 100% |
| `Company Name` | Text | 100% |
| `Website URL` | URL | 100% |
| `Country` | Text | 100% |
| `Category` | Text | 100% |
| `Est. Revenue (EUR)` | Currency | varies |
| `LinkedIn Company Page` | URL | varies |
| `CEO / MD Name` | Text | **5%** (19/377) |
| `CEO LinkedIn Profile` | URL | **<1%** (3/377) |
| `Head of Product (Name)` | Text | **0%** (0/377) |
| `Head of Ecommerce (Name)` | Text | **0%** (0/377) |
| `Head of Growth / CMO (Name)` | Text | **0%** (0/377) |
| `Notes (Search Relevance)` | Text | varies |

#### Sheet: Legend & Notes -- 34 rows, 2 columns
- Headers: `COLOR LEGEND`, (blank)
- Reference sheet, not prospect data.

#### Sheet: Summary by Country -- 14 rows, 3 columns
- Headers: `Country`, `Companies`, `Color Code`
- Aggregate summary, not prospect data.

---

### 2. US_Ecommerce_Prospects_SiteSearch.xlsx

**Sheets:** `US Ecommerce Prospects`, `Summary by Category`, `How to Use`

#### Sheet: US Ecommerce Prospects (PRIMARY) -- 500 data rows, 12 columns

| Column | Type | Fill Rate |
|--------|------|-----------|
| `#` | Row number | 100% |
| `Company Name` | Text | 100% |
| `Website URL` | URL | 100% |
| `Category` | Text | 100% |
| `Est. Revenue (USD)` | Currency | varies |
| `LinkedIn Company Page` | URL | varies |
| `CEO / Founder Name` | Text | **32%** (160/500) |
| `CEO LinkedIn Profile` | URL | **<1%** (1/500) |
| `Head of Product (Name)` | Text | **0%** (0/500) |
| `Head of Ecommerce (Name)` | Text | **0%** (0/500) |
| `Head of Growth / CMO (Name)` | Text | **0%** (0/500) |
| `Notes (Search Relevance)` | Text | varies |

#### Sheet: Summary by Category -- 43 rows, 3 columns
- Headers: `Category`, `Companies`, `Color`
- Aggregate summary, not prospect data.

#### Sheet: How to Use -- 33 rows, 1 column
- Instructional content, not prospect data.

---

## Structural Inconsistencies

| Issue | EU File | US File |
|-------|---------|---------|
| CEO column naming | `CEO / MD Name` | `CEO / Founder Name` |
| Country column | Present | **Missing** |
| Revenue currency | EUR | USD |
| Column count | 13 | 12 (no `Country`) |

---

## Enrichment Column Audit

| Target Column | EU File | US File |
|---------------|---------|---------|
| CEO / MD Name | EXISTS (5% filled) | EXISTS as `CEO / Founder Name` (32% filled) |
| CEO LinkedIn Profile | EXISTS (<1% filled) | EXISTS (<1% filled) |
| Head of Product (Name) | EXISTS (0% filled) | EXISTS (0% filled) |
| Head of Ecommerce (Name) | EXISTS (0% filled) | EXISTS (0% filled) |
| Head of Growth / CMO (Name) | EXISTS (0% filled) | EXISTS (0% filled) |
| **CEO Email** | **MISSING** | **MISSING** |
| **Head of Product Email** | **MISSING** | **MISSING** |
| **Head of Ecommerce Email** | **MISSING** | **MISSING** |
| **Head of Growth / CMO Email** | **MISSING** | **MISSING** |

---

## Recommendations

### Primary Enrichment Targets
Both primary sheets should be enriched:
1. **`US_Ecommerce_Prospects_SiteSearch.xlsx` > `US Ecommerce Prospects`** -- 500 rows, larger dataset, higher priority
2. **`EU_Ecommerce_Prospects_SiteSearch.xlsx` > `EU Ecommerce Prospects`** -- 377 rows

### Columns to Add (both files)
These 4 email columns are missing from both files and should be added:
- `CEO Email`
- `Head of Product Email`
- `Head of Ecommerce Email`
- `Head of Growth / CMO Email`

### Pre-Enrichment Harmonization Needed
- **Normalize CEO column name**: `CEO / Founder Name` (US) vs `CEO / MD Name` (EU) -- pick one canonical name or map during pipeline.
- **Country column**: US file lacks a `Country` column. Add it (can default to `US`) or handle in pipeline.
- **Revenue currency**: Different currencies (`EUR` vs `USD`). Not blocking for enrichment but relevant for downstream analysis.

### Data Quality Notes
- People columns are almost entirely empty -- this is the enrichment gap the pipeline needs to fill.
- US file has partial CEO names (32%), EU file has very few (5%). These can serve as validation data for the enrichment pipeline.
