"""Deterministic contract retrieval and input provenance, separate from execution."""
from collections import Counter
import re

from rank_bm25 import BM25Plus

from .input_context import absence, facts, normalized
from .values import Unknown
from .ui import UIModel


STOP = set("the a an of to with from for on in by and their this that my our please request endpoint api using controller service java string".split())
def tokens(text):
    text = re.sub(r'\blog\s+in\b', 'login', text, flags=re.I)
    text = re.sub(r"([a-zа-я])([A-ZА-Я])", r"\1 \2", text)
    words = re.findall(r"[^\W_]+", text.lower())
    return [word[:-1] if len(word) > 3 and word.endswith('s') and not word.endswith(('ss', 'us', 'is')) else word
            for word in words if word not in STOP]


OPERATIONS = [set('get find query lookup search read view open show list refresh inspect fetch check browse look ask calculate compute estimate получить показать'.split()),
              set('create add insert register save book reserve buy purchase создать добавить'.split()),
              set('delete remove erase удалить'.split()),
              set('update modify change edit amend alter revise replace rename изменить'.split()),
              set('login signin authenticate'.split()), set('pay charge settle'.split())]


def intent(text):
    words = tokens(re.sub(r'\blog\s+in\b', 'login', text, flags=re.I))
    return next((i for i, group in enumerate(OPERATIONS) if words and words[0] in group), None)


def reference(value, history):
    if isinstance(value, dict) and set(value) == {'$concat'} and isinstance(value['$concat'],list):
        parts=[reference(part,history) for part in value['$concat']]
        if all(isinstance(part,str) for part in parts):
            return ''.join(parts)
        from .values import Symbol, Text
        if all(isinstance(part,(str,Text)) or isinstance(part,Symbol) and part.typ.split('.')[-1] in {'str','String','UUID'} for part in parts):
            return Text(tuple(item for part in parts for item in (part.parts if isinstance(part,Text) else (part,))))
        return Unknown('History string composition contains a nonstring or unknown value')
    if isinstance(value, dict) and set(value) == {"$ref"}:
        path = str(value["$ref"]).split(".")
        current = history
        for part in path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, (list, tuple)) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                return Unknown("history reference is unavailable", origin=value["$ref"])
        return current
    if isinstance(value, dict):
        return {k: reference(v, history) for k, v in value.items()}
    if isinstance(value, list):
        return [reference(v, history) for v in value]
    return value


