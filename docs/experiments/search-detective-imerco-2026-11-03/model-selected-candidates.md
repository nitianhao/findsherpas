# Model-selected candidate evidence

Final extraction/matching review of the 35 products selected by autonomous category-first discovery. Nine accepted modes; this is candidate evidence, not proof of search failure. Prices/availability must be refreshed before search tests.

## negation

- Positive: [RAW by Aida RAW Colour Mini Kop  /  4 stk.](https://www.imerco.dk/raw-by-aida-raw-colour-mini-kop-4-stk-5-cl-stentoej?id=100481065) — `100481065`
- Positive: [Royal Copenhagen Sort Riflet Blonde Termokop](https://www.imerco.dk/royal-copenhagen-sort-riflet-blonde-termokop-26-cl-porcelaen-sort-hvid?id=100422904) — `100422904`
- Positive: [Royal Copenhagen Hvid Riflet Termokop](https://www.imerco.dk/royal-copenhagen-hvid-riflet-termokop-29-cl-porcelaen-hvid?id=100309088) — `100309088`
- Positive: [Pillivuyt Plissé Termokrus  /  2 stk.](https://www.imerco.dk/pillivuyt-plisse-termokrus-2-stk-25-cl-porcelaen-hvid?id=100388154) — `100388154`

Supporting facts:

- `0:0` / `100481065`: product_type = cup ; source: “RAW Colour minikopperne fra RAW by Aida er små kopper i gennemfarvet stentøj”
- `0:1` / `100481065`: handle = none ; source: “Underkategori Krus og kopper uden hank”
- `0:9` / `100422904`: product_type = cup ; source: “Sort Riflet Blonde Termokop”
- `0:10` / `100422904`: handle = none ; source: “Underkategori Krus og kopper uden hank”
- `0:18` / `100309088`: product_type = cup ; source: “Hvid Riflet Termokop”
- `0:19` / `100309088`: handle = none ; source: “Underkategori Krus og kopper uden hank”
- `0:31` / `100388154`: product_type = cup ; source: “Pillivuyt Plissé Termokrus”
- `0:32` / `100388154`: handle = none ; source: “Underkategori Krus og kopper uden hank”

Review: All four products (100481065, 100422904, 100309088, 100388154) have 'Underkategori Krus og kopper uden hank' explicitly stated in their source specifications, which directly means 'Mugs and cups without handle'. This is an explicit categorical designation, not an inference from silence. The handle=none attribute is correctly derived from this explicit subcategory label present in each product's source text. All fact quotes are accurately reproduced and correctly interpreted.

## unit_conversion

- Positive: [Eva Trio Legio Nova Kande](https://www.imerco.dk/eva-trio-legio-nova-kande-70-cl-porcelaen-hvid?id=100408286) — `100408286`
- Positive: [Eva Trio Legio Nova Kande m. hank](https://www.imerco.dk/eva-trio-legio-nova-kande-m-hank-1-liter-porcelaen-hvid?id=100449039) — `100449039`
- Positive: [Eva Trio Legio Nova Kande](https://www.imerco.dk/eva-trio-legio-nova-kande-1-6-liter-porcelaen-hvid?id=100396731) — `100396731`
- Positive: [Georg Jensen Bernadotte Kande](https://www.imerco.dk/georg-jensen-bernadotte-kande-1-2-liter-porcelaen-hvid?id=100448547) — `100448547`
- Positive: [CASA Living Kande](https://www.imerco.dk/casa-living-kande-1-8-liter-borosilikatglas-staal-klar?id=100463435) — `100463435`

Supporting facts:

- `2:0` / `100408286`: product_type = jug ; source: “Underkategori Serveringskander”
- `2:2` / `100408286`: capacity = 0,70 L; source: “Kapacitet 0,70 L”
- `2:5` / `100449039`: product_type = jug ; source: “Underkategori Serveringskander”
- `2:7` / `100449039`: capacity = 1 L; source: “Kapacitet 1 L”
- `2:10` / `100396731`: product_type = jug ; source: “Underkategori Serveringskander”
- `2:12` / `100396731`: capacity = 1,6 L; source: “Kapacitet 1,6 L”
- `2:16` / `100448547`: product_type = jug ; source: “Underkategori Serveringskander”
- `2:18` / `100448547`: capacity = 1,2 L; source: “Kapacitet 1,2 L”
- `2:21` / `100463435`: product_type = jug ; source: “Underkategori Serveringskander”
- `2:24` / `100463435`: capacity = 1,8 L; source: “Kapacitet 1,8 L”

Review: All five products have explicit capacity values in L confirmed by direct quotes in the source text: 100408286 'Kapacitet 0,70 L' (700ml), 100449039 'Kapacitet 1 L' (1000ml), 100396731 'Kapacitet 1,6 L' (1600ml), 100448547 'Kapacitet 1,2 L' (1200ml), 100463435 'Kapacitet 1,8 L' (1800ml). All normalized_value conversions to ml are arithmetically correct. All five are categorized as 'Serveringskander' (serving jugs). The unit conversion facts are correctly interpreted and supported by source evidence.

## dimension

- Positive: [Kähler Hammershøi Sommer Vase](https://www.imerco.dk/kahler-hammershoei-sommer-vase-oe-17-x-h-21-cm-porcelaen-wild-flowers?id=100445100) — `100445100`
- Positive: [CASA Living Vase](https://www.imerco.dk/casa-living-vase-oe-15-5-x-h-20-cm-glas-lysegraa?id=100465402) — `100465402`
- Positive: [CASA Living Glasvase](https://www.imerco.dk/casa-living-glasvase-oe-16-5-x-h-22-cm-glas-blaa?id=100437417) — `100437417`
- Positive: [CASA Living Swirl Vase](https://www.imerco.dk/casa-living-swirl-vase-oe-21-5-x-h-23-2-cm-porcelaen-groen?id=100425739) — `100425739`
- Positive: [Lene Bjerre Helene Vase](https://www.imerco.dk/lene-bjerre-helene-vase-oe-8-x-h-9-cm-keramik-lys-rosa?id=100452312) — `100452312`

Supporting facts:

- `3:0` / `100445100`: product_type = vase ; source: “Underkategori Vaser”
- `3:2` / `100445100`: height = 21 cm; source: “Højde 21 cm”
- `3:3` / `100445100`: diameter = 17 cm; source: “Diameter 17 cm”
- `3:5` / `100465402`: product_type = vase ; source: “Underkategori Vaser”
- `3:7` / `100465402`: height = 20 cm; source: “Højde 20 cm”
- `3:8` / `100465402`: diameter = 15,5 cm; source: “Diameter 15,5 cm”
- `3:10` / `100437417`: product_type = vase ; source: “Underkategori Vaser”
- `3:12` / `100437417`: height = 22 cm; source: “Højde 22 cm”
- `3:13` / `100437417`: diameter = 16,5 cm; source: “Diameter 16,5 cm”
- `3:15` / `100425739`: product_type = vase ; source: “Underkategori Vaser”
- `3:17` / `100425739`: height = 23,2 cm; source: “Højde 23,2 cm”
- `3:18` / `100425739`: diameter = 21,5 cm; source: “Diameter 21,5 cm”
- `3:20` / `100452312`: product_type = vase ; source: “Underkategori Vaser”
- `3:22` / `100452312`: height = 9 cm; source: “Højde 9 cm”
- `3:23` / `100452312`: diameter = 8 cm; source: “Diameter 8 cm”

Review: All five products (100445100, 100465402, 100437417, 100425739, 100452312) have explicit height and diameter values directly quoted from their respective source texts, with correct unit conversions (cm to mm). Each fact ID references a specific, verifiable quote: e.g., 3:2 'Højde 21 cm' and 3:3 'Diameter 17 cm' for 100445100; 3:7 'Højde 20 cm' and 3:8 'Diameter 15,5 cm' for 100465402; 3:12 'Højde 22 cm' and 3:13 'Diameter 16,5 cm' for 100437417; 3:17 'Højde 23,2 cm' and 3:18 'Diameter 21,5 cm' for 100425739; 3:22 'Højde 9 cm' and 3:23 'Diameter 8 cm' for 100452312. Both dimension axes are retained and correctly interpreted for each product. Product type facts are also correctly sourced from 'Underkategori Vaser' in each source.

## pack_capacity

- Positive: [Georg Jensen Bernadotte Glas  /  6 stk.](https://www.imerco.dk/georg-jensen-bernadotte-glas-6?id=100404523) — `100404523`
- Positive: [Eva Solo Facet Vandglas  /  4 stk.](https://www.imerco.dk/eva-solo-facet-vandglas-4-stk-43-cl-glas-klar?id=100353708) — `100353708`
- Positive: [Holmegaard Future Vandglas  /  4 stk.](https://www.imerco.dk/holmegaard-future-vandglas-4-stk-37-cl-glas-klar?id=100109877) — `100109877`
- Positive: [Eva Trio Legio Nova Vandglas  /  6 stk.](https://www.imerco.dk/eva-trio-legio-nova-vandglas-6-stk-40-cl-krystalglas-klar?id=100430598) — `100430598`
- Positive: [Luigi Bormioli Aero Vandglas  /  6 stk.](https://www.imerco.dk/luigi-bormioli-aero-vandglas-6-stk-40-cl-glas-klar?id=100325650) — `100325650`

Supporting facts:

- `4:0` / `100404523`: product_type = glass ; source: “Bernadotte glassene er designet med blide riller”
- `4:1` / `100404523`: material = glass ; source: “Materiale Blyfrit krystalglas”
- `4:2` / `100404523`: pack_count = 6 items; source: “Antal 6”
- `4:3` / `100404523`: capacity = 38 cl; source: “Kapacitet 38 cl”
- `4:5` / `100353708`: product_type = glass ; source: “facetterede vandglas fra Eva Solo”
- `4:6` / `100353708`: material = glass ; source: “Materiale Glas”
- `4:7` / `100353708`: pack_count = 4 items; source: “Antal 4”
- `4:8` / `100353708`: capacity = 43 cl; source: “Kapacitet 43 cl”
- `4:10` / `100109877`: product_type = glass ; source: “Future: Et unikt designet drikkeglas”
- `4:11` / `100109877`: material = glass ; source: “Materiale Glas”
- `4:12` / `100109877`: pack_count = 4 items; source: “Antal 4”
- `4:13` / `100109877`: capacity = 37 cl; source: “Kapacitet 37 cl”
- `4:16` / `100430598`: product_type = glass ; source: “Dæk et flot bord med Legio Nova drikkeglassene fra Eva Trio”
- `4:17` / `100430598`: material = glass ; source: “Materiale Blyfrit krystalglas”
- `4:18` / `100430598`: pack_count = 6 items; source: “Antal 6”
- `4:19` / `100430598`: capacity = 40 cl; source: “Kapacitet 40 cl”
- `4:22` / `100325650`: product_type = glass ; source: “Aero er et elegant og utrolig holdbart vandglas fra Luigi Bormioli”
- `4:23` / `100325650`: material = glass ; source: “Materiale Glas”
- `4:24` / `100325650`: pack_count = 6 items; source: “Antal 6”
- `4:25` / `100325650`: capacity = 40 cl; source: “Kapacitet 40 cl”

Review: All five products have explicit pack_count and capacity-per-glass facts verified against source text. 100404523: Antal 6, Kapacitet 38 cl (confirmed). 100353708: Antal 4, Kapacitet 43 cl (confirmed). 100109877: Antal 4, Kapacitet 37 cl (confirmed). 100430598: Antal 6, Kapacitet 40 cl (confirmed). 100325650: Antal 6, Kapacitet 40 cl (confirmed). All normalized unit conversions (cl to ml) are arithmetically correct. All products are drinking glasses. No ambiguity in capacity-per-item as each pack contains identical glasses.

## solid_material

- Positive: [FDB Møbler D102 Sofabord](https://www.imerco.dk/fdb-moebler-d102-sofabord-oe-85-cm-egetrae-natur?id=100455704) — `100455704`
- Positive: [FDB Møbler D102 Sofabord](https://www.imerco.dk/fdb-moebler-d102-sofabord-oe-55-cm-egetrae-natur?id=100455702) — `100455702`
- Contrast: [Hübsch Skak Sofabord](https://www.imerco.dk/hubsch-skak-sofabord-h-40-x-b-82-x-l-82-cm-mdf-egetraesfiner?id=100478281) — `100478281`

Supporting facts:

- `5:0` / `100455704`: product_type = table ; source: “Kategori Borde Underkategori Sofaborde”
- `5:1` / `100455704`: material = solid_oak ; source: “Massivt egetræ”
- `5:6` / `100455702`: product_type = table ; source: “Kategori Borde Underkategori Sofaborde”
- `5:7` / `100455702`: material = solid_oak ; source: “Massivt egetræ”
- `5:12` / `100478281`: product_type = table ; source: “Kategori Borde Underkategori Sofaborde”
- `5:13` / `100478281`: material = oak_veneer ; source: “Materiale Egetræ,  Finér,  MDF”

Review: All referenced facts are correctly supported by the source text. Products 100455704 and 100455702 both explicitly state 'Massivt egetræ' in their descriptions (solid oak), confirming facts 5:1 and 5:7. Product 100478281 lists 'Materiale Egetræ, Finér, MDF' confirming veneer/MDF construction (fact 5:13), not solid oak. All three are categorized as sofaborde (facts 5:0, 5:6, 5:12). The solid-oak positive and oak-veneer contrast are both explicitly evidenced in the source text.

## compatibility

- Positive: [Eva Trio Stainless Steel Honeycomb Stegepandesæt  /  2 stk.](https://www.imerco.dk/eva-trio-stainless-steel-honeycomb-stegepandesaet-2-stk-oe-24-28-cm-genanvendt-rustfrit-staal?id=100468230) — `100468230`
- Positive: [Eva Trio Stainless Steel Stegepande](https://www.imerco.dk/eva-trio-stainless-steel-stegepande-oe-24-cm-genanvendt-rustfrit-staal-aluminium-keramisk-slip-let-belaegning?id=100442546) — `100442546`
- Positive: [Eva Trio Stainless Steel Stegepande](https://www.imerco.dk/eva-trio-stainless-steel-stegepande-oe-28-cm-aluminium-rustfrit-staal?id=100456332) — `100456332`
- Positive: [Eva Trio Multi 5-ply Stegepande](https://www.imerco.dk/eva-trio-multi-5-ply-stegepande-oe-28-cm-genanvendt-rustfrit-staal?id=100468229) — `100468229`
- Positive: [Scanpan Fusion 5 Stegepande](https://www.imerco.dk/scanpan-fusion-5-stegepande-oe-28-cm-staal?id=100414744) — `100414744`

Supporting facts:

- `6:0` / `100468230`: product_type = pan ; source: “Sæt med pander på Ø 24 og 28 cm”
- `6:3` / `100468230`: induction = true ; source: “Varmekilder Alle varmekilder, Induktion, Glaskeramisk, Gas”
- `6:7` / `100442546`: product_type = pan ; source: “Eva Trio Stainless Steel Stegepande”
- `6:10` / `100442546`: induction = true ; source: “Varmekilder Alle varmekilder, Gas, Glaskeramisk, Induktion”
- `6:14` / `100456332`: product_type = pan ; source: “Eva Trio Stainless Steel Stegepande”
- `6:17` / `100456332`: induction = true ; source: “Panden kan bruges på alle typer komfurer – også induktion”
- `6:20` / `100468229`: product_type = pan ; source: “Eva Trio Multi 5-ply Stegepande”
- `6:23` / `100468229`: induction = true ; source: “Varmekilder Alle varmekilder, Induktion, Glaskeramisk, Gas”
- `6:27` / `100414744`: product_type = pan ; source: “Scanpan Fusion 5 Stegepande”
- `6:30` / `100414744`: induction = true ; source: “Varmekilder Alle varmekilder, Induktion”

Review: All five products have explicit induction support confirmed in source text. 100468230: 'Varmekilder Alle varmekilder, Induktion, Glaskeramisk, Gas'; 100442546: 'Varmekilder Alle varmekilder, Gas, Glaskeramisk, Induktion'; 100456332: 'Panden kan bruges på alle typer komfurer – også induktion'; 100468229: 'Varmekilder Alle varmekilder, Induktion, Glaskeramisk, Gas'; 100414744: 'Varmekilder Alle varmekilder, Induktion'. All fact quotes are correctly interpreted and product-specific.

## combined_exclusions

- Positive: [Eva Trio Multi 5-ply Stegepande](https://www.imerco.dk/eva-trio-multi-5-ply-stegepande-oe-28-cm-genanvendt-rustfrit-staal?id=100468229) — `100468229`

Supporting facts:

- `6:20` / `100468229`: product_type = pan ; source: “Eva Trio Multi 5-ply Stegepande”
- `6:21` / `100468229`: material = stainless_steel_aluminium ; source: “Materiale Aluminium,  Rustfrit stål”
- `6:22` / `100468229`: coating = none ; source: “Stegepanden har ingen belægning”
- `6:23` / `100468229`: induction = true ; source: “Varmekilder Alle varmekilder, Induktion, Glaskeramisk, Gas”

Review: 100468229 source confirms stainless steel and aluminium material ('Materiale Aluminium, Rustfrit stål'), no coating ('Stegepanden har ingen belægning'), and induction compatibility ('Varmekilder Alle varmekilder, Induktion, Glaskeramisk, Gas'). The no-coating claim is based on an explicit statement about absence of coating, not merely PFAS-free status. All three facts are correctly interpreted and specific to this product.

## specificity

- Positive: [Eva Trio Legio Nova Kande](https://www.imerco.dk/eva-trio-legio-nova-kande-1-6-liter-porcelaen-hvid?id=100396731) — `100396731`

Supporting facts:

- `2:10` / `100396731`: product_type = jug ; source: “Underkategori Serveringskander”
- `2:11` / `100396731`: material = porcelain ; source: “Materiale Porcelæn”
- `2:12` / `100396731`: capacity = 1,6 L; source: “Kapacitet 1,6 L”

Review: All three facts are correctly supported by the source text for product 100396731: 'Underkategori Serveringskander' confirms jug/serving pitcher type, 'Materiale Porcelæn' confirms porcelain material, and 'Kapacitet 1,6 L' confirms 1600ml capacity. The product is a single variant with explicit material and capacity, suitable for one-attribute-at-a-time specificity testing.

## conditional_price

- Positive: [Eva Trio Stainless Steel Honeycomb Stegepandesæt  /  2 stk.](https://www.imerco.dk/eva-trio-stainless-steel-honeycomb-stegepandesaet-2-stk-oe-24-28-cm-genanvendt-rustfrit-staal?id=100468230) — `100468230`
- Contrast: [Eva Trio Stainless Steel Stegepande](https://www.imerco.dk/eva-trio-stainless-steel-stegepande-oe-28-cm-aluminium-rustfrit-staal?id=100456332) — `100456332`

Supporting facts:

- `6:0` / `100468230`: product_type = pan ; source: “Sæt med pander på Ø 24 og 28 cm”
- `6:5` / `100468230`: price_regular = 1499,95 DKK; source: “1499,95 Ikke medlem”
- `6:6` / `100468230`: price_member = 499,95 DKK; source: “499,95 Medlemspris”
- `6:14` / `100456332`: product_type = pan ; source: “Eva Trio Stainless Steel Stegepande”
- `6:18` / `100456332`: price_public = 299,95 DKK; source: “299,95 SuperPris”
- `6:19` / `100456332`: pack_count = 1 items; source: “Antal 1”

Review: Facts 6:5 and 6:6 are correctly supported: product 100468230 shows '1499,95 Ikke medlem' (regular/non-member price >=500 DKK) and '499,95 Medlemspris' (member price <500 DKK). Fact 6:0 confirms it is a pan set. For the contrast product 100456332, fact 6:18 shows '299,95 SuperPris' which is a publicly available promotional price (SuperPris) with no membership condition stated in the source, making it a public price <500 DKK. Facts 6:14 and 6:19 confirm it is a single pan. All facts are correctly interpreted and the conditional vs. unconditional pricing distinction is valid.

## Unaccepted mode

`either_or`: model proposed the correct glass and porcelain bowls but repeated them in both positive and contrast lists. Deterministic validation rejected the inconsistent representation. No manual override was applied.
