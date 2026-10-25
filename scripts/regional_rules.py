"""The two bounded native Loon conditions used by regional service lists."""
from __future__ import annotations
import re

INNER = r'((?:DOMAIN|DOMAIN-SUFFIX|IP-CIDR|IP-CIDR6|IP-ASN),[^()\s]+)'
CN = re.compile(r'AND,\(\(' + INNER + r'\),\(GEOIP,CN\)\)\Z')
OVERSEAS = re.compile(r'AND,\(\(' + INNER + r'\),\(NOT,\(\(GEOIP,CN\)\)\)\)\Z')


def condition(rule: str):
    """Return (underlying matcher, is CN); reject other logical expressions."""
    for expression, is_cn in ((CN, True), (OVERSEAS, False)):
        hit = expression.fullmatch(rule)
        if hit:
            return hit[1], is_cn
    if rule.startswith(('AND,', 'OR,', 'NOT,')):
        raise ValueError('unsupported regional expression: ' + rule[:100])
    return None


def wrap(rule: str, is_cn: bool) -> str:
    if not re.fullmatch(INNER, rule):
        raise ValueError('unsupported regional child matcher')
    geo = 'GEOIP,CN' if is_cn else 'NOT,((GEOIP,CN))'
    return 'AND,((' + rule + '),(' + geo + '))'


def permits(rule: str, country: str | None) -> bool:
    parsed = condition(rule)
    return parsed is None or parsed[1] == (country == 'CN')


def source_matcher(rule: str) -> str:
    parsed = condition(rule)
    return parsed[0] if parsed else rule
