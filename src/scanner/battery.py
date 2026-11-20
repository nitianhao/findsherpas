"""Catalog-grounded paired battery; hypotheses are never catalog facts.

F001–F007, F018/19/21/22/25/26/28, F041/42/43/57 from
 docs/search-failure-modes.md. F013 supplements approved formatting modes.
"""
import json
import re
from dataclasses import dataclass, field
from .models import ProbeType as P
from .probes import generate_typo, remove_diacritics


@dataclass
class Pair:
    kind: P
    query: str
    control: str
    expected_title: str = ""
    expected_url: str = ""
    constraints: dict = field(default_factory=dict)
    evidence: str = ""
    grounded: bool = True


def build_battery(generator, products):
    pairs = []
    def add(kind, query, control, product=None, **kwargs):
        if query and control and (query != control or kind == P.RANKING_CHECK):
            pairs.append(Pair(kind, query, control,
                product.title if product else "", product.url or "" if product else "", **kwargs))
    categories = [c for c in generator.nav_categories if 3 <= len(c) <= 55]
    for c in categories[:3]:
        add(P.TYPO, generate_typo(c), c)
    for category in [c for c in categories if remove_diacritics(c) != c][:2]:
        add(P.DIACRITICS,remove_diacritics(category),category)
    if categories:
        pairs.append(Pair(P.CATEGORY_TERM,categories[0],categories[0]))
    # Several genuine two/three-word nav phrases; do not merge entire sentences.
    for c in [c for c in categories if 2 <= len(c.split()) <= 3][:3]:
        add(P.MERGED_WORDS, c.replace(' ', ''), c)
    for product in products[:3]:
        title = product.title
        add(P.EXACT_PRODUCT_NAME, title, categories[0] if categories else title, product)
        add(P.RANKING_CHECK, title, categories[0] if categories else title, product)
        add(P.COVERAGE_CHECK, title, categories[0] if categories else title, product)
        if product.brand:
            add(P.BRAND_SEARCH,f'{product.brand} {title}', title,product,evidence=f'Brand on catalog card: {product.brand}')
            misspelled=generate_typo(product.brand)
            if misspelled.casefold()!=product.brand.casefold():
                add(P.TYPO,f'{misspelled} {title}', title,product,evidence=f'Brand on catalog card: {product.brand}')
        for brand in generator.brands:
            if len(brand) >= 4 and brand.casefold() in title.casefold():
                add(P.BRAND_SEARCH, brand + ' ' + re.sub(re.escape(brand), '', title, flags=re.I).strip(), title, product)
                add(P.TYPO, re.sub(re.escape(brand), generate_typo(brand), title, count=1, flags=re.I), title, product)
                break
        # Unit and format transformations are conditional on literal catalog evidence.
        for pattern, replacement in [(r'(?i)\b(\d+)\s*inch\b', r'\1"'),
                (r'(?i)\b(\d+)\s*(?:litre|liter|litres|liters)\b', r'\1 l'),
                (r'(?i)\bgore-tex\b', 'gore tex'), (r'(?i)\busb-c\b','USB C'),
                (r'(?i)\bTV-Möbel\b','Fernsehmöbel'), (r'(?i)\bTV stand\b','television stand')]:
            if re.search(pattern, title):
                add(P.ABBREVIATION if any(term in pattern for term in ('inch','litre','TV')) else P.FORMAT_VARIANT,
                    re.sub(pattern,replacement,title), title, product)
        for token in title.split():
            if re.search(r'\d', token) and re.search(r'[a-zA-Z]', token) and len(token) >= 3 and not re.fullmatch(r'\d+(?:ml|cm|mm|kg|gb|tb|l|oz)', token, re.I):
                add(P.SKU_SEARCH, token.strip('(),'), title, product)
                break
        unit=re.search(r'\b(\d+)(oz|mm|cm|ml|l)\b',title,re.I)
        if unit:
            add(P.FORMAT_VARIANT,title[:unit.start()]+unit[1]+' '+unit[2]+title[unit.end():],title,product)
            if unit[2].casefold()=='oz':
                add(P.ABBREVIATION,title[:unit.start()]+unit[1]+' ounce'+title[unit.end():],title,product)
        if '-' in title:
            add(P.FORMAT_VARIANT, title.replace('-', ' '), title, product)
        if remove_diacritics(title) != title:
            add(P.DIACRITICS, remove_diacritics(title), title, product)
    for product in products[3:15]:
        title = product.title
        code = re.search(r"\b(?=[A-Za-z0-9-]*\d)(?=[A-Za-z0-9-]*[A-Za-z])[A-Za-z0-9-]{3,}\b|\b\d{5,}\b",title)
        if code and not re.fullmatch(r'\d+(?:ml|cm|mm|kg|gb|tb|l|oz)',code.group(),re.I):
            add(P.SKU_SEARCH,code.group(),title,product)
        for original, variant in [('GORE-TEX','gore tex'),('USB-C','USB C')]:
            if original.casefold() in title.casefold():
                add(P.FORMAT_VARIANT,re.sub(re.escape(original),variant,title,flags=re.I),title,product)
    # Reorder literal title attributes into a shopper query. A qualifying SKU
    # exists in the same captured control; never append an invented size/color.
    for product in products[:3]:
        attributes = {}
        for key, pattern in {
            'colour': r"\b(?:black|white|blue|red|green|orange|pink|schwarz|weiß|blau|rot|grün|černá|černé|modrá|modré|čierna|czarny|biały|blå|sort|svart|grön)\b",
            'gender': r"\b(?:women's|men's|womens|mens|damen|herren|dámské|pánské|dámske|pánske|damskie|męskie|børn|barn)\b",
            'material': r"\b(?:cotton|wool|leather|linen|merino|baumwolle|wolle|leder|bavlna|vlna|bawełna)\b",
            'feature': r"\b(?:waterproof|windproof|vandtæt|wasserdicht|nepromokavé)\b",
        }.items():
            match = re.search(pattern, product.title, re.I)
            if match and not re.search(r'non-|faux|imitation|vegan|kunstleder',product.title,re.I):
                attributes[key] = match.group()
        if attributes:
            remaining = product.title
            for value in attributes.values():
                remaining = re.sub(re.escape(value),'',remaining,count=1,flags=re.I)
            query = ' '.join(list(attributes.values())[::-1] + re.findall(r"[\w'®]+",remaining))
            add(P.CONSTRAINT_QUERY,query,product.title,product,constraints=attributes,evidence=product.title)
    # One cheap Haiku call for linguistic choices; all controls must be supplied text.
    context = json.dumps({'categories': categories[:18],
        'products': [p.title for p in products[:6]], 'brands': generator.brands[:10]}, ensure_ascii=False)
    prompt = f'''Generate up to 12 paired ecommerce search tests in {generator.site.primary_language}.
Catalog: {context}
Return a JSON array ONLY. Each object: kind, query, control, evidence, constraints.
kind allowed: synonym, plural_singular, compound_split, abbreviation, format_variant,
natural_language, constraint_query, brand_search, typo.
control MUST be verbatim one category or product title above (never invent controls).
Try several compound splits at real morpheme boundaries, a misspelled brand,
brand + model (from title), natural problem/use-case query, singular/plural in store language,
units/abbreviations only if present, and long-tail combinations of >=3 explicit title attributes.
For constraint_query, evidence MUST equal the full product title and constraints maps
colour/gender/material/size to exact substrings present in that title. Never invent size,
colour or material. Do not use synonyms as evidence. Unknown is inapplicable; omit it.
For brand_search use a real brand + model from a supplied title; control is that title.
Never output a test for a catalog gap. No markdown.'''
    lines = generator._llm_pick_terms(prompt, count=1, max_tokens=2800)
    if lines:
        try:
            raw = lines[0].strip().removeprefix('```json').removeprefix('```').removesuffix('```')
            for item in json.loads(raw):
                kind = P(item['kind'])
                control = item['control']
                if control not in categories + [p.title for p in products] + generator.brands:
                    continue
                product = next((p for p in products if p.title == control), None)
                constraints = item.get('constraints') or {}
                if kind == P.COMPOUND_SPLIT and re.sub(r'\s+', '', item['query']).casefold() != re.sub(r'\s+', '', control).casefold():
                    continue
                if kind == P.BRAND_SEARCH:
                    if not set(re.findall(r'\w+', item['query'].casefold())) <= set(re.findall(r'\w+', control.casefold())):
                        continue
                if kind == P.CONSTRAINT_QUERY:
                    words = set(re.findall(r"\w+", item['query'].casefold()))
                    allowed = set(re.findall(r"\w+", control.casefold())) | {'for','with','a','the','in','für','mit','pro','na','dla','til'}
                    if not words <= allowed or any(str(v).casefold() not in item['query'].casefold() for v in constraints.values()):
                        continue
                if kind == P.CONSTRAINT_QUERY:
                    if not product or not constraints or any(str(v).casefold() not in product.title.casefold() for v in constraints.values()):
                        continue
                add(kind, item['query'], control, product,
                    constraints=constraints, evidence=product.title if product else control,
                    grounded=kind not in (P.SYNONYM, P.NATURAL_LANGUAGE, P.PLURAL_SINGULAR, P.ABBREVIATION) and (kind != P.FORMAT_VARIANT or re.sub(r"\W", "", item["query"]).casefold() == re.sub(r"\W", "", control).casefold()))
        except (ValueError, KeyError, TypeError, AttributeError):
            pass
    # Deterministic grounded price query: qualify a product already seen with a price.
    language = generator.site.primary_language
    under = {'German':'unter', 'Czech':'do', 'Slovak':'do', 'Polish':'poniżej',
             'Danish':'under', 'Swedish':'under'}.get(language, 'under')
    for p in products:
        price = numeric_price(p.price)
        if price is not None and price > 0:
            limit = int(price * 1.2) + 1
            add(P.PRICE_CONSTRAINT, f'{p.title} {under} {limit}', p.title, p,
                constraints={'price_max':str(limit)}, evidence=f'{p.title}: {p.price}')
            break
    seen = set()
    return [p for p in pairs if not ((p.kind,p.query,p.control) in seen or seen.add((p.kind,p.query,p.control)))]


def numeric_price(value):
    if not value:
        return None
    # Refuse ranges/from-prices or ambiguous multiple prices.
    text = str(value).replace('\xa0',' ').replace('\u202f',' ')
    if re.search(r'from|ab |od |från|–', text, re.I):
        return None
    match = re.search(r'\d[\d .,]*', text)
    if not match:
        return None
    number = match.group().strip().replace(' ', '')
    if ',' in number and '.' in number:
        decimal = ',' if number.rfind(',') > number.rfind('.') else '.'
        number = number.replace('.' if decimal == ',' else ',', '').replace(decimal,'.')
    elif ',' in number:
        number = number.replace(',', '.' if len(number.rsplit(',',1)[1]) == 2 else '')
    try:
        return float(number)
    except ValueError:
        return None
