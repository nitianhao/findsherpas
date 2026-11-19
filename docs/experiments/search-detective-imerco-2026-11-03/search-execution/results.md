# Imerco search execution

Observed results, not quality verdicts. Counts use the authoritative results header, excluding facet subtotals.

| Mode | Role | Query | Status | Reported hits | Anchor rank in top 10 |
| --- | --- | --- | --- | ---: | ---: |
| negation | baseline | kopper | ok | 2470 | — |
| negation | test | kopper uden hank | ok | 245 | — |
| unit_conversion | baseline | kande 1,6 L | ok | 28 | 1 |
| unit_conversion | test | kande 1600 ml | ok | 5 | — |
| dimension | baseline | vase | ok | 3777 | — |
| dimension | test | vase højde 21 cm | zero_confirmed | 0 | — |
| pack_capacity | baseline | glas sæt 6 stk | zero_confirmed | 0 | — |
| pack_capacity | test | glas sæt 6 stk 38 cl | zero_confirmed | 0 | — |
| solid_material | baseline | sofabord | ok | 169 | 2 |
| solid_material | test | sofabord massivt egetræ | zero_confirmed | 0 | — |
| compatibility | baseline | stegepande | ok | 1219 | — |
| compatibility | test | stegepande induktion | ok | 778 | 8 |
| combined_exclusions | baseline | stegepande rustfrit stål | ok | 424 | — |
| combined_exclusions | test | stegepande rustfrit stål uden belægning | ok | 2 | — |
| specificity | baseline | kande | ok | 1156 | — |
| specificity | test | kande porcelæn | ok | 147 | 7 |
| specificity | test | kande porcelæn 1,6 L | ok | 15 | 1 |
| conditional_price | baseline | stegepande | ok | 1219 | — |
| conditional_price | test | stegepande under 500 kr | zero_confirmed | 0 | — |
