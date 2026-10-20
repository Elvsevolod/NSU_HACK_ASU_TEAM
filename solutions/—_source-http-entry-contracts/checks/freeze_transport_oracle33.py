"""Extend the original source oracle with typed wire/ordered SQL obligations.

This extension is prepared after semantic outputs were observed. It is a
development checker extension, not a new untouched test. All values are read
from the pre-inference oracle/recipes and production source, never predictions.
"""
from copy import deepcopy
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from tree_sitter import Language,Parser
import tree_sitter_java

V=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def walk(node):
    yield node
    for child in node.named_children:yield from walk(child)
def raw(node):return node.text.decode() if node is not None else ''


def source_parameters(package,graph,entry):
    meta=graph['nodes'][entry];path=package/'source'/meta['file'];source=path.read_bytes()
    tree=Parser(Language(tree_sitter_java.language())).parse(source)
    methods=[node for node in walk(tree.root_node) if node.type=='method_declaration' and node.start_point.row+1==meta['line']]
    assert len(methods)==1,(entry,meta['line'])
    imports=re.findall(r'import\s+([\w.*]+)\s*;',source.decode());params=[]
    for node in methods[0].child_by_field_name('parameters').named_children:
        if node.type!='formal_parameter':continue
        name=raw(node.child_by_field_name('name'));written=raw(node.child_by_field_name('type'))
        mods=next((n for n in node.named_children if n.type=='modifiers'),None)
        for note in mods.named_children if mods else []:
            if note.type not in ('annotation','marker_annotation'):continue
            annotation=raw(note.child_by_field_name('name'));kind=annotation.rsplit('.',1)[-1]
            if kind not in ('PathVariable','RequestParam','RequestBody'):continue
            fqn='org.springframework.web.bind.annotation.'+kind
            assert annotation==fqn or fqn in imports or 'org.springframework.web.bind.annotation.*' in imports
            text=raw(note.child_by_field_name('arguments'));named=re.search(r'"([^"]+)"',text)
            wire_name=named[1] if named else name
            native=written.removeprefix('java.lang.')
            if kind!='RequestBody':
                assert native in ('Long','Integer','String') and not any(i.endswith('.'+native) and i!='java.lang.'+native for i in imports)
            params.append({'name':name,'wire_name':wire_name,'kind':kind,'declared_type':'java.lang.'+native if kind!='RequestBody' else written,
                           'native_kind':native if kind!='RequestBody' else None})
    return params


def method(graph,module,owner,name):
    found=[key for key,row in graph['nodes'].items() if row['kind']=='method' and row['module']==module and row['name']==name
           and graph['nodes'][row['owner']]['fqn'].endswith('.'+owner)]
    assert len(found)==1,(module,owner,name)
    return found[0]


def operation(graph,module,owner,name,resource,verb,args,request=1):
    return {'method':method(graph,module,owner,name),'resource':'res:table:'+resource,'operation':verb,'arguments':deepcopy(args),
            'argument_kinds':[None if isinstance(value,dict) and '$identity' not in value else 'Long' for value in args],
            'request_id':request}


def sql(project,graph,case,number,expected,oracle):
    if project=='healthcare':
        i={'$identity':'new_patient','native_kind':'Long','fresh':True}
        p=lambda name,verb,args,req=1:operation(graph,'patient-service','PatientServiceImpl',name,'hospital_db.patients',verb,args,req)
        d=lambda:operation(graph,'doctor-service','DoctorServiceImpl','getDoctorById','hospital_db.doctors','findById',[7])
        if 'fresh-state' in case:return [p('getPatientById','findById',[11])]
        if number==1:
            row=deepcopy(expected['tables']['hospital_db.patients'][-1]);row['id']=None
            return [p('createPatient','save',[row])]
        if number in (2,4,10):return [p('getPatientById','findById',[11 if number==10 else i])]
        if number==3:return [p('getPatientById','findById',[i]),p('updatePatient','save',[expected['result']])]
        if number in (5,9):return [d(),p('getPatientById','findById',[i],2)]
        if number==6:return [p('deletePatient','deleteById',[i])]
        return [p('getPatientById','findById',[i])]
    i={'$identity':'new_company','native_kind':'Long','fresh':True}
    c=lambda name,verb,args,req=1:operation(graph,'companyms','companyServiceImplement',name,'company.company',verb,args,req)
    r=lambda name,verb,args,req=1:operation(graph,'reviewms','reviewServiceImpl',name,'review.review',verb,args,req)
    j=lambda:operation(graph,'jobms','JobServiceImplement','getJobById','job.job','findById',[101])
    if 'remote-error' in case:return [j(),c('getCompany','findById',[1],2)]
    if 'fresh-state' in case:return [c('getCompany','findById',[1])]
    if number==1:
        row=deepcopy(expected['result']);row['id']=None
        return [c('createCompany','save',[row])]
    if number in (2,4):return [c('getCompany','findById',[i])]
    if number==3:return [c('updateCompany','findById',[i])]
    if number==5:return [j(),c('getCompany','findById',[1],2),r('getAllreview','findByCompanyId',[1],3)]
    if number==6:return [r('updateReview','findById',[201]),r('updateReview','save',[expected['tables']['review.review'][0]])]
    if number==7:return [r('getReview','findById',[201])]
    return [r('updateReview','findById',[999])]


