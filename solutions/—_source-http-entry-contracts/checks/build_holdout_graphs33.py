"""Prepare new real-project graph inputs; no scenario prediction is permitted."""
import hashlib
import json
from pathlib import Path
from holdout_source_graph33 import extract

V=Path(__file__).resolve().parents[1]
PACKAGES={
    'employment':{'modules':['companyms','jobms','reviewms'],'schemas':{'companyms':'company','jobms':'job','reviewms':'review'}},
    'healthcare':{'modules':['doctor-service','patient-service'],'schemas':{'doctor-service':'hospital_db','patient-service':'hospital_db'}},
}


def main():
    for name,spec in PACKAGES.items():
        root=V/'development/holdout-preflight'/name;source=root/'source';output=root/'prepared';output.mkdir(exist_ok=False)
        resolved={}
        for module in spec['modules']:
            values={}
            for line in (source/module/'src/main/resources/application.properties').read_text().splitlines():
                if not line.strip() or line.lstrip().startswith(('#','!')) or '=' not in line:continue
                key,value=line.split('=',1);values[key.strip()]=value.strip()
            resolved[module]={'profiles':[values.get('spring.profiles.active','default')],
                'propertySources':[{'name':'independent resolved deployment snapshot, from pinned source defaults','source':values}]}
        context={'clock':'The system clock is 2026-10-19T12:00:00',
            'configuration':resolved,'environment_scope':'Direct service API requests; initial datastore and runtime facts will be frozen with the source oracle before inference.',
            'preflight_only':True}
        graph,provenance=extract(source,spec['modules'],'holdout-'+name+'-v1',context,spec['schemas'])
        (output/'skeleton.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
        (output/'extraction.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
        kinds={kind:sum(n['kind']==kind for n in graph['nodes'].values()) for kind in ('module','type','method','call_site','data_resource','config_entry')}
        record={'project':name,'source_revision':json.loads((root/'origin.json').read_text())['revision'],
            'graph_sha256':hashlib.sha256((output/'skeleton.json').read_bytes()).hexdigest(),
            'extractor_sha256':hashlib.sha256((V/'checks/holdout_source_graph33.py').read_bytes()).hexdigest(),
            'kinds':kinds,'diagnostics':provenance['diagnostics'],'source_only_preparation':True,'scenario_inference_run':False,
            'oracle_status':'not frozen; source review and framework-state obligations still required',
            'excluded_modules':[p.name for p in source.iterdir() if p.is_dir() and p.name not in spec['modules']],
            'scope':'Complete production sources of the selected synchronous service slices, not a full application-support claim.'}
        (output/'preflight.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(record,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
