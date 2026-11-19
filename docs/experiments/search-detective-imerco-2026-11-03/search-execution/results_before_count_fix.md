# Imerco search execution

All rows are observations, not search-quality verdicts. Only the first ten results were extracted. Anchor absence does not establish failure.

| Mode | Role | Query | Status | Reported hits | Anchor rank in top 10 |
| --- | --- | --- | --- | ---: | ---: |
| negation | baseline | kopper | ok | 1115 | — |
| negation | test | kopper uden hank | ok | 137 | — |
| unit_conversion | baseline | kande 1,6 L | ok | 3 | 1 |
| unit_conversion | test | kande 1600 ml | ok | 2 | — |
| dimension | baseline | vase | ok | 1490 | — |
| dimension | test | vase højde 21 cm | zero_confirmed | 0 | — |
| pack_capacity | baseline | glas sæt 6 stk | zero_confirmed | 0 | — |
| pack_capacity | test | glas sæt 6 stk 38 cl | zero_confirmed | 0 | — |
| solid_material | baseline | sofabord | ok | 23 | 2 |
| solid_material | test | sofabord massivt egetræ | zero_confirmed | 0 | — |
| compatibility | baseline | stegepande | ok | 890 | — |
| compatibility | test | stegepande induktion | ok | 602 | 8 |
| combined_exclusions | baseline | stegepande rustfrit stål | ok | 331 | — |
| combined_exclusions | test | stegepande rustfrit stål uden belægning | ok | 2 | — |
| specificity | baseline | kande | ok | 518 | — |
| specificity | test | kande porcelæn | ok | 47 | 7 |
| specificity | test | kande porcelæn 1,6 L | ok | 1 | 1 |
| conditional_price | baseline | stegepande | ok | 890 | — |
| conditional_price | test | stegepande under 500 kr | zero_confirmed | 0 | — |
