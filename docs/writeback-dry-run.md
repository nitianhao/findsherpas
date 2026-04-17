# Writeback Dry Run Report

Generated: 2026-04-17

## Summary

| Metric | Count |
|--------|-------|
| Rows processed | 877 |
| Role decisions | 3508 |
| Total actions | 7900 |
| **WRITE_CELL** | **0** |
| SKIP_EXISTING_VALUE | 15 |
| SKIP_NOT_APPROVED | 5 |
| SKIP_BLOCKED | 0 |
| SKIP_EMPTY_VALUE | 7873 |
| SKIP_COLUMN_MISSING | 7 |
| ERROR | 0 |

## By Workbook

| Workbook | Writes | Skips |
|----------|--------|-------|
| US_Ecommerce_Prospects_SiteSearch.xlsx | 0 | 4504 |
| EU_Ecommerce_Prospects_SiteSearch.xlsx | 0 | 3396 |

## By Role

| Role | Writes | Skips |
|------|--------|-------|
| CEO | 0 | 2631 |
| HEAD_OF_PRODUCT | 0 | 1755 |
| HEAD_OF_ECOMMERCE | 0 | 1757 |
| HEAD_OF_GROWTH | 0 | 1757 |

## By Column

| Column | Writes | Skips |
|--------|--------|-------|
| CEO / Founder Name | 0 | 500 |
| CEO LinkedIn Profile | 0 | 877 |
| CEO Email | 0 | 877 |
| Head of Product (Name) | 0 | 877 |
| Head of Product Email | 0 | 877 |
| Head of Ecommerce (Name) | 0 | 877 |
| HEAD_OF_ECOMMERCE_LINKEDIN | 0 | 3 |
| Head of Ecommerce Email | 0 | 877 |
| Head of Growth / CMO (Name) | 0 | 877 |
| Head of Growth / CMO Email | 0 | 877 |
| HEAD_OF_GROWTH_LINKEDIN | 0 | 3 |
| CEO / MD Name | 0 | 377 |
| HEAD_OF_PRODUCT_LINKEDIN | 0 | 1 |

## Write Examples

| Company | Role | Column | Value | Confidence | Evidence |
|---------|------|--------|-------|------------|----------|

## Skip/Block Examples

| Company | Role | Column | Action | Reason |
|---------|------|--------|--------|--------|
| Reformation | CEO | CEO / Founder Name | SKIP_EMPTY_VALUE | No value to write |
| Reformation | CEO | CEO LinkedIn Profile | SKIP_EMPTY_VALUE | No value to write |
| Reformation | CEO | CEO Email | SKIP_EMPTY_VALUE | No value to write |
| Reformation | HEAD_OF_PRODUCT | Head of Product (Name) | SKIP_EMPTY_VALUE | No value to write |
| Reformation | HEAD_OF_PRODUCT | Head of Product Email | SKIP_EMPTY_VALUE | No value to write |
| Reformation | HEAD_OF_ECOMMERCE | Head of Ecommerce (Name) | SKIP_NOT_APPROVED | Status REVIEW not in allowed statuses: Role resolution is UNRESOLVED_WEAK — needs manual review |
| Reformation | HEAD_OF_ECOMMERCE | HEAD_OF_ECOMMERCE_LINKEDIN | SKIP_COLUMN_MISSING | No workbook column for HEAD_OF_ECOMMERCE_LINKEDIN |
| Reformation | HEAD_OF_ECOMMERCE | Head of Ecommerce Email | SKIP_EMPTY_VALUE | No value to write |
| Reformation | HEAD_OF_GROWTH | Head of Growth / CMO (Name) | SKIP_EMPTY_VALUE | No value to write |
| Reformation | HEAD_OF_GROWTH | Head of Growth / CMO Email | SKIP_EMPTY_VALUE | No value to write |
| Tuckernuck | CEO | CEO / Founder Name | SKIP_EXISTING_VALUE | Cell already has value "Jocelyn Gailliot" — overwrite disabled |
| Tuckernuck | CEO | CEO LinkedIn Profile | SKIP_EXISTING_VALUE | Cell already has value "https://www.linkedin.com/in/jocelyn-gailliot-44135b4/" — overwrite disabled |
| Tuckernuck | CEO | CEO Email | SKIP_EMPTY_VALUE | No value to write |
| Tuckernuck | HEAD_OF_PRODUCT | Head of Product (Name) | SKIP_EMPTY_VALUE | No value to write |
| Tuckernuck | HEAD_OF_PRODUCT | Head of Product Email | SKIP_EMPTY_VALUE | No value to write |
| Tuckernuck | HEAD_OF_ECOMMERCE | Head of Ecommerce (Name) | SKIP_EMPTY_VALUE | No value to write |
| Tuckernuck | HEAD_OF_ECOMMERCE | Head of Ecommerce Email | SKIP_EMPTY_VALUE | No value to write |
| Tuckernuck | HEAD_OF_GROWTH | Head of Growth / CMO (Name) | SKIP_EMPTY_VALUE | No value to write |
| Tuckernuck | HEAD_OF_GROWTH | Head of Growth / CMO Email | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | CEO | CEO / Founder Name | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | CEO | CEO LinkedIn Profile | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | CEO | CEO Email | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | HEAD_OF_PRODUCT | Head of Product (Name) | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | HEAD_OF_PRODUCT | Head of Product Email | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | HEAD_OF_ECOMMERCE | Head of Ecommerce (Name) | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | HEAD_OF_ECOMMERCE | Head of Ecommerce Email | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | HEAD_OF_GROWTH | Head of Growth / CMO (Name) | SKIP_EMPTY_VALUE | No value to write |
| Johnny Was | HEAD_OF_GROWTH | Head of Growth / CMO Email | SKIP_EMPTY_VALUE | No value to write |
| Faherty Brand | CEO | CEO / Founder Name | SKIP_NOT_APPROVED | Status REVIEW not in allowed statuses: Person "Faherty Brand" is suspicious (score: 30): company suffix: matches \b(brand|brands|group|holding|holdings|company|enterprises)\b, toxic token: "brand", name overlaps company name "Faherty Brand" — likely company/brand, not person |
| Faherty Brand | CEO | CEO LinkedIn Profile | SKIP_NOT_APPROVED | Status REVIEW not in allowed statuses: Person is suspicious — LinkedIn URL needs review |