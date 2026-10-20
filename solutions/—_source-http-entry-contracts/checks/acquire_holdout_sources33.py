"""Pin public production sources before any new-app analyzer inference."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import stat
import os
import re
import subprocess
import urllib.request
import zipfile
from io import BytesIO

V=Path(__file__).resolve().parents[1]
PROJECTS={'employment':'mohit-karonde/microserviceJobApplication','healthcare':'txk39430/hospital-management-system'}


def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'source-only-holdout-preparation'})
    with urllib.request.urlopen(request,timeout=60) as response:
        value=response.read(64*1024*1024+1)
    assert len(value)<=64*1024*1024,'source archive exceeds the preparation limit'
    return value


def main():
    base=V/'development/holdout-preflight';base.mkdir(exist_ok=False);summary=[]
    for name,repo in PROJECTS.items():
        target=base/name;target.mkdir()
        result=subprocess.run(['git','-c','credential.helper=','-c','core.askPass=','ls-remote','https://github.com/'+repo+'.git','HEAD'],
            env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','GIT_TERMINAL_PROMPT':'0','GIT_ASKPASS':'/usr/bin/false'},
            capture_output=True,text=True,check=True,timeout=45)
        revision=result.stdout.split()[0];assert re.fullmatch(r'[0-9a-f]{40}',revision)
        url='https://codeload.github.com/'+repo+'/zip/'+revision
        archive=fetch(url);included={};excluded=[]
        with zipfile.ZipFile(BytesIO(archive)) as z:
            assert sum(info.file_size for info in z.infolist())<512*1024*1024
            for info in z.infolist():
                if info.is_dir():continue
                path=PurePosixPath(info.filename);assert not path.is_absolute() and '..' not in path.parts
                assert stat.S_IFMT(info.external_attr>>16)!=stat.S_IFLNK
                relative=PurePosixPath(*path.parts[1:]);parts=set(relative.parts)
                production=('/src/main/' in '/'+str(relative) or relative.name=='pom.xml')
                document=relative.name.lower().startswith(('license','copying','readme'))
                frontend=any(part in parts for part in ('frontend','client','ui')) and relative.suffix in ('.js','.jsx','.ts','.tsx','.html','.json','.css')
                excluded_tree=parts&{'.git','.idea','target','build','node_modules','dist','.mvn','src/test'} or 'src/test/' in str(relative)
                if excluded_tree or not (production or document or frontend) or relative.suffix in ('.class','.jar','.zip','.png','.jpg','.jpeg','.gif','.pdf'):
                    excluded.append(str(relative));continue
                data=z.read(info);file=target/'source'/str(relative);file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
                included[str(relative)]=hashlib.sha256(data).hexdigest()
        origin={'repository':'https://github.com/'+repo,'revision':revision,'archive_url':url,'archive_sha256':hashlib.sha256(archive).hexdigest(),
            'license_metadata':'Read retained license files; no API metadata claim','source_files':included,'excluded_paths':excluded,
            'targets_executed':False,'analyzer_inference_run':False,'oracle_written':False,
            'selection':'Source-only preflight for two different domains; mandatory chain coverage must be established from code before a holdout can be frozen.'}
        (target/'origin.json').write_text(json.dumps(origin,ensure_ascii=False,indent=2)+'\n')
        summary.append({'project':name,'repository':repo,'revision':revision,'files':len(included),'excluded':len(excluded)})
    (base/'selection.json').write_text(json.dumps({'projects':summary,'status':'source_preflight_only','predictions_used_for_selection':False},indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
