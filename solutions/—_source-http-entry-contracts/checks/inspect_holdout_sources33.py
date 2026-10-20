"""Measure source/index preparation only; labels and scenarios are not inputs."""
import argparse
import hashlib
import json
import platform
import resource
import time
from pathlib import Path
from analyzer.project import Project
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex
from analyzer.retrieval_sources import documents
from analyzer.measurements import peak_rss

V=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);rows=[]
    for name in ('employment','healthcare'):
        folder=V/'development/holdout-preflight'/name;started=time.perf_counter()
        project=Project(folder/'prepared/skeleton.json',folder/'source');frontend=Frontend(project);index=ContractIndex(project,frontend)
        facts=documents(project,index.contracts)
        assert len(facts)==len({c['entry'] for c in index.contracts.values()})
        for row in facts.values():
            assert row['source_sha256']==hashlib.sha256(project.sources[row['file']]).hexdigest()
        (args.output/(name+'-source-facts.json')).write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n')
        record={'project':name,'seconds':time.perf_counter()-started,'canonical_handlers':len(facts),'contracts':len(index.contracts),
            'frontend_sites':len(frontend.sites),'source_errors':project.source_errors,'route_warnings':project.route_warnings,
            'source_only_preparation':True,'query_inference_run':False,'targets_executed':False,
            'cost_scope':'fresh process, sequential app preparation; OS cache not cleared; no query/model forward',
            'python':platform.python_version(),**peak_rss(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}
        rows.append(record)
    (args.output/'preparation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(json.dumps(rows))


if __name__=='__main__':main()
