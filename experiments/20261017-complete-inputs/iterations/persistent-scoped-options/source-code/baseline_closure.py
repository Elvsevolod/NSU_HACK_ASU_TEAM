"""Generic skeleton indexes and lexical retrieval."""
import re, math, json, gzip, collections, warnings


def load_json(path):
    with (gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")) as fh:
        return json.load(fh)


def path_segs(p):
    return [s for s in re.split(r"[/]+", p.split("?")[0]) if s]


def match(req, tpl):
    """Сегменты запроса против шаблона Spring: {x} — один сегмент, ** — хвост."""
    if not tpl:
        return not req
    t = tpl[0]
    if t == "**":
        return True
    if not req:
        return False
    if t.startswith("{") or t == "*" or t == req[0]:
        return match(req[1:], tpl[1:])
    return False


def path_priority(template):
    """Spring MVC specificity for the supported segment-pattern subset."""
    variables = sum(part.startswith('{') for part in template)
    wildcards = sum(part == '*' for part in template)
    catchalls = sum(part == '**' or part.startswith('{*') for part in template)
    length = sum(1 if part.startswith('{') else len(part) for part in template) + len(template)
    return (-bool(catchalls), -variables - wildcards - 2 * catchalls, length, variables - wildcards)


_SPRING_MAPPINGS = {"RequestMapping": None, "GetMapping": "GET", "PostMapping": "POST",
                    "PutMapping": "PUT", "PatchMapping": "PATCH", "DeleteMapping": "DELETE"}


class RouteWarning(UserWarning):
    """Маршрут аннотации не удалось разобрать: путь не литерал."""


def _split_args(s):
    """Аргументы аннотации: деление по запятым верхнего уровня вне кавычек и скобок."""
    s = (s or "").strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    parts, buf, depth, q, esc = [], [], 0, "", False
    for ch in s:
        if q:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == q:
                q = ""
        elif ch in "\"'":
            q = ch; buf.append(ch)
        elif ch in "([{":
            depth += 1; buf.append(ch)
        elif ch in ")]}":
            depth -= 1; buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip()); buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


_LIT = r'"(?:[^"\\]|\\.)*"'
_CONCAT = re.compile(r"\s*{0}(?:\s*\+\s*{0})*\s*".format(_LIT))
_HTTP_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"}


def _literal(expr):
    """Строковый литерал или чистая конкатенация литералов -> значение; иначе None."""
    if not _CONCAT.fullmatch(expr):
        return None
    vals = []
    for tok in re.findall(_LIT, expr):
        try:
            vals.append(json.loads(tok))
        except ValueError:
            return None
    return "".join(vals)


def _path_values(expr, a):
    """Пути value/path: литерал/массив литералов; пустой массив — [""], иначе None при неразрешимости."""
    s = expr.strip()
    if s.startswith("{") and s.endswith("}"):
        comps = _split_args(s[1:-1])
        if not comps:
            return [""]
        vals = []
        for c in comps:
            v = _literal(c)
            if v is None:
                warnings.warn("неразрешённый элемент пути в аннотации %s: %s" % (a["name"], c), RouteWarning)
            else:
                vals.append(v)
        return vals or None
    v = _literal(s)
    if v is None:
        warnings.warn("не литеральный путь в аннотации %s: %s" % (a["name"], expr), RouteWarning)
    return [v] if v is not None else None


def _method_verb(expr):
    """RequestMethod.X (возможно полное имя) или стандартная константа -> HTTP-метод; иначе None."""
    s = expr.strip()
    m = re.fullmatch(r"(?:[A-Za-z_]\w*\s*\.\s*)*RequestMethod\s*\.\s*([A-Za-z_]\w*)", s) or re.fullmatch(r"([A-Za-z_]\w*)", s)
    return m.group(1) if m and m.group(1) in _HTTP_METHODS else None


