"""Explicit mass units, never a default unit for an unqualified weight field."""
from decimal import Decimal
import re
from .state import U

ALIASES={'g':'g','gram':'g','grams':'g','kg':'kg','kilogram':'kg','kilograms':'kg',
         'mg':'mg','milligram':'mg','milligrams':'mg'}
GRAMS={'g':Decimal(1),'kg':Decimal(1000),'mg':Decimal('0.001')}


def unit_name(value):
    return ALIASES.get(value.strip().lower()) if isinstance(value,str) else None


def mass_binding(field,action,hints=()):
    words=re.findall(r'[a-z]+',re.sub(r'([a-z0-9])([A-Z])',r'\1 \2',field).lower())
    if not set(words)&{'mass','weight'}:return None
    matches=list(re.finditer(r'\b(\d+(?:\.\d+)?)\s*('+ '|'.join(sorted(ALIASES,key=len,reverse=True))+r')\b',action,re.I))
    if not matches:return None
    units={ALIASES[word] for word in words if word in ALIASES}
    units.update(unit for unit,_ in hints)
    if len(matches)!=1 or len(units)!=1:return U,action,'unit:unresolved'
    match=matches[0];target=next(iter(units));source=ALIASES[match[2].lower()]
    value=Decimal(match[1])*GRAMS[source]/GRAMS[target]
    references=[ref for unit,ref in hints if unit==target]
    return format(value,'f'),match[0],';'.join(references) or 'declared-field-unit:'+field
