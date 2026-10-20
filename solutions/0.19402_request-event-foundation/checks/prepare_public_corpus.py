"""Freeze bounded real-source NL journeys and manual oracles before prediction.

This validation adapter supplies a skeleton, which is an analyzer input. It
never compiles/runs the target and never feeds oracle methods/edges to grounding.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'code/tests')]
from builders import build


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def fixture(repo,output,module,subdirs,rows,commit):
    sources={p.relative_to(repo).as_posix():p.read_text() for subdir in subdirs
        for p in sorted((repo/subdir).rglob('*.java')) if p.name!='package-info.java'}
    project,_,ids=build(output,sources,module=module,rows=rows)
    graph=deepcopy(project.skeleton)
    for node in graph['nodes'].values():
        if node['kind']=='type':
            package=re.search(r'^package\s+([\w.]+)\s*;',sources[node['file']],re.M)
            if package:node['fqn']=package[1]+'.'+node['fqn']
    resources={}
    for tid,node in list(graph['nodes'].items()):
        if node['kind']!='type':continue
        document=next((a for a in node.get('annotations',[]) if a['name'].split('.')[-1]=='Document'),None)
        if document:
            match=re.search(r'\bcollection\s*=\s*"([^"]+)"',document.get('args',''))
            if match:
                rid='res:collection:'+module+'.'+match[1]
                graph['nodes'][rid]={'kind':'data_resource','resource_kind':'collection','schema':module,'name':match[1],'origin':[{'file':node['file']}]}
                resources[node['fqn'].split('.')[-1]]=rid
        else:
            for rid,resource in graph['nodes'].items():
                if resource['kind']=='data_resource' and any(o.get('file')==node['file'] for o in resource.get('origin',[])):
                    resources[node['fqn'].split('.')[-1]]=rid
    repositories={}
    for source in sources.values():
        for match in re.finditer(r'interface\s+(\w+)\s+extends\s+(?:JpaRepository|CrudRepository|MongoRepository)\s*<\s*(\w+)',source):
            if match[2] in resources:repositories[match[1]]=resources[match[2]]
    for cid,node in graph['nodes'].items():
        if node['kind']=='call_site' and node.get('receiver_type') in repositories:
            edge={'source':cid,'type':'data_access','target':repositories[node['receiver_type']]}
            if edge not in graph['edges']:graph['edges'].append(edge)
    save(output/'skeleton.json',graph)
    save(output/'source-manifest.json',{'repository':repo.name,'commit':commit,'profile':subdirs,
        'application_started':False,'source_files':{key:hashlib.sha256(value.encode()).hexdigest() for key,value in sources.items()},
        'skeleton_adapter':'source-only declarations/calls/Spring Data resources; no expected request or execution edges'})
    return ids


def edge(source,relation,target):return dict(source=source,relation=relation,target=target)


def oracle(output,scenarios,steps,method_ids,extra_edges,limits):
    save(output/'scenarios.json',scenarios)
    save(output/'oracle.json',{'fixed_before_prediction':True,'steps':steps,'edges':[
        edge('scenario:'+scenarios['id'],'executes',method_ids[name]) for name in extra_edges['executes']]+[
        edge(method_ids[a],relation,method_ids[b] if relation=='calls' else b) for a,relation,b in extra_edges['other']],
        'limits':limits})
    save(output/'FILES.sha256.json',{p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob('*')) if p.is_file()})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--public-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not args.output.exists()
    clinic=args.output/'petclinic-customers'
    base='spring-petclinic-customers-service/src/main/java/org/springframework/samples/petclinic/customers/'
    seed={'id':1,'first_name':'Joe','last_name':'Smith','address':'Main','city':'York','telephone':'12345'}
    ids=fixture(args.public_root/'petclinic-microservices',clinic,'customers',[base+'model',base+'web'],
        {'owners':[seed],'pets':[],'types':[]},'1d76b00d683e86b62867a6bf59530f8ab301244f')
    payload='firstName "Eva" lastName "Jones" address "Elm" city "York" telephone "67890"'
    actions=['List owners','Create owner '+payload,'List owners',
        'Update owner ownerId "1" firstName "Joe" lastName "Smith" address "Oak" city "Leeds" telephone "11223"',
        'Read first owner','GET /owners/invalid','List owners']
    owner={'id':1,'firstName':'Joe','lastName':'Smith','address':'Main','city':'York','telephone':'12345','pets':[]}
    updated={**owner,'address':'Oak','city':'Leeds','telephone':'11223'}
    expected=[(200,[owner],1),(201,{'firstName':'Eva','lastName':'Jones','address':'Elm','city':'York','telephone':'67890','pets':[]},2),
        (200,None,2),(204,None,2),(200,updated,2),(400,None,2),(200,None,2)]
    names=['OwnerResource.findAll','OwnerResource.createOwner','OwnerResource.findAll','OwnerResource.updateOwner','OwnerResource.findOwner','OwnerResource.findOwner','OwnerResource.findAll']
    steps=[{'n':n+1,'endpoint':ids[names[n]],'status':status,'result':result,'result_subset':n==1,
            'ignore_result':n in (2,3,5,6),'rows':{'customers.owners':count,'customers.pets':0},
            'arguments':{'ownerId':1} if n in (3,4) else {'ownerId':'invalid'} if n==5 else {}}
        for n,(status,result,count) in enumerate(expected)]
    setters=['Owner.set'+name for name in ('Address','City','Telephone','FirstName','LastName')]
    executes=['OwnerResource.findAll','OwnerResource.createOwner','OwnerResource.updateOwner','OwnerResource.findOwner','OwnerEntityMapper.map','Owner.getPetsInternal',*setters]
    other=[('OwnerResource.createOwner','calls','OwnerEntityMapper.map'),('OwnerResource.updateOwner','calls','OwnerEntityMapper.map')]
    other += [('OwnerEntityMapper.map','calls',name) for name in setters]
    other += [(name,'data','res:table:customers.owners') for name in names[:5]]
    other += [(name,'data','res:table:customers.pets') for name in ('OwnerResource.findAll','OwnerResource.updateOwner','OwnerResource.findOwner')]
    # Deduplicate repeated controller operations in the scenario union.
    oracle(clinic,{'id':'clinic-journey','project':'fixture','steps':[{'n':n+1,'action':action} for n,action in enumerate(actions)]},steps,ids,
        {'executes':executes,'other':list(dict.fromkeys(other))},[
        'Pinned Customers HTTP profile, prevalidated valid DTO fields; no gateway/reactive or full Bean Validation/security model',
        'Generated numeric identifier is symbolic; never supplied as a guessed integer',
        'No pets initially; EAGER association read is a datastore event even when empty',
        'No remote edge in this real-source profile; synthetic corpus tests nonempty remote separately'])
    finance=args.output/'piggymetrics-account'
    base='account-service/src/main/java/com/piggymetrics/account/'
    ids=fixture(args.public_root/'piggymetrics',finance,'account',[base+'domain',base+'controller',base+'service',base+'client',base+'repository'],
        {'accounts':[{'name':'demo','lastSeen':None,'incomes':None,'expenses':None,'saving':None,'note':'seed'}]},'6bb2cf9ddbca980b664d3edbb6ff775d75369278')
    actions=['Read account by name "demo"','Create new account username "demo" password "valid-password"','Read account by name "demo"']
    names=['AccountController.getAccountByName','AccountController.createNewAccount','AccountController.getAccountByName']
    steps=[{'n':n+1,'endpoint':ids[name],'status':400 if n==1 else 200,
        'result':{'name':'demo','note':'seed'},'result_subset':True,'ignore_result':n==1,
        'rows':{'account.accounts':1},'arguments':{'name':'demo'} if n!=1 else {}}
        for n,name in enumerate(names)]
    executes=['AccountController.getAccountByName','AccountController.createNewAccount','AccountServiceImpl.findByName','AccountServiceImpl.create','User.setUsername','User.setPassword','User.getUsername','ErrorHandler.processValidationError']
    other=[('AccountController.getAccountByName','calls','AccountServiceImpl.findByName'),('AccountController.createNewAccount','calls','AccountServiceImpl.create'),
        ('AccountServiceImpl.create','calls','User.getUsername'),('AccountServiceImpl.findByName','data','res:collection:account.accounts'),('AccountServiceImpl.create','data','res:collection:account.accounts')]
    oracle(finance,{'id':'finance-refusal','project':'fixture','steps':[{'n':n+1,'action':action} for n,action in enumerate(actions)]},steps,ids,
        {'executes':executes,'other':other},[
        'PiggyMetrics was already used in development; this is not a blind holdout',
        'Authorized account HTTP profile and normalized supplied Mongo seed; Mongo event is not labeled SQL',
        'Duplicate creation fails before auth-service; success creation/statistics Feign chain is outside this measured profile'])
    # Held-out scenarios are sealed now and run only after candidate development.
    save(args.output/'heldout.json',{'frozen_before_final_run':True,'cases':[
        {'fixture':'petclinic-customers','action':'PUT /owners/999\n'+json.dumps({'firstName':'Mia','lastName':'Doe','address':'Birch','city':'York','telephone':'33333'}),
         'endpoint':'OwnerResource.updateOwner','status':404,'initial_context':'fresh supplied seed, before any generated identity'},
        {'fixture':'piggymetrics-account','action':'GET /absent','endpoint':'AccountController.getAccountByName','status':200,'result':None}]})
    print(json.dumps({'output':str(args.output),'oracles_frozen':True,'source_apps_started':False}))


if __name__=='__main__':main()
