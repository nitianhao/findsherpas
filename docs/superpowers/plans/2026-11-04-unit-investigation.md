# Imerco volume failure investigation record

Completed 2026-11-04. Starting point: accepted 1.6-L/1600-ml failure with independently verified product evidence.

- [x] Generate and run controlled representation/token/branded query variants from the verified volume.
- [x] Repeat key comparisons and check stability.
- [x] Inspect public query-bound search records and capacity representation.
- [x] Isolate numeric typo handling with read-only, request-scoped controls.
- [x] Test local unit-aware candidate expansion/filtering with a second-volume control.
- [x] Add meaningful parser/feed/recall regression tests and preserve results, source boundaries and proposed fix.

Result: mixed unit strings are not unified in these requests, and numeric typo matching supplies wrong-size products. Disabling numeric typos alone gives zero; normalizing quantity and filtering canonical capacity is needed. The local 1600-ml replay keeps 26 capacity-consistent candidates and rejects seven wrong-size candidates. No production configuration changed.

See `docs/experiments/search-detective-imerco-2026-11-03/unit-investigation-results.md` for complete evidence and limitations.
