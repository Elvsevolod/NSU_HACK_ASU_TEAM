"""Project facts and skeleton identity mapping; bodies are lowered on demand."""
from collections import defaultdict
from copy import deepcopy
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import builtins

from .ir import Span, pack, unpack

RUNTIME_PACKAGES=('tree-sitter','tree-sitter-java','tree-sitter-javascript','libcst','sqlglot','z3-solver',
                  'rank-bm25','numpy','PyYAML','html5lib','quickjs-ng','six','webencodings',
                  'fastapi','starlette','pydantic','pydantic-core','python-multipart','email-validator',
                  'PyJWT','pwdlib','argon2-cffi','argon2-cffi-bindings','bcrypt','anyio','cffi','pycparser',
                  'typing-extensions','typing-inspection','annotated-doc','annotated-types','opentelemetry-api','dnspython','idna','javaproperties','tzdata')


def read_json(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


class Project:
    MODEL_VERSION = "polygraph-13-models-1"

    def __init__(self, root, skeleton, cache=None, profiles=(), source_globals=None,source_configuration=None):
        self.root = Path(root).resolve()
        self.source_globals=source_globals or {}
        self.source_configuration=deepcopy(source_configuration or {})
        self.skeleton = read_json(skeleton) if not isinstance(skeleton, dict) else skeleton
        self.nodes = self.skeleton["nodes"]
        if not isinstance(self.nodes, dict):
            raise ValueError("Skeleton nodes must be an ID-to-node mapping")
        self.methods, self.types, self.endpoints = {}, {}, []
        self.source_candidates = defaultdict(list)
        for mid, node in self.nodes.items():
            if node.get("kind") == "method":
                self.source_candidates[(node.get("file"), node.get("name"))].append((mid, node))
        self.method_by_id, self.types_by_name, self.types_by_fqn = {}, defaultdict(list), defaultdict(list)
        self.imports, self.globals, self.aliases = {}, {}, {}
        self.import_wildcards = defaultdict(list)
        self.immutable_globals = set()
        self.lexical_modules = {}
        self.raw_methods, self.adapters, self.diagnostics = {}, {}, []
        self.framework_risks = []
        self.modules = {k: v for k, v in self.nodes.items() if v.get("kind") == "module"}
        self.tables = {k: v for k, v in self.nodes.items() if v.get("kind") == "data_resource"}
        self.profiles = set(profiles)
        self.profile_order=tuple(dict.fromkeys(profiles))
        self.framework_versions = {}
        build_sources, spring_candidates = {}, defaultdict(set)
        self.sources = {}
        self.configuration_sources={}
        self.frontend_hashes = {}
        self.lowered, self.cache_hits = 0, 0
        self.cache_path = Path(cache) if cache else None
        self.cache = {}
        if self.cache_path and self.cache_path.exists():
            try:
                self.cache = read_json(self.cache_path)
            except (ValueError, OSError):
                self.warn("cache-invalid", "Ignoring unreadable IR cache")
        ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "target", "build"}
        for path in sorted(self.root.rglob("*")):
            relative = path.relative_to(self.root)
            if not path.is_file() or set(relative.parts) & ignored:
                continue
            if path.suffix in {".java", ".py"}:
                self.sources[relative.as_posix()] = path.read_bytes()
            elif path.suffix in {'.js','.html','.htm','.vue','.ts','.jsx','.tsx'}:
                self.frontend_hashes[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.name == 'pom.xml':
                from .java_contracts import spring_versions, ET
                raw = path.read_bytes()
                build_sources[relative.as_posix()] = raw
                try:
                    spring_candidates[self.module(relative.as_posix())].update(spring_versions(raw))
                except ET.ParseError:
                    self.warn('build-config-parse', 'Maven metadata cannot establish library versions', Span(relative.as_posix()))
            elif path.suffix in {'.properties','.yaml','.yml'}:
                self.configuration_sources[relative.as_posix()]=path.read_bytes()
        for module, versions in spring_candidates.items():
            if module and len(versions) == 1:
                self.framework_versions[module] = {'spring': next(iter(versions))}
            elif len(versions) > 1:
                self.warn('framework-version-conflict', 'Explicit Spring dependency versions disagree; mutability is unknown', detail=module)
        digest = hashlib.sha256(self.MODEL_VERSION.encode())
        for package in RUNTIME_PACKAGES:
            digest.update((package + "=" + importlib.metadata.version(package)).encode())
        digest.update(json.dumps(self.skeleton, sort_keys=True).encode())
        digest.update(json.dumps(self.profile_order).encode())
        digest.update(json.dumps(self.source_configuration,sort_keys=True).encode())
        digest.update(json.dumps(self.source_globals,sort_keys=True).encode())
        digest.update(json.dumps(self.frontend_hashes, sort_keys=True).encode())
        for file, content in self.sources.items():
            digest.update(file.encode() + b"\0" + content)
        for file, content in build_sources.items():
            digest.update(file.encode() + b"\0" + content)
        for file,content in self.configuration_sources.items():
            digest.update(file.encode()+b'\0'+content)
        # A model/code change invalidates lowered IR even when source bytes stay equal.
        for path in sorted(Path(__file__).parent.rglob("*.py")):
            digest.update(path.relative_to(Path(__file__).parent).as_posix().encode() + b'\0' + path.read_bytes())
        self.fingerprint = digest.hexdigest()
        if self.cache.get("fingerprint") != self.fingerprint:
            self.cache = {"fingerprint": self.fingerprint, "methods": {}}
        from .java import JavaAdapter
        from .python import PythonAdapter
        self.adapters = {"java": JavaAdapter(self), "python": PythonAdapter(self)}
        for adapter in self.adapters.values():
            adapter.index()
        from .spring_config import SpringConfiguration
        self.configuration=SpringConfiguration(self,self.configuration_sources,build_sources,self.source_configuration,self.profile_order)
        for adapter in self.adapters.values():
            adapter.link()
        for info in self.types.values():
            if info.language == "java" and self.enabled(info) is not False and any(re.search(r"(?:OncePerRequestFilter|GenericFilterBean|(?:^|\.)Filter|SecurityConfigurerAdapter|ResourceServerConfigurerAdapter)\b", p) for p in info.parents):
                self.framework_risks.append({"module":info.module,"framework":"spring","file":info.span.file,"line":info.span.line,"reason":"unmodeled filter/security lifecycle"})
        for method in self.methods.values():
            if method.annotations.get("middleware"):
                self.framework_risks.append({"module":method.module,"framework":"fastapi","file":method.span.file,"line":method.span.line,"reason":"unmodeled FastAPI middleware lifecycle"})
        for mid, node in self.nodes.items():
            if node.get("kind") == "method" and mid not in self.method_by_id:
                self.warn("unmapped-method", "Skeleton method has no matching source declaration", Span(node.get("file", ""), node.get("line", 0)), mid)

    def warn(self, code, message, span=Span(), detail=""):
        item = {"code": code, "message": message, "file": span.file, "line": span.line, "detail": detail}
        if item not in self.diagnostics:
            self.diagnostics.append(item)

    def module(self, file):
        matches = []
        for key, meta in self.modules.items():
            path = meta.get("path", meta.get("name", "")).strip("/")
            if path and (file == path or file.startswith(path + "/")):
                matches.append((len(path), meta.get("name", key.removeprefix("module:"))))
        if matches:
            return max(matches)[1]
        owners = {n.get("module") for n in self.nodes.values() if n.get("file") == file and n.get("module")}
        if len(owners) == 1:
            return owners.pop()
        if len(self.modules) == 1:
            key, meta = next(iter(self.modules.items()))
            return meta.get("name", key.removeprefix("module:"))
        return ""

    def add_type(self, info):
        self.types[info.key] = info
        self.types_by_name[info.name].append(info.key)
        self.types_by_fqn[info.key.split(':', 1)[-1]].append(info.key)

    def add_method(self, method, raw):
        candidates = []
        for mid, node in self.source_candidates[(method.span.file, method.name)]:
            owner = self.nodes.get(node.get("owner"), {})
            if owner.get("fqn") and method.language == "java" and owner["fqn"].split(".")[-1].split("$")[-1] != method.owner.split(".")[-1].split(":")[-1]:
                continue
            if node.get("line") is not None and not raw[1] <= node["line"] <= raw[2]:
                continue
            params = node.get("params_as_written")
            if params is not None and len(params) != len(method.params):
                continue
            candidates.append(mid)
        if len(candidates) == 1:
            method.skeleton_id = candidates[0]
            self.method_by_id[candidates[0]] = method.key
        elif len(candidates) > 1:
            self.warn("ambiguous-method-id", "Source declaration maps to multiple skeleton IDs", method.span)
        self.methods[method.key] = method
        self.raw_methods[method.key] = raw[0]

    def lower(self, key):
        method = self.methods[key]
        if method.body is None:
            cached = self.cache["methods"].get(key)
            if cached is not None:
                try:
                    method.body = unpack(cached)
                    self.cache_hits += 1
                except (TypeError, ValueError, KeyError):
                    method.body = None
            if method.body is None:
                method.body = self.adapters[method.language].lower(method, self.raw_methods[key])
                self.cache["methods"][key] = pack(method.body)
                self.lowered += 1
        return method.body

    def save_cache(self):
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
            temporary.write_text(json.dumps(self.cache, ensure_ascii=False))
            temporary.replace(self.cache_path)

    def table_id(self, name, schema=""):
        if name in self.tables:
            return name
        matches = [rid for rid, node in self.tables.items() if node.get("name") == name or rid.removeprefix("res:table:") == name]
        if schema:
            exact = [rid for rid in matches if self.tables[rid].get("schema") == schema or rid.removeprefix("res:table:").startswith(schema + ".")]
            if len(exact) == 1:
                return exact[0]
        return matches[0] if len(matches) == 1 else ""

    def resolve_type(self, name, module="", file=""):
        raw = re.sub(r"<.*>|\[.*\]|\?", "", name).strip()
        if raw in self.types:
            return raw
        local_key=self.lexical_modules.get(file,'')+'.'+raw
        if file.endswith('.py') and local_key in self.types:return local_key
        explicit=self.resolve_import(raw,file)
        imported = explicit or raw
        candidates = self.types_by_fqn.get(imported, [])
        if not candidates:
            if explicit or '.' in raw or file.endswith('.py') and isinstance(getattr(builtins,raw,None),type):
                return ''
            candidates = self.types_by_name.get(raw.split(".")[-1], [])
        local = [key for key in candidates if self.types[key].module == module]
        selected = local or candidates
        return selected[0] if len(selected) == 1 else ""

    def resolve_import(self, name, file):
        explicit = self.imports.get(file, {}).get(name)
        if explicit:
            return explicit
        if file.endswith('.py') and '.' in name:
            head,tail=name.split('.',1)
            if head in self.imports.get(file,{}):return self.imports[file][head]+'.'+tail
        if file.endswith('.java'):
            from .java_contracts import TYPES
            candidates = [package + '.' + name for package in self.import_wildcards[file]
                          if package + '.' + name in TYPES or package + '.' + name in self.types_by_fqn]
            if len(set(candidates)) == 1:
                return candidates[0]
        return ''

    def type_fields(self, key, seen=None):
        seen = set() if seen is None else seen
        if key in seen or key not in self.types:
            return {}
        seen.add(key)
        info = self.types[key]
        result = {}
        for parent in info.parents:
            resolved = self.resolve_type(parent, info.module, info.span.file)
            result.update(self.type_fields(resolved, seen))
        result.update(info.fields)
        return result

    def methods_of(self, key, name, count=None, seen=None):
        seen = set() if seen is None else seen
        if key not in self.types or key in seen:
            return []
        seen.add(key)
        info = self.types[key]
        found = [self.methods[m] for m in info.methods if self.methods[m].name == name and (count is None or len(self.methods[m].params) == count)]
        if found:
            return found
        return [m for parent in info.parents for m in self.methods_of(self.resolve_type(parent, info.module, info.span.file), name, count, seen)]

    def enabled(self, info):
        profile = info.annotations.get("Profile", "")
        if not profile:
            return True
        values = re.findall(r'"([^"\\]+)"', profile)
        profiles=self.configuration.profiles.get(info.module) or self.profiles
        if not profiles:
            return None
        from .spring_config import matches
        outcomes=[matches(v,profiles) for v in values]
        return True if True in outcomes else None if None in outcomes else False

    def implementation(self, key):
        if 'FeignClient' in self.types[key].annotations:
            return '' if re.search(r'\bprimary\s*=\s*false\b',self.types[key].annotations['FeignClient']) else key
        candidates = []
        for candidate, info in self.types.items():
            if self.enabled(info) is False:
                continue
            if any(self.resolve_type(p, info.module, info.span.file) == key for p in info.parents) and info.annotations.get("kind") != "interface_declaration":
                candidates.append(candidate)
        return candidates[0] if len(candidates) == 1 else key if not candidates else ""

    def resolve_function(self, name, file="", module=""):
        target = self.imports.get(file, {}).get(name.split(".")[0])
        if target:
            name = target + name[len(name.split(".")[0]):]
        local_module = self.adapters["python"].module_names.get(file, "")
        name = self.adapters["python"].scoped(name, file)
        variants = {name, local_module + "." + name}
        matches = [m.key for m in self.methods.values() if m.language == "python" and (m.key in variants or (m.owner not in self.types and m.name == name and m.span.file == file))]
        scope = module or self.module(file)
        local = [key for key in matches if self.methods[key].module == scope]
        matches = local or matches
        if len(matches) == 1:
            return matches[0]
        return ""
