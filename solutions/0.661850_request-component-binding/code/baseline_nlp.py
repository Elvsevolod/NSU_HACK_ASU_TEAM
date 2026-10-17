"""Source-file discovery, token normalization and route-prefix matching."""
import os
import re
from baseline_closure import toks

FRONT_EXT = ('.js', '.html', '.htm', '.vue', '.ts', '.jsx', '.tsx')
SKIP_DIR = {'node_modules', 'target', 'build', 'dist', '.git', 'bower_components'}
VENDOR = re.compile(r'(\.min\.|^(vue|angular|jquery|bootstrap|echarts|amazeui|iscroll|cropper|aliyun|react|lodash|moment|d3|three)\b)', re.I)
VOWELS = set('aeiouy')

def stem(w):
    """Консервативная нормализация английских суффиксов без предметного словаря."""
    if len(w) >= 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) >= 5 and w.endswith("es") and w[-3] in "sxz" or w.endswith(("ches", "shes")):
        w = w[:-2]
    elif len(w) >= 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 4 and any(c in VOWELS for c in w[:-len(suf)]):
            w = w[:-len(suf)]
            if len(w) > 4 and w[-1] == w[-2] and w[-1] not in VOWELS:
                w = w[:-1]
            break
    return w


def ntoks(t):
    return [stem(w) for w in toks(t)]


def prefix_match(segs, tpl):
    """Литерал пути из фронтенда против шаблона обработчика: литерал может обрываться перед хвостом из переменных
    (`"/items/" + itemKey`)."""
    i = 0
    for i, s in enumerate(segs):
        if i >= len(tpl):
            return False
        t = tpl[i]
        if t == "**":
            return True
        if not (t.startswith("{") or t == "*" or t == s):
            return False
    return all(t.startswith("{") or t in ("*", "**") for t in tpl[len(segs):])


def front_files(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIR and not d.startswith(".")]
        for f in fns:
            if f.endswith(FRONT_EXT) and not VENDOR.search(f):
                p = os.path.join(dp, f)
                if os.path.getsize(p) < 400_000:
                    yield p