def _method_values(expr, a):
    """Методы method=...: константа/массив; пустой массив — без ограничения, None — неразрешено."""
    s = expr.strip()
    if s.startswith("{") and s.endswith("}"):
        comps = _split_args(s[1:-1])
        if not comps:
            return ["REQUEST"]
        vals = []
        for c in comps:
            v = _method_verb(c)
            if v is None:
                warnings.warn("неразрешённый метод в аннотации %s: %s" % (a["name"], c), RouteWarning)
            else:
                vals.append(v)
        return vals or None
    v = _method_verb(s)
    if v is None:
        warnings.warn("неразрешённый метод в аннотации %s: %s" % (a["name"], expr), RouteWarning)
        return None
    return [v]


def ann_paths(anns):
    """Маршруты Spring: только value/path (литерал или массив); method=RequestMethod.X — по tuple на метод."""
    out = []
    for a in anns or []:
        base = a["name"].rsplit(".", 1)[-1]
        if base not in _SPRING_MAPPINGS:
            continue
        paths, verbs, bad = None, None, False
        for i, part in enumerate(_split_args(a.get("args") or "")):
            m = re.match(r"([A-Za-z_]\w*)\s*=\s*(.*)$", part, re.S)
            name, expr = (m.group(1), m.group(2)) if m else (None, part)
            if name in ("value", "path") or (name is None and i == 0):
                paths = _path_values(expr, a)
                bad = bad or paths is None
            elif name == "method":
                verbs = _method_values(expr, a)
                bad = bad or verbs is None
        if bad:
            continue
        if paths is None:
            paths = [""]
        fixed = _SPRING_MAPPINGS[base]
        if fixed:
            verbs = [fixed]
        elif verbs is None:
            verbs = ["REQUEST"]
        for v in verbs:
            out.append((v, list(paths)))
    return out


def toks(t):
    return [w.lower() for w in re.findall(r"[A-Za-z][a-z0-9]+|[A-Z]+(?![a-z])", re.sub(r"([a-z])([A-Z])", r"\1 \2", t or "")) if len(w) > 2]