class Grounder:
    def __init__(self, project):
        self.p = project
        self.ui = UIModel(project, tokens)
        self.documents, self.extra, self.operations = [], [], []
        for endpoint in project.endpoints:
            method = project.methods[endpoint.method]
            owner = project.types.get(method.owner)
            fields = []
            for param in method.params:
                fields.extend([param.name, param.typ, param.alias])
                resolved = project.resolve_type(param.typ, method.module, method.span.file)
                fields.extend(project.type_fields(resolved))
            self.documents.append(tokens(" ".join([method.name, owner.name if owner else "", endpoint.path, method.doc, self.ui.text(method.key), *fields])) or ['__empty_contract__'])
            source = project.sources.get(method.span.file, b'').decode('utf-8', errors='replace').splitlines()
            raw = project.raw_methods[method.key]
            end = raw.end_point.row + 1 if method.language == 'java' else raw.end_lineno
            self.extra.append(tokens('\n'.join(source[max(0, method.span.line - 1):end])) or ['__empty_source__'])
            ui_operations={intent(self.ui.sites[i]['action_label']) for i in self.ui.by_method.get(method.key, [])} - {None}
            self.operations.append(next(iter(ui_operations)) if len(ui_operations)==1 else intent(method.name))
        # delta=0 retains saturated TF and positive IDF without adding a score
        # to documents that contain none of the query terms.
        self.index = BM25Plus(self.documents, delta=0) if self.documents else None
        self.source_index = BM25Plus(self.extra, delta=0) if self.extra else None
        self.features = [(Counter(primary), Counter(source), operation) for primary, source, operation in zip(self.documents, self.extra, self.operations)]

    def candidates(self, action):
        query = tokens(action)
        if not self.index:
            return []
        focus = tokens(re.split(r'\b(?:for|with|without|from|filtered|on|onto)\b', action, 1, flags=re.I)[0])
        wanted = intent(action)
        scores = self.index.get_scores(query)
        secondary = self.source_index.get_scores(query)
        ranked = []
        for index, document in enumerate(self.documents):
            score = float(scores[index] + .12 * secondary[index])
            score += sum(self.index.idf.get(word, 0) for word in focus if word in document)
            actual = self.operations[index]
            if wanted is not None and actual is not None:
                score *= 1.8 if wanted == actual else .5
            if score > 0:
                ranked.append((score, index))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        if not ranked:
            return []
        # Keep close alternatives as hypotheses; score is not a calibrated probability.
        def signature(index):
            primary, source, operation = self.features[index]
            return operation, tuple((word, primary[word], source[word]) for word in sorted(set(query)))
        equivalent = signature(ranked[0][1])
        return [(i, s) for s, i in ranked if s >= ranked[0][0] - max(0.15, ranked[0][0] * 0.08) or signature(i) == equivalent]

    @staticmethod
    def extract(action, name, typ):
        words = re.findall(r'[^\W_]+', re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name))
        label = r'[ _-]*'.join(map(re.escape, words))
        pattern = r"\b" + label + r"\s*(?:=|:|is\b)?\s*(?:'([^']*)'|\"([^\"]*)\"|([-+]?\d+(?:\.\d+)?)\b|(true|false)\b)"
        match = re.search(pattern, action, re.I)
        if not match:
            if typ.split('.')[-1] in {'String', 'str', 'UUID'}:
                text = re.search(r'\b' + label + r'\s*(?:=|:|is\b)\s*([\w@.+-]+)', action, re.I)
                if text:
                    return text[1]
            return Unknown("no source-grounded scenario literal", typ, name)
        if match[1] is not None or match[2] is not None:
            return match[1] if match[1] is not None else match[2]
        if match[4]:
            return match[4] if typ.split('.')[-1] in {'String', 'str'} else match[4].lower() == "true"
        if re.match(r'[./*]|,\d|[-–]\s*\d|\s+\d', action[match.end():]):
            return Unknown('Numeric fragment has an unsupported continuation', typ, name)
        unit = re.match(r"\s*(kg|grams?|kilograms?|g|lb|lbs|pounds?|km|cm|mm|ms|seconds?|minutes?|hours?)\b", action[match.end():], re.I)
        if unit:
            return Unknown("numeric literal carries units without a source-derived conversion", typ, name)
        if typ.split('.')[-1] in {'String', 'str'}:
            return match[3]
        return float(match[3]) if "." in match[3] else int(match[3])

    def bind(self, engine, scenario, step, history):
        if isinstance(step.get("request"), dict):
            request = reference(step["request"], history)
            return request, {"kind": "explicit-request", "input": step["request"]}
        action = step.get("action", "")
        direct = re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\s+((?:https?://[^\s]+)?/[^\s]*)", action, re.I)
        if direct:
            return {"method": direct[1].upper(), "url": direct[2]}, {"kind": "literal-http", "literal": direct[0]}
        candidates = self.candidates(action)
        if not candidates:
            engine.note("ungrounded-action", "No source contract matches the scenario action", action=action)
            return None, {"kind": "unresolved", "action": action}
        if len(candidates) > 1:
            engine.note("grounding-hypotheses", "Contract retrieval is ambiguous", action=action,
                        candidates=[{"handler": self.p.methods[self.p.endpoints[i].method].skeleton_id, "score": score} for i, score in candidates])
            choice = engine.choose(tuple(range(len(candidates))), "scenario endpoint hypothesis")
        else:
            choice = 0
        index, score = candidates[choice]
        endpoint = self.p.endpoints[index]
        method = self.p.methods[endpoint.method]
        engine.note('lexical-grounding', 'Execution is conditional on a lexical source-contract hypothesis', method.span, handler=method.skeleton_id, score=score)
        request = {"method": endpoint.verb if endpoint.verb != "*" else "GET", "path": endpoint.path,
                   "module": endpoint.module, "body": {}, "query": {}, "path_params": {}, "headers": {}, "form": {}}
        supplied = {**engine.context.get("inputs", {}), **scenario.get("inputs", {}), **step.get("inputs", {})}
        context_facts, raw_context, limited = facts(self.p, engine.context)
        if limited:
            engine.note('context-span-budget', 'Only the first 192 context spans were retained', method.span)
        provenance = []

        def value_for(name, alias, typ):
            if alias in supplied or name in supplied:
                key = alias if alias in supplied else name
                return reference(supplied[key], history), {'source': 'provided-input', 'reference': key}
            value = self.extract(action, alias, typ)
            if isinstance(value, Unknown) and alias != name and value.reason == 'no source-grounded scenario literal':
                value = self.extract(action, name, typ)
            if not isinstance(value, Unknown):
                return value, {'source': 'scenario-literal', 'quote': action}
            # Units must not be discarded in favour of a context default.
            if value.reason != 'no source-grounded scenario literal':
                return value, {'source': 'scenario-literal', 'quote': action}
            found = context_facts.get(normalized(alias), context_facts.get(normalized(name)))
            if found:
                # An explicitly new value cannot inherit an old context credential.
                if normalized(name) in {'username', 'password'} and re.search(r'\bnew\b', action, re.I):
                    return Unknown('New credential has no supplied literal', typ, name), {'source': 'action', 'quote': action}
                return found['value'], {k: v for k, v in found.items() if k != 'value'}
            absent = absence(alias, raw_context)
            if absent and typ.split('.')[-1] in {'String', 'str', 'boolean', 'Boolean', 'bool'}:
                return (False if typ.split('.')[-1] in {'boolean', 'Boolean', 'bool'} else ''), {'source': 'context-absence', 'references': absent}
            return value, {'source': 'unresolved'}

        for param in method.params:
            if param.dependency:
                continue
            alias = param.alias or param.name
            location = param.location or ("path" if "{" + alias + "}" in endpoint.path else "query")
            resolved = self.p.resolve_type(param.typ, method.module, method.span.file)
            if param.typ.split('.')[-1] in {'HttpHeaders', 'BindingResult', 'Principal'}:
                continue
            if location == "body" or (endpoint.framework == "fastapi" and resolved and location != 'form'):
                if not resolved:
                    value, evidence = value_for(param.name, alias, param.typ)
                    request['body'] = value
                    provenance.append({'field': alias, **evidence, 'value': value})
                    continue
                for field, (typ, default) in self.p.type_fields(resolved).items():
                    value, evidence = value_for(field, field, typ)
                    if not isinstance(value, Unknown) or default is None or evidence['source'] != 'unresolved':
                        request["body"][field] = value
                    provenance.append({"field": field, **evidence, "value": value, "entity": resolved})
            else:
                value, evidence = value_for(param.name, alias, param.typ)
                target = "path_params" if location == "path" else "headers" if location == 'header' else 'form' if location == 'form' else "query"
                if not isinstance(value, Unknown) or param.default is None or evidence['source'] != 'unresolved':
                    request[target][alias] = value
                provenance.append({"field": alias, **evidence, "value": value})
        request, ui = self.ui.bind(engine, method.key, action, request, provenance, reference(step.get('ui_inputs', {}), history))
        return request, {"kind": "lexical-hypothesis", "handler": method.skeleton_id, "score": score, "provenance": provenance, "ui": ui}

    def apply_response(self, engine, binding, response):
        return self.ui.apply_response(engine, binding.get('ui'), response)
