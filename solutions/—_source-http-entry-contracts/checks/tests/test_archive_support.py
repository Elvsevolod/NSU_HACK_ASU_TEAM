"""Own-package extraction rejects corruption, ambiguity, traversal and symlinks."""
import hashlib,io,json,os,stat,sys,zipfile
import pytest
from archive_support import verified_manifest,execute


def package(name='submission.json',data=b'{}',duplicate=False,symlink=False,digest=None):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        info=zipfile.ZipInfo(name)
        if symlink:info.external_attr=(stat.S_IFLNK|0o777)<<16
        z.writestr(info,data)
        if duplicate:z.writestr(name,data)
        z.writestr('benchmark/package-manifest.json',json.dumps({name:digest or hashlib.sha256(data).hexdigest()}))
    stream.seek(0);return zipfile.ZipFile(stream)


def test_own_package_manifest():
    with package() as archive:assert verified_manifest(archive,'benchmark/package-manifest.json')['submission.json']==hashlib.sha256(b'{}').hexdigest()


@pytest.mark.parametrize('name',['../escape','/absolute','a/../escape','a\\escape','C:escape','a//b'])
def test_unsafe_paths(name):
    with package(name) as archive,pytest.raises(ValueError):verified_manifest(archive,'benchmark/package-manifest.json')


@pytest.mark.parametrize('options',[{'duplicate':True},{'symlink':True},{'digest':'0'*64}])
def test_duplicate_symlink_or_corruption(options):
    with package(**options) as archive,pytest.raises(ValueError):verified_manifest(archive,'benchmark/package-manifest.json')


def test_timeout_keeps_partial_output_and_real_status(tmp_path):
    value=execute([sys.executable,'-u','-c','import time;print("started",flush=True);time.sleep(2)'],tmp_path,os.environ,tmp_path,'probe',0.1)
    assert value['timed_out'] and value['returncode'] is None
    assert (tmp_path/'probe.stdout.txt').read_text()=='started\n'
