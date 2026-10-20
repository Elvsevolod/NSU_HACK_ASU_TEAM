"""Copy selected production slices and frozen inputs into standalone packages."""
import hashlib
import json
from pathlib import Path
import shutil

V=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    frozen=V/'development/semantic-holdouts-frozen-v1'
    freeze=json.loads((frozen/'freeze.json').read_text())
    assert all(sha(frozen/name)==digest for name,digest in freeze['files'].items())
    output=V/'development/semantic-holdout-packages-v1';output.mkdir(exist_ok=False)
    for project in freeze['applications']:
        old=frozen/project;target=output/project
        shutil.copytree(old,target)
        source=V/'development/holdout-preflight'/project/'source'
        extraction=json.loads((V/'development/holdout-preflight'/project/'prepared/extraction.json').read_text())
        for module in extraction['modules']:
            shutil.copytree(source/module,target/'source'/module)
        manifest={'project':project,'source_revision':json.loads((old/'oracle.json').read_text())['source_revision'],
            'source':'source','normal_skeleton':'skeleton.json','context':'initial.sql','oracle':'oracle.json',
            'input_recipes_contain_oracle':False,'targets_started':False,
            'source_scope':extraction['modules'],'origin_freeze_sha256':sha(frozen/'freeze.json'),
            'files':{p.relative_to(target).as_posix():sha(p) for p in sorted(target.rglob('*')) if p.is_file()}}
        (target/'package.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'project':project,'files':len(manifest['files']),'inference_run':False}))


if __name__=='__main__':main()
