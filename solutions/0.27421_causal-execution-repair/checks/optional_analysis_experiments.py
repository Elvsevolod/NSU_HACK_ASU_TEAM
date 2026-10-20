"""Measured getter-summary ablation and a bounded Java-int SMT pilot."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'checks')]
from analyzer.project import Project,text
from analyzer.state import Database,U
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex,ContractGrounder,read_static_context
from analyzer.__main__ import analyze,serial
from analyzer import getter_effects
from analyzer.constraints import assume,InfeasiblePath,unparenthesized
from compare_public_corpus import edge_set,subset
from tree_sitter import Language,Parser
import tree_sitter_java


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    summaries=[];original=getter_effects.commute
    for enabled in (False,True):
        getter_effects.commute=original if enabled else lambda *args:False
        for fixture in sorted(args.fixtures.iterdir()):
            if not (fixture/'skeleton.json').exists():continue
            started=time.perf_counter();project=Project(fixture/'skeleton.json',fixture)
            frontend=Frontend(project);index=ContractIndex(project,frontend);db=Database(fixture/'initial.sql')
            prepare=time.perf_counter()-started
            scenario=json.loads((fixture/'scenarios.json').read_text());oracle=json.loads((fixture/'oracle.json').read_text())
            for repetition in range(3):
                started=time.perf_counter();block,detail=analyze(project,frontend,index,None,db,read_static_context({}),scenario,grounder_type=ContractGrounder)
                elapsed=time.perf_counter()-started
                results=all(observed['alternatives'] and all(wanted['ignore_result'] or
                    (subset(wanted['result'],a['result']) if wanted.get('result_subset') else wanted['result']==a['result']) for a in observed['alternatives'])
                    for observed,wanted in zip(detail['steps'],oracle['steps']))
                summaries.append({'enabled':enabled,'fixture':fixture.name,'repetition':repetition,'prepare_seconds':prepare,
                    'analysis_seconds':elapsed,'graph_exact':edge_set(block['edges'])==edge_set(oracle['edges']),
                    'results_exact':results,'summary_entries':len(project.__dict__.get('_getter_effect_summaries',{}))})
    getter_effects.commute=original
    import z3
    java=Parser(Language(tree_sitter_java.language()))
    cases=[('(x-y)==1 && x==y',False),('x<0 && x>0',False),('x==y && x!=y',False),
        ('x==0 && (x*x)<0',False),('x==2147483647 && (x+1)<0',True),('x<y && y<0',True)]
    solver_rows=[]
    for expression,expected_sat in cases:
        tree=java.parse(('class P {boolean test(int x,int y){return '+expression+';}}').encode())
        from analyzer.project import walk
        condition=next(n for n in walk(tree.root_node) if n.type=='return_statement').named_children[0]
        variables={name:z3.BitVec(name,32) for name in ('x','y')}
        def convert(node):
            node=unparenthesized(node)
            if node.type=='identifier':return variables[text(node)]
            if node.type=='decimal_integer_literal':return z3.BitVecVal(int(text(node)),32)
            if node.type=='unary_expression':return -convert(node.named_children[-1])
            if node.type!='binary_expression':raise ValueError('outside pure int32 pilot')
            a,b=convert(node.child_by_field_name('left')),convert(node.child_by_field_name('right'))
            operation=text(node.child_by_field_name('operator'))
            return {'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'==':lambda:a==b,'!=':lambda:a!=b,
                '<':lambda:a<b,'>':lambda:a>b,'<=':lambda:a<=b,'>=':lambda:a>=b,
                '&&':lambda:z3.And(a,b),'||':lambda:z3.Or(a,b)}[operation]()
        started=time.perf_counter();solver=z3.Solver();solver.add(convert(condition));sat=solver.check()==z3.sat
        solver_seconds=time.perf_counter()-started
        rejected=False
        try:assume(condition,{'x':U,'y':U},True,{'x':'int','y':'int'},lambda:'local')
        except InfeasiblePath:rejected=True
        assert sat==expected_sat
        solver_rows.append({'java_condition':expression,'expected_satisfiable':expected_sat,'smt_satisfiable':sat,
            'interval_rejected':rejected,'smt_seconds':solver_seconds})
    report={'summary_ablation':summaries,'summary_decision':'Accepted only source effect summaries with source/model/config/receiver versions and alias proof; never cache a return value by method/arguments.',
        'smt_version':z3.get_version_string(),'smt_checks':len(solver_rows),'smt_cases':solver_rows,
        'smt_scope':'Experimental pure int32 locals/bitvector arithmetic. No heap, calls, long/floating-point, Java exceptions or write-state reuse.',
        'smt_decision':'Not a production dependency: this pilot improves relational feasibility examples, but a real-corpus final error reduction is not established.',
        'targets_started':False,'external_llm_api_calls':0}
    (args.output/'experiments.json').write_text(json.dumps(report,indent=2,default=serial)+'\n')
    print(json.dumps({'summary_rows':len(summaries),'smt_checks':len(solver_rows),'smt_passed':True}))


if __name__=='__main__':main()
