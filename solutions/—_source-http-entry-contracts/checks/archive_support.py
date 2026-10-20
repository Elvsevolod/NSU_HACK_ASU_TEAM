"""Strict own-package verification before extraction, plus durable timeout outputs."""
import hashlib,json,stat,subprocess,time
from pathlib import PurePosixPath


def verified_manifest(archive,manifest_name):
    names=[]
    for info in archive.infolist():
        name=info.filename;path=PurePosixPath(name)
        if not name or '\\' in name or ':' in name or '\x00' in name or path.is_absolute() or '..' in path.parts or '.' in path.parts:
            raise ValueError('unsafe archive member: '+repr(name))
        if path.as_posix()!=name.rstrip('/') or stat.S_ISLNK(info.external_attr>>16):raise ValueError('non-canonical or symbolic-link member: '+repr(name))
        names.append(name.rstrip('/'))
    if len({n.casefold() for n in names})!=len(names):raise ValueError('duplicate/case-colliding archive member')
    files={i.filename for i in archive.infolist() if not i.is_dir()}
    manifest=json.loads(archive.read(manifest_name))
    if set(manifest)|{manifest_name}!=files:raise ValueError('manifest does not cover exact archive files')
    for name,digest in manifest.items():
        if hashlib.sha256(archive.read(name)).hexdigest()!=digest:raise ValueError('package hash differs: '+name)
    if archive.testzip() is not None:raise ValueError('archive CRC failed')
    return manifest


def execute(command,cwd,environment,output,label,timeout):
    started=time.perf_counter()
    with (output/(label+'.stdout.txt')).open('w') as out,(output/(label+'.stderr.txt')).open('w') as err:
        try:
            run=subprocess.run(command,cwd=cwd,env=environment,stdout=out,stderr=err,timeout=timeout)
            status={'returncode':run.returncode,'timed_out':False}
        except subprocess.TimeoutExpired:status={'returncode':None,'timed_out':True}
    return {**status,'command':command,'timeout_seconds':timeout,'elapsed_seconds':time.perf_counter()-started}
