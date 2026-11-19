"""Deterministic grounding; semantic correctness additionally requires review."""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from .contracts import Candidate, Fact, Product


def norm(s: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', s).split()).casefold()


def number(s: str) -> Decimal:
    s = s.strip().replace(' ', '')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    return Decimal(s)


def ground_fact(f: Fact, p: Product) -> str | None:
    if f.product_id != p.id:
        return 'wrong product source'
    if not 3 <= len(f.quote) <= 600 or norm(f.quote) not in norm(p.text):
        return 'quote absent from product source or not a specific fragment'
    if f.attribute == 'coating' and f.value == 'none' and not re.search(
            r'ingen belægning|uden (?:non[ -]?stick[ -]?)?belægning|ubelagt|uncoated|without (?:a )?(?:non[ -]?stick )?coating', norm(f.quote)):
        return 'no-coating claim needs an explicit absence statement in the quote'
    if f.attribute in {'capacity','height','width','diameter','pack_count','price_member','price_regular','price_public'}:
        try:
            value = number(f.value)
        except InvalidOperation:
            return 'invalid numeric value'
        quoted_numbers=[]
        for token in re.findall(r'\d+(?:[.,]\d+)*', f.quote):
            try: quoted_numbers.append(number(token))
            except InvalidOperation: continue
        if not value.is_finite() or value <= 0 or value not in quoted_numbers:
            return 'numeric value not present in quote'
        unit = f.unit.casefold()
        if f.attribute == 'capacity':
            factors = {'l':1000,'liter':1000,'litre':1000,'cl':10,'ml':1}
            aliases = {'l':r'(?:l|liter|litre)', 'liter':r'(?:l|liter|litre)',
                       'litre':r'(?:l|liter|litre)', 'cl':'cl', 'ml':'ml'}
            if unit not in factors or not re.search(r'(?<![a-zæøå])'+aliases[unit]+r'(?![a-zæøå])',norm(f.quote)):
                return 'capacity unit missing or unsupported'
            value *= factors[unit]
            f.normalized_unit = 'ml'
        elif f.attribute in {'height','width','diameter'}:
            if unit not in {'mm','cm','m'} or not re.search(r'(?<!\w)'+unit+r'(?!\w)',norm(f.quote)):
                return 'dimension unit missing or unsupported'
            value *= {'mm':1,'cm':10,'m':1000}[unit]
            f.normalized_unit = 'mm'
        elif f.attribute == 'pack_count':
            if value != int(value):
                return 'pack count must be integral'
            f.normalized_unit = 'items'
        else:
            if f.unit.casefold().rstrip('.') not in {'dkk','kr'}:
                return 'pilot prices require DKK'
            # Currency may be established by the store context; eligibility needs semantic review.
            f.normalized_unit = 'DKK'
        f.normalized_value = format(value.normalize(), 'f')
    return None


def validate_candidate(c: Candidate, products: dict[str, Product], facts: dict[str, Fact]) -> list[str]:
    errors=[]
    ids=c.positive_ids+c.contrast_ids
    if not c.positive_ids or len(ids)!=len(set(ids)) or any(pid not in products for pid in ids):
        return ['missing, duplicate, or unknown product ID']
    if not c.fact_ids or len(c.fact_ids)!=len(set(c.fact_ids)) or any(fid not in facts for fid in c.fact_ids):
        return ['missing, duplicate, or unknown fact ID']
    selected=[facts[fid] for fid in c.fact_ids]
    if any(f.product_id not in ids for f in selected):
        return ['fact belongs to an unreferenced product']
    def values(pid, attr):
        return [f.value for f in selected if f.product_id==pid and f.attribute==attr]
    def has(pid, attr, allowed=None):
        vs=values(pid,attr)
        return bool(vs) and (allowed is None or bool(set(vs)&set(allowed)))
    def numeric(pid, attr):
        return [number(f.normalized_value) for f in selected if f.product_id==pid and f.attribute==attr and f.normalized_value]
    def positive(pid):
        mode=c.mode
        if mode=='negation': return has(pid,'product_type',['cup']) and has(pid,'handle',['none'])
        if mode=='either_or': return has(pid,'product_type',['bowl']) and has(pid,'material',['glass','porcelain'])
        if mode=='unit_conversion': return has(pid,'product_type',['jug']) and bool(numeric(pid,'capacity'))
        if mode=='dimension':
            h=numeric(pid,'height'); other=numeric(pid,'diameter')+numeric(pid,'width')
            return has(pid,'product_type',['vase']) and bool(h and other and any(a!=b for a in h for b in other))
        if mode=='pack_capacity': return has(pid,'product_type',['glass']) and any(v>=2 for v in numeric(pid,'pack_count')) and bool(numeric(pid,'capacity'))
        if mode=='solid_material': return has(pid,'product_type',['table']) and has(pid,'material',['solid_oak'])
        if mode=='compatibility': return has(pid,'product_type',['pan']) and has(pid,'induction',['true'])
        if mode=='combined_exclusions': return has(pid,'product_type',['pan']) and has(pid,'material',['stainless_steel','stainless_steel_aluminium']) and has(pid,'coating',['none'])
        if mode=='specificity': return has(pid,'product_type',['jug']) and has(pid,'material') and bool(numeric(pid,'capacity'))
        if mode=='conditional_price': return has(pid,'product_type',['pan']) and any(v<500 for v in numeric(pid,'price_member')) and any(v>=500 for v in numeric(pid,'price_regular'))
        return False
    if not all(positive(pid) for pid in c.positive_ids):
        errors.append('positive product lacks required mode facts')
    if c.mode=='either_or':
        if not all(any(has(pid,'material',[m]) for pid in c.positive_ids) for m in ['glass','porcelain']): errors.append('both OR branches need product evidence')
    if c.mode=='solid_material':
        if not c.contrast_ids or not all(has(pid,'product_type',['table']) and has(pid,'material',['oak_veneer']) for pid in c.contrast_ids): errors.append('explicit oak veneer contrast required')
    if c.mode=='conditional_price':
        if not c.contrast_ids or not all(has(pid,'product_type',['pan']) and any(v<500 for v in numeric(pid,'price_public')) for pid in c.contrast_ids): errors.append('unconditional under-budget pan contrast required')
    return errors