class Index:
    """Скелет: обработчики с шаблонами путей, рёбра для обхода, unit'ы модулей."""

    def __init__(self, sk):
        self.sk = sk; N = self.N = sk["nodes"]
        self.handlers = []; seen = set()
        for nid, n in N.items():
            if n["kind"] != "method":
                continue
            mp = ann_paths(n.get("annotations"))
            if not mp:
                continue
            owner_anns = N[n["owner"]].get("annotations") or []
            cls_ann = ann_paths(owner_anns)
            if not cls_ann and any(a["name"].rsplit(".", 1)[-1] in _SPRING_MAPPINGS for a in owner_anns):
                continue
            cls_paths = list(dict.fromkeys(p for _, ps in cls_ann for p in ps)) or [""]
            cls_verbs = {v for v, _ in cls_ann if v and v != "REQUEST"}
            for verb, vals in mp:
                if verb == "REQUEST":
                    verbs = sorted(cls_verbs) or [None]
                elif cls_verbs:
                    verbs = sorted(cls_verbs | {verb})
                else:
                    verbs = [verb]
                for hv in verbs:
                    for v in vals:
                        for cp in cls_paths:
                            segs = path_segs(cp + "/" + v); key = (nid, hv, tuple(segs))
                            if key not in seen:
                                seen.add(key); self.handlers.append((nid, hv, segs))
        self.cs_method = {nid: n["method"] for nid, n in N.items() if n["kind"] == "call_site"}
        self.calls = collections.defaultdict(set); self.over = collections.defaultdict(set)
        self.wiring = collections.defaultdict(lambda: collections.defaultdict(set))
        for e in sk["edges"]:
            if e["type"] == "calls":
                self.calls[self.cs_method[e["source"]]].add(e["target"])
            elif e["type"] == "overrides":
                self.over[e["target"]].add(e["source"])
            elif e["type"] in ("remote_call", "message_delivery", "runtime_dispatch", "data_access"):
                self.wiring[e["type"]][self.cs_method.get(e["source"], e["source"])].add(e["target"])
        self.module = {nid: n["module"] for nid, n in N.items() if n["kind"] == "method"}
        self.units = {n["name"]: set(n.get("deployment_units") or [n["name"]]) for n in N.values() if n["kind"] == "module"}
        self.size = collections.Counter(u for us in self.units.values() for u in us)
        self.stmts = collections.defaultdict(list)
        for e in sk["edges"]:
            if e["type"] == "contains" and e["target"].startswith("stmt:"):
                self.stmts[e["source"]].append(e["target"])

    def unit_of(self, m):
        """Самый узкий unit модуля метода: отдельный сервис при нескольких вариантах сборки."""
        mod = self.module[m]
        return min(self.units.get(mod, {mod}), key=lambda u: (self.size[u], u))

    def cha(self, m):
        out, st = set(), [m]
        while st:
            x = st.pop()
            for o in self.over.get(x, ()):
                if o not in out:
                    out.add(o); st.append(o)
        return out

    def handlers_for(self, method, path, host=None):
        """Обработчики, чей шаблон совпадает с путём запроса (host — сервис, если проект без gateway)."""
        segs = path_segs(path); matches = []
        for nid, verb, tpl in self.handlers:
            if host and host not in self.N[nid]["module"]:
                continue
            if (verb is None or method is None or verb == method or (method == "HEAD" and verb == "GET")) and match(segs, tpl):
                matches.append((nid, verb, tpl))
        return self.preferred_handlers(matches, method)

    def preferred_handlers(self, candidates, method=None):
        """Compare paths within each service and known HTTP method."""
        best, output = {}, collections.defaultdict(set)
        for nid, verb, template in candidates:
            group = (self.N[nid]['module'], verb if method is None else method)
            priority = (*path_priority(template), bool(method and verb == method))
            if group not in best or priority > best[group]:
                best[group], output[group] = priority, {nid}
            elif priority == best[group]:
                output[group].add(nid)
        return set().union(*output.values()) if output else set()

    def handler_docs(self):
        """Текст обработчика для лексического поиска: шаблон пути (x3), имя (x2), модуль."""
        docs = {}
        for nid, verb, tpl in self.handlers:
            docs.setdefault(nid, []).extend(toks(" ".join(tpl)) * 3 + toks(self.N[nid]["name"]) * 2 + toks(self.N[nid]["module"]))
        return docs

    def closure(self, entries):
        """Обход в контексте unit'а: вызовы — только в модули того же unit'а (общие модули могут входить в несколько сервисов);
        remote — переход в unit обработчика. -> (методы, calls, remote, data)."""
        seen, edges, remote, data = set(), set(), set(), set()
        st = [(m, self.unit_of(m)) for m in entries]
        while st:
            m, u = st.pop()
            if (m, u) in seen:
                continue
            seen.add((m, u))
            for t in self.calls.get(m, ()):
                for x in ({t} | self.cha(t) | self.wiring["runtime_dispatch"].get(m, set())):
                    if not self.N[x].get("abstract") and u in self.units.get(self.module.get(x), ()):
                        edges.add((m, x)); st.append((x, u))
            for t in self.wiring["remote_call"].get(m, set()) | self.wiring["message_delivery"].get(m, set()):
                remote.add((m, t)); st.append((t, self.unit_of(t)))
            for t in self.wiring["data_access"].get(m, set()):
                data.add((m, t))
        return {m for m, _ in seen}, edges, remote, data



class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.ids = list(docs); D = [docs[i] for i in self.ids]
        self.tf = [collections.Counter(d) for d in D]; self.len = [len(d) for d in D]
        self.avg = sum(self.len) / max(1, len(D)); self.k1, self.b = k1, b
        df = collections.Counter(t for c in self.tf for t in c)
        self.idf = {t: math.log(1 + (len(D) - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def rank(self, q):
        """-> [(балл, id)] по убыванию, только ненулевые."""
        q = collections.Counter(q); sc = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t, qn in q.items():
                if t in tf:
                    s += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg)) * min(qn, 3)
            if s > 0:
                sc.append((s, self.ids[i]))
        return sorted(sc, reverse=True)
