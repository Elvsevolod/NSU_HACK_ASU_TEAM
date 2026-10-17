"""Generic skeleton indexes and lexical retrieval."""
import re, math, json, gzip, collections


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


def ann_paths(anns):
    out = []
    for a in anns or []:
        if a["name"].endswith("Mapping"):
            vals = re.findall(r'"([^"]*)"', a.get("args") or "")
            out.append((a["name"].replace("Mapping", "").upper(), vals or [""]))
    return out


def toks(t):
    return [w.lower() for w in re.findall(r"[A-Za-z][a-z0-9]+|[A-Z]+(?![a-z])", re.sub(r"([a-z])([A-Z])", r"\1 \2", t or "")) if len(w) > 2]


class Index:
    """Скелет: обработчики с шаблонами путей, рёбра для обхода, unit'ы модулей."""

    def __init__(self, sk):
        self.sk = sk; N = self.N = sk["nodes"]
        self.handlers = []
        for nid, n in N.items():
            if n["kind"] != "method":
                continue
            mp = ann_paths(n.get("annotations"))
            if not mp:
                continue
            cls_paths = [v for verb, vals in ann_paths(N[n["owner"]].get("annotations")) for v in vals] or [""]
            for verb, vals in mp:
                for v in vals:
                    for cp in cls_paths:
                        self.handlers.append((nid, verb if verb != "REQUEST" else None, path_segs(cp + "/" + v)))
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
        segs = path_segs(path); out = set()
        for nid, verb, tpl in self.handlers:
            if host and host not in self.N[nid]["module"]:
                continue
            if (verb is None or method is None or verb == method) and match(segs, tpl):
                out.add(nid)
        return out

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