def reference(spec,case):
    if not isinstance(spec,dict) or '$response' not in spec:return deepcopy(spec)
    value=case['steps'][spec['$response']-1]['result']
    for part in spec['path']:value=value[part]
    return deepcopy(value)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    OUT=args.output.resolve()
    OUT.mkdir(exist_ok=False);result={};inputs={}
    for project in ('employment','healthcare'):
        package=V/'development/semantic-holdout-packages-v1'/project
        manifest=read(package/'package.json');assert all(sha(package/name)==digest for name,digest in manifest['files'].items())
        oracle=read(package/'oracle.json');graph=read(package/'skeleton.json');cases={}
        for sid,case in oracle['cases'].items():
            if case['steps'][0].get('refusal'):continue
            explicit=sid.replace('-nl-en','-explicit-script').replace('-nl-ru','-explicit-script')
            script=read(package/case['environment']/'explicit-script'/(explicit+'.json'));witnesses=[]
            for number,expected in enumerate(case['steps'],1):
                recipe=script['request_scripts'][explicit+':'+str(number)];entry=expected['entry']
                values={name:reference(spec,case) for name,spec in recipe['parameters'].items()}
                path=[values.get(part[1:-1],part) if part.startswith('{') and part.endswith('}') else part for part in recipe['route_template'].strip('/').split('/')]
                outer={'target':entry,'deployment':recipe['deployment'],'method':recipe['method'],'path':path,'query':{},
                       'headers':recipe['headers'],'body':recipe.get('body',{'missing':True}),'status':expected['status']}
                bound={};history={}
                for param in source_parameters(package,graph,entry):
                    if param['kind']=='RequestBody':continue
                    name=param['name'];value=values[param['wire_name']]
                    bound[name]={'declared_type':param['declared_type'],'native_kind':param['native_kind'],'value':value}
                    original=recipe['parameters'][param['wire_name']]
                    if isinstance(original,dict) and '$response' in original:
                        previous=original['$response']
                        history[name]={'step':previous,'entry':case['steps'][previous-1]['entry'],'value':value,
                            'reference':'history['+str(previous-1)+'].result.'+'.'.join(original['path'])}
                remotes=[]
                for remote in expected['remote_requests']:
                    row=deepcopy(remote);row.update(headers={},body={'missing':True})
                    config=graph['context']['configuration'][row['deployment']]['propertySources'][0]['source']
                    row['authority']='http://'+row['deployment']+':'+str(config['server.port'])
                    if project=='healthcare':row['response_body']=expected['result']['patient'] if row['status']==200 else expected['result']['message']['response']
                    elif row['deployment']=='companyms':row['response_body']=oracle['initial_tables']['company.company'][0]
                    elif row['status']==200:row['response_body']=[]
                    row['bound']={}
                    for param in source_parameters(package,graph,row['target']) if row['target'] else []:
                        if param['kind']=='RequestBody':continue
                        value=row['path'][-1] if param['kind']=='PathVariable' else row['query'][param['wire_name']][0]
                        if param['native_kind'] in ('Long','Integer') and isinstance(value,str):value=int(value)
                        row['bound'][param['name']]={'declared_type':param['declared_type'],'native_kind':param['native_kind'],'value':value}
                    remotes.append(row)
                witnesses.append({'outer':outer,'bound':bound,'history':history,'remotes':remotes,
                    'operations':sql(project,graph,sid,number,expected,oracle)})
            cases[sid]=witnesses
        save(OUT/(project+'.json'),cases)
        inputs[project]={'package_sha256':sha(package/'package.json'),'oracle_sha256':sha(package/'oracle.json')}
        result[project]={'cases':len(cases),'steps':sum(map(len,cases.values()))}
    save(OUT/'freeze.json',{'frozen_at':datetime.now(timezone.utc).isoformat(),'semantic_predictions_previously_observed':True,
        'prediction_files_read':False,'status':'source-backed development checker extension; no new transfer claim',
        'inputs':inputs,'counts':result,'files':{p.name:sha(p) for p in sorted(OUT.glob('*.json'))}})
    print(json.dumps(result))


if __name__=='__main__':main()
