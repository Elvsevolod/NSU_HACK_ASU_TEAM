"""Bounded literal field defaults, with source rather than payload classes."""
import json,re
from .state import U


def literal_default(node):
    if node is None:return U,None
    kind,raw=node.type,node.text.decode('utf-8')
    if kind=='parenthesized_expression':
        return literal_default(next((child for child in node.named_children if child.type not in ('line_comment','block_comment')),None))
    if kind=='null_literal':return None,None
    if kind=='unary_expression' and raw[:1] in ('+','-'):
        operand=node.child_by_field_name('operand') or node.named_children[-1]
        token=operand.text.decode('utf-8')
        if operand.type=='decimal_integer_literal':
            try:
                value=int(token.rstrip('lL').replace('_',''))*(-1 if raw.startswith('-') else 1)
                bits=64 if token.lower().endswith('l') else 32
                if -(1<<(bits-1))<=value<(1<<(bits-1)):return value,'Long' if bits==64 else 'Integer'
            except ValueError:pass
        elif operand.type=='decimal_floating_point_literal':
            value,boxed=literal_default(operand)
            if value is not U:return (-value if raw.startswith('-') else value),boxed
        return U,None
    if kind in ('true','false'):return kind=='true','Boolean'
    if kind=='string_literal':
        try:return json.loads(raw),'String'
        except ValueError:return U,None
    if kind=='character_literal':
        content=raw[1:-1]
        if len(content)==1:return content,'Character'
        if content=="\\'":return "'",'Character'
        if content=='\\s':return ' ','Character'
        if re.fullmatch(r'\\[0-7]{1,3}',content) and int(content[1:],8)<=255:return chr(int(content[1:],8)),'Character'
        try:
            decoded=json.loads('"'+content+'"')
            if len(decoded.encode('utf-16-le',errors='surrogatepass'))==2:return decoded,'Character'
        except ValueError:pass
    if kind=='decimal_integer_literal':
        try:
            value=int(raw.rstrip('lL').replace('_',''))
            bits=64 if raw.lower().endswith('l') else 32
            if value<1<<(bits-1):return value,'Long' if bits==64 else 'Integer'
        except ValueError:pass
    if kind=='decimal_floating_point_literal' and not raw.lower().endswith('f'):
        try:return float(raw.rstrip('dD').replace('_','')),'Double'
        except ValueError:pass
    return U,None
