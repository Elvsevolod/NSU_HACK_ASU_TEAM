"""Recheck immutable parent/inputs and produce the cumulative accepted patch."""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path

V=Path(__file__).resolve().parents[1];ROOT=V.parents[1]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',default='e4');args=parser.parse_args()
    assert re.fullmatch(r'e[0-9]+',args.tag)
    output=V/'development'/(args.tag+'-integrity');output.mkdir(exist_ok=False)
    parent=ROOT/'solutions/0.22997_state-semantics-and-retrieval'
    parent_hashes=read(V/'development/parent32-sha256.json')
    protected=read(parent/'development/protected-files.json');registry='solutions/README.md'
    parent_errors=[name for name,value in parent_hashes.items() if not (parent/name).is_file() or sha(parent/name)!=value]
    input_errors=[name for name,value in protected.items() if name!=registry and (not (ROOT/name).is_file() or sha(ROOT/name)!=value)]
    frozen={'solution.zip':'386e17850efe73a1816f1a162528e1dd7f97208ad9c4bede819259dfc43b4a3a',
        '../../exports/solution_33_source_contracts_models_analysis.zip':'39aa80b268a681a03010b064749582d8b81d518ab73e62b58da4d1e69b105fca',
        'solution-e4.zip':'1cc962d8a2ba86225bfb2f9a9d90416d2d8d1ec3d7fc281b110fda0b0ac8eed2',
        'solution-e6.zip':'fce7191a5f4b386bff7f6b7648d62a45c999e7d3f6503efa4ae0ded7ba244b6a',
        'solution-e7.zip':'10602c42dade62d580bae16db4b53332d9a1403549518cb467a2249b45726386',
        'solution-e14.zip':'7bda7698542525e52acbb176ce0cc63a6706eab2e65ddd2ea3f265e83bf5e398',
        'solution-e16.zip':'d110a94c3ba41ee77ab53e461af6ce468e4a378b39654fd151ef9b7b53dc2812',
        'solution-e21.zip':'d9a8929730eca4006d0c3cae70ceccf668943c40f1008308aefe6dd943b27332',
        '../../exports/solution_33_source_contracts_models_analysis_v5.zip':'e2d204f8e2a97a57a7ec38f0b01feb5781cc3720e733905ca1aaa90509e601c7',
        '../../exports/solution_33_source_contracts_models_analysis_v4.zip':'1e8096069d650d6fb8463e3597b3c873e2f902dc8b788ea1c8b5e2faa327c57f',
        '../../exports/solution_33_source_contracts_models_analysis_v3.zip':'0375e6378c0b8de98a633e33f907d2e90508c665304072ccd0b0e1aca76648a4',
        '../../exports/solution_33_source_contracts_models_analysis_v2.zip':'1ac30d0625a238ef0d3f08d8801f57dffb0837356ca12a0e3d9aabe0129914a4'}
    archive_errors=[name for name,value in frozen.items() if sha(V/name)!=value]
    changes=[];patch=[]
    for name in sorted({p.relative_to(root) for root in (parent/'code',V/'code') for p in root.rglob('*') if p.is_file()}):
        a=(parent/'code'/name).read_text() if (parent/'code'/name).is_file() else ''
        b=(V/'code'/name).read_text() if (V/'code'/name).is_file() else ''
        if a==b:continue
        changes.append(str(name));patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='parent32/'+str(name),tofile=args.tag.upper()+'/'+str(name)))
    (output/('parent32-to-'+args.tag+'.patch')).write_text(''.join(patch))
    metadata=read(V/'benchmark'/(args.tag+'-candidate-metadata.json'))
    exact_code={p.relative_to(V/'code').as_posix():sha(p) for p in (V/'code').rglob('*') if p.is_file()}
    report_sha=sha(Path('/Users/elvsevolod/Downloads/solution_31_models_and_static_analysis_review.md'))
    result={'parent32_files':len(parent_hashes),'parent32_mismatches':parent_errors,'protected_input_files':len(protected)-int(registry in protected),
        'protected_input_mismatches':input_errors,'mutable_registry':{'path':registry,'current_sha256':sha(ROOT/registry),
            'reason':'Authorized version registry update, not a protected input'},
        'frozen_archives':frozen,'frozen_archive_mismatches':archive_errors,'changed_code_files':changes,
        'code_matches_candidate':exact_code==metadata['code_sha256'],'stage':args.tag,'report_sha256':report_sha,
        'report_matches_active_goal':report_sha=='4a1c9f985808aacd4e35816d028779586407c13bf74f938df14a71b859a29592',
        'targets_started':False}
    result['passed']=not parent_errors and not input_errors and not archive_errors and result['code_matches_candidate'] and result['report_matches_active_goal']
    (output/'integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('frozen_archives','changed_code_files')}))
    assert result['passed']


if __name__=='__main__':main()
