"""Independent state assertions compiled from frozen requests/SQL and source.

This strengthens the partial checker after its first runs; it does not change
the analyzed inputs, relevance labels, thresholds, or assessed analyzer code.
"""

import copy

import json

from pathlib import Path

BASE=Path(__file__).resolve().parent

def unknown(value):
    return isinstance(value,dict) and (value.get('unknown') is True or value.get('knowledge')=='unknown')

def matches(wanted,actual):
    if wanted=={'known_nonnull':True}:
        return actual is not None and not unknown(actual)
    if isinstance(wanted,dict):return isinstance(actual,dict) and all(key in actual and matches(v,actual[key]) for key,v in wanted.items())
    if isinstance(wanted,list):return isinstance(actual,list) and len(wanted)==len(actual) and all(matches(a,b) for a,b in zip(wanted,actual))
    if type(wanted) is bool and type(actual) is int:return actual==int(wanted)  # Physical BIT transport only.
    return type(wanted) is type(actual) and wanted==actual

def rows_match(expected,actual):
    return isinstance(actual,list) and len(expected)==len(actual) and all(any(matches(row,found) for found in actual) for row in expected)

def state_matches(wanted,state):
    if any(table in state.get('unknown_tables',[]) for table in wanted):return False
    return all(rows_match(rows,state.get('tables',{}).get(table)) for table,rows in wanted.items())

def hr_expected():
    tables={'organization-service.organization':[],'department-service.department':[],'employee-service.employee':[]}
    rows=[]
    for number in range(1,10):
        if number==1:tables['organization-service.organization']=[{'id':'O1','name':'North Lab','address':'Main Street','departments':[],'employees':[]}]
        if number==2:tables['department-service.department']=[{'id':'D1','organizationId':'O1','name':'Research'}]
        if number==3:tables['employee-service.employee']=[{'id':'E1','organizationId':'O1','departmentId':'D1','name':'Ada','age':23,'position':'Engineer'}]
        if number==5:tables['employee-service.employee'][0].update(age=24,position='Senior Engineer')
        rows.append(copy.deepcopy(tables))
    return rows

def initial_library():
    return {
      'order.book_order':[{'id':100,'userId':7,'bookId':11,'bookReferenceId':'loaned-11','collectedAt':None,'returnedAt':None,'lateFees':None}],
      'order.book_order_history':[],
      'inventory.inventory':[{'bookId':11,'bookReferenceId':'loaned-11','available':False},
                             {'bookId':21,'bookReferenceId':'available-21','available':True},
                             {'bookId':31,'bookReferenceId':'copy-A','available':True},
                             {'bookId':31,'bookReferenceId':'copy-B','available':True}]}

def wanted_library(case,number,result):
    tables=initial_library()
    if case=='library-existing-order-state':
        if number>=2:tables['order.book_order'][0]['collectedAt']={'known_nonnull':True}
        if number>=5:
            tables['order.book_order']=[]
            tables['order.book_order_history']=[{'orderId':100,'userId':7,'bookId':11,'bookReferenceId':'loaned-11','lateFees':0,'collectedAt':{'known_nonnull':True},'returnedAt':{'known_nonnull':True}}]
            tables['inventory.inventory'][0]['available']=True
    elif case=='library-create-and-select':
        tables['order.book_order'].append({'userId':8,'bookId':21,'bookName':'Bench Book','bookReferenceId':'available-21','id':{'known_nonnull':True}})
        tables['inventory.inventory'][1]['available']=False
    elif case=='library-unordered-stock':
        ref=result.get('bookReferenceId') if isinstance(result,dict) else None
        if ref not in ('copy-A','copy-B'):return None
        for row in tables['inventory.inventory']:
            if row['bookReferenceId']==ref:row['available']=False
    return tables

def evaluate(project,report):
    checks=[]
    hr=hr_expected()
    for sid,scenario in report['scenarios'].items():
        for number,step in enumerate(scenario['steps'],1):
            outcomes=[];refs=set()
            for alternative in step['alternatives']:
                if project=='organization':
                    expected=hr[number-1] if sid=='organization-state-chain' else {key:[] for key in hr[0]}
                else:
                    expected=wanted_library(sid,number,alternative['result'])
                    if sid=='library-unordered-stock' and isinstance(alternative['result'],dict):refs.add(alternative['result'].get('bookReferenceId'))
                after=alternative.get('state_after',{})
                valid=expected is not None and state_matches(expected,after)
                complete=alternative.get('exploration',{}).get('complete') is True
                outcomes.append({'entry':alternative['entry'],'state_projection_passed':valid,'exploration_complete':complete})
            coverage=project!='library' or sid!='library-unordered-stock' or refs=={'copy-A','copy-B'}
            checks.append({'scenario':sid,'step':number,'passed':bool(outcomes) and all(r['state_projection_passed'] and r['exploration_complete'] for r in outcomes) and coverage,
                'outcomes':outcomes,'legal_order_coverage':coverage,'scope':'Known persistent fields and row cardinalities; transient fields, generated exact timestamps and full framework callbacks not asserted.'})
    return {'project':project,'passed':all(c['passed'] for c in checks),'checks':checks,'partial_oracle':True,'after_first_run_checker_strengthening':True,
            'source_basis':'Frozen initial.sql, literal requests, controller repository.save, Mongo explicit-save persistence, order collect/refusal/return bodies and history mapping.'}
