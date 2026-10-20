"""Do not apply a pinned native contract to a conflicting supplied version."""
from functools import lru_cache
from importlib.metadata import version


@lru_cache(maxsize=None)
def installed(package):return version(package)


def check(engine,package,span):
    module=engine.method.module if engine.method else engine.p.module(span.file)
    supplied=engine.context.get('framework_versions',{}).get(module,{})
    declared=next((v for k,v in supplied.items() if k.lower().replace('_','-')==package.lower().replace('_','-')),None)
    if declared is not None and declared!=installed(package):
        engine.unsupported('Native '+package+' contract is pinned to '+installed(package)+'; supplied '+str(declared),span)
