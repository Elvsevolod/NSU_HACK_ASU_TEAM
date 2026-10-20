"""A single explicit final JSON object, separate from NL field heuristics."""
import json
import math
from .java_collections import JsonObject


class LiteralBodyError(ValueError):
    pass


def pairs(values):
    result={}
    for key,value in values:
        if key in result:raise LiteralBodyError('Duplicate JSON object key: '+key)
        result[key]=value
    return JsonObject(values)


def constant(value):
    raise LiteralBodyError('Non-finite JSON literal is not a request value: '+value)


def floating(written):
    value=float(written)
    if not math.isfinite(value):raise LiteralBodyError('JSON number exceeds the finite floating-value contract')
    return value


def parse(action):
    quote=None;escaped=False
    for index,char in enumerate(action):
        if quote:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char==quote:quote=None
            continue
        if char in ('"',"'"):
            # An apostrophe inside a natural-language word is not a quote.
            if char=="'" and index and index+1<len(action) and action[index-1].isalnum() and action[index+1].isalnum():continue
            quote=char;continue
        if char!='{':continue
        prefix=action[:index].rstrip()
        if not prefix.endswith((':','=')):continue
        try:body,end=json.JSONDecoder(object_pairs_hook=pairs,parse_constant=constant,parse_float=floating).raw_decode(action,index)
        except json.JSONDecodeError as error:
            raise LiteralBodyError('Explicit JSON request body is malformed') from error
        if action[end:].strip():raise LiteralBodyError('Explicit JSON body must be a single final object; trailing actions are ambiguous')
        return {'body':body,'quote':action[index:end],'prefix':prefix[:-1].rstrip()}
    return None
