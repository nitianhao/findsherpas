"""Conservative product-level scoring for the paired battery."""
import re
from .models import ProbeScore as S, ProbeType as P, ScoredProbe
from .battery import numeric_price


def normalized(text):
    return re.sub(r'[^\w]', '', (text or '').casefold())


def matches(result, title, url):
    return bool((title and normalized(result.title) == normalized(title)) or
                (url and result.url and result.url.split('?')[0].rstrip('/') == url.split('?')[0].rstrip('/')))


def attribute_check(attribute, value, title):
    """Missing text stays unknown; only explicit contradictions can fail."""
    term=re.escape(value.casefold())
    text=title.casefold()
    present=bool(re.search(r'(?<!\w)'+term+r'(?!\w)',text))
    if attribute=='material':
        if re.search(r'\b(?:faux|imitation|vegan|synthetic)\s*[- ]?'+term+r'\b',text):
            return False
        if value.casefold() in ('leather','leder') and re.search(r'\bkunstleder\b',text):
            return False
    if attribute=='gender' and not present:
        pairs=[("men's","women's"),('mens','womens'),('herren','damen'),('pánské','dámské'),
               ('pánske','dámske'),('męskie','damskie')]
        for first,second in pairs:
            opposite=second if value.casefold()==first else first if value.casefold()==second else None
            if opposite and re.search(r'(?<!\w)'+re.escape(opposite)+r'(?!\w)',text) and 'unisex' not in text:
                return False
    return True if present else None


def score_evidence(p):
    def verdict(score, reason, severity='none', confidence='medium'):
        if score == S.FAIL:
            confidence = 'high' if p.grounded and p.repeated and p.control_screenshot_path and p.screenshot_path and p.control_screenshot_path != p.screenshot_path else 'medium'
        return ScoredProbe(probe=p, score=score, score_reason=reason,
                           severity=severity, confidence=confidence)
    known = bool(p.expected_title or p.expected_url)
    expected_in_control = any(matches(r,p.expected_title,p.expected_url) for r in p.control_results)
    # Broad positive counts alone do not prove a particular constrained product exists.
    if known and not expected_in_control:
        return verdict(S.PARTIAL, 'Reference product not verified in control sample')
    if p.result_count == 0:
        if not p.grounded:
            return verdict(S.PARTIAL, "Zero results; semantic equivalence needs manual catalog verification", confidence="low")
        if p.probe_type in (P.CONSTRAINT_QUERY,P.PRICE_CONSTRAINT) and not p.constraints:
            return verdict(S.PARTIAL, 'No independently verified qualifying product')
        return verdict(S.FAIL, 'Confirmed zero versus positive paired control', 'high')
    if p.probe_type == P.RANKING_CHECK:
        ranks = [r.rank for r in p.results if matches(r,p.expected_title,p.expected_url)]
        if ranks and min(ranks) <= 3:
            return verdict(S.PASS, f'Exact catalog product at rank {min(ranks)}')
        if ranks:
            return verdict(S.FAIL, f'Exact catalog product buried at rank {min(ranks)}', 'medium')
        return verdict(S.PARTIAL, 'Exact product absent from extracted sample; ranking not proven')
    if p.constraints:
        checks = []
        for r in p.results[:3]:
            for attr, value in p.constraints.items():
                if attr == 'price_max':
                    price = numeric_price(r.price)
                    checks.append(None if price is None else price <= float(value))
                else:
                    # Missing text is unknown, never a contradiction. Explicit opposing
                    # attributes require PDP verification and stay review candidates.
                    checks.append(attribute_check(attr,value,r.title))
        if checks and all(c is True for c in checks):
            return verdict(S.PASS, 'All requested attributes verified in top-three result evidence')
        if any(c is False for c in checks):
            return verdict(S.FAIL, 'Top-three result contradicts a verified attribute or price requirement', 'medium')
        return verdict(S.PARTIAL, 'Returned product attributes unknown; counts do not prove compliance')
    if known and any(matches(r,p.expected_title,p.expected_url) for r in p.results):
        return verdict(S.PASS, 'Verified catalog product retrieved')
    overlap = {normalized(r.title) for r in p.results} & {normalized(r.title) for r in p.control_results}
    if overlap:
        return verdict(S.PASS, f'{len(overlap)} products shared with positive control')
    return verdict(S.PARTIAL, 'Nonzero results without verified product overlap; manual relevance review required')
