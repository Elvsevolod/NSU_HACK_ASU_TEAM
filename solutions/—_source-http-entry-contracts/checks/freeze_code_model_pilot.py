"""Freeze identical handler units, source labels and model protocol before inference."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'code'))
from analyzer.contracts import ContractIndex
from analyzer.frontend import Frontend
from analyzer.project import Project,text
from analyzer.retrieval_sources import documents


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--transfer-review',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    source=args.transfer_review.resolve()
    shutil.copytree(source/'sources/licensing-candidate',root/'sources/licensing')
    origin=json.loads((source/'sources/licensing-candidate.origin.json').read_text())
    origin['label']='licensing';save(root/'sources/licensing.origin.json',origin)
    spec=importlib.util.spec_from_file_location('independent_source_prepare',V/'checks/freeze_model_source.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);builder.BASE=root
    builder.prepare('licensing')
    package=root/'packages/licensing'
    shutil.copyfile(package/'skeleton.json',package/'source/skeleton.json')
    (package/'source/initial.sql').write_text('-- Empty ranking-only state; no application execution claimed.\n')
    projects={name:V/'development/transfer'/name/'source' for name in ('organization','library')}
    projects['licensing']=package/'source'
    corpus={};project_objects={}
    for name,location in projects.items():
        project=Project(location/'skeleton.json',location);project_objects[name]=project
        index=ContractIndex(project,Frontend(project));raw=documents(project,index.contracts)
        units={}
        for row in raw.values():
            if row['entry'] in units:raise ValueError('duplicate handler unit needs explicit consolidation')
            method=text(project.ast.get(row['entry']))
            facts=row['facts']
            prefix=f"{facts['owner']}.{facts['method']}\nHTTP {facts['http_method']} /{'/'.join(facts['route'])}\nRequest fields: "+json.dumps(facts['request_fields'],ensure_ascii=False,sort_keys=True)+'\n'
            base=prefix+method
            chunks=[]
            for chunk in row['chunks']:
                value=chunk['text']
                if value not in base and value not in chunks:chunks.append(value)
            units[row['entry']]={'entry':row['entry'],'file':row['file'],'line':row['line'],
                'source_sha256':row['source_sha256'],'text':base,
                'context_text':base+('\nSource context:\n'+'\n'.join(chunks[:4]) if chunks else ''),
                'source_chunks':row['chunks']}
        assert len(units)<=128
        corpus[name]={'documents':units,'candidate_pool':sorted(units),'root_relative_to_variant':location.relative_to(V).as_posix()}
    development=json.loads((source/'frozen-v2/queries.json').read_text())
    for row in development:row['split']='development'
    methods=project_objects['licensing'].methods
    def entry(owner,name,count):
        found=[mid for mid,meta in methods.items() if project_objects['licensing'].nodes[meta['owner']]['fqn'].endswith('.'+owner)
               and meta['name']==name and len(meta['params_as_written'])==count]
        assert len(found)==1,(owner,name,count,found)
        return found[0]
    controller='LicenseServiceController';organization='OrganizationServiceController'
    families=[
        ('license-list',[entry(controller,'getLicenses',1)],'answer',False,
         'List all licenses belonging to organization O7.','Покажи все лицензии организации O7.'),
        ('license-read',[entry(controller,'getLicenses',2)],'answer',False,
         'Read license L2 issued to organization O7.','Прочитай лицензию L2 организации O7.'),
        ('license-create',[entry(controller,'saveLicenses',1)],'answer',False,
         'Issue a new license for organization O7 and its compiler product.','Создай лицензию для организации O7 на продукт компилятора.'),
        ('license-update',[entry(controller,'updateLicenses',2)],'answer',False,
         'Update the details of license L2 for organization O7.','Измени сведения лицензии L2 организации O7.'),
        ('organization-read',[entry(organization,'getOrganization',1)],'answer',False,
         'Read the contact details of organization O7.','Прочитай контактные сведения организации O7.'),
        ('organization-update',[entry(organization,'updateOrganization',2)],'answer',False,
         'Change the contact name for organization O7.','Измени имя контактного лица организации O7.'),
        ('no-sms-handler',[],'no-handler',True,
         'Send an SMS text message to a phone number.','Отправь SMS на номер телефона.'),
        ('ambiguous-delete',[entry(controller,'deleteLicenses',2),entry(organization,'deleteOrganization',2)],'ambiguous',True,
         'Delete a record.','Удали запись.'),
    ]
    holdout=[]
    for family,acceptable,kind,refuse,en,ru in families:
        for language,action in (('en',en),('ru',ru)):
            holdout.append({'id':'licensing/'+family+'/'+language,'project':'licensing','family':'licensing/'+family,
                'language':language,'action':action,'acceptable_entries':acceptable,'kind':kind,
                'requires_refusal':refuse,'split':'test',
                'label_basis':'Independent source reading of pinned controller method annotations and bodies; no analyzer/model prediction used.'})
    for row in development+holdout:
        assert set(row['acceptable_entries'])<=set(corpus[row['project']]['candidate_pool']),row['id']
    frozen=root/'frozen';frozen.mkdir()
    save(frozen/'corpus.json',corpus)
    save(frozen/'labels-dev.json',development);save(frozen/'labels-test.json',holdout)
    save(frozen/'actions.json',[{k:q[k] for k in ('id','project','action','language','split')} for q in development+holdout])
    protocol={'frozen_at':datetime.now(timezone.utc).isoformat(),'version':33,
        'task':'Rank existing static source HTTP handlers, no method/body/edge generation',
        'development':'32 previously observed organization/library queries; never called fresh holdout',
        'test':'16 licensing-domain queries from pinned real source, no prior inference in our work; not a full semantic holdout',
        'public_pretraining_overlap':'unknown','seed':0,'max_sequence_tokens':512,'document_batch':4,'query_batch':1,
        'max_candidates_per_project':128,'candidate_pool':'Identical complete source handler IDs for every embedding model and common lexical baseline',
        'context_ablation':'Same selected development winner; append at most four deduplicated source AST chunks. No test-based winner or tuning.',
        'ranking_k':[1,3,6],'dtype':'float32','threads':4,'device':'mps; CPU fallback is a separately reported runtime if needed',
        'resource_authority':'User allowed three local model pilots; no paid/cloud APIs, no target application execution',
        'refusal_calibration':{'development_only':True,'minimum_score_grid':[i/20 for i in range(21)]+[1.01],
            'minimum_margin_grid':[0,.01,.03,.05,.1],
            'objective':'Maximize accepted correct - 2*accepted wrong - 2*false accepts; then fewer errors, more accepted correct, stronger margin'},
        'model_selection':'Highest development MRR, then top1, then fewer calibrated false accepts; test labels not consulted',
        'models':{'unixcoder':'5604afdc964f6c53782a6813140ade5216b99006','codet5p':'d9f3a534af4252f04b10cd9f78e05037542d10f6',
            'coderank':'3c4b60807d71f79b43f3c4363786d9493691f8b1','qwen':'97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'},
        'guardrails':'Inference sees corpus/actions/protocol only; no labels, expected graphs, traces or saved predictions in model input',
        'cost':'One fresh-process load per model, reused index; three separately reported warm forwards; OS page cache uncontrolled'}
    save(frozen/'protocol.json',protocol)
    save(frozen/'sha256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(frozen.iterdir()) if p.is_file()})
    print(json.dumps({'projects':{name:len(row['documents']) for name,row in corpus.items()},'development_queries':len(development),'test_queries':len(holdout),'model_inference_run':False}))


if __name__=='__main__':main()
